"""Foxy repository support through Foxy CLI.

Mods are resolved with `foxy --json launch` (without `--execute`, which only builds the launch command),
so the selected repository profile, Creator DLCs and Foxy's addon path resolution are respected.
"""
import fnmatch
import json
import subprocess
from dataclasses import dataclass
from pathlib import PureWindowsPath
from typing import Optional

LOCATION = "foxy"

# Stable Foxy CLI exit codes
EXIT_CODES = {
    2: "validation error",
    3: "not found",
    4: "operation failed",
    5: "partial success",
    6: "database busy",
}


class FoxyError(Exception):
    pass


@dataclass(frozen=True)
class FoxyMod:
    repo: str
    name: str
    path: Optional[str]  # None for Creator DLC codes

    @property
    def is_dlc(self):
        return self.path is None


_cache = {}


def clear_cache():
    _cache.clear()


def parse_spec(spec):
    """Split `repo` or `repo\\@mod` (or `repo/@mod`) into repository and mod pattern."""
    normalized = spec.replace("\\", "/")
    if "/" in normalized:
        repo, pattern = normalized.rsplit("/", 1)
        return repo, pattern
    return normalized, ""


def selector(repo, settings):
    target = settings.get("aliases", {}).get(repo, repo)
    if target.startswith(("http://", "https://")):
        return ["--repo-url", target]
    return ["--repo-name", target]


def build_command(settings, args):
    command = list(settings.get("command", ["foxy"]))
    config_dir = settings.get("config_dir")
    if config_dir:
        command += ["--config-dir", str(config_dir)]
    return command + ["--json", "--no-progress"] + args


def _parse_envelope(stdout):
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        pass

    # Tolerate any stray output before the JSON envelope
    start = stdout.find("{")
    if start != -1:
        try:
            return json.loads(stdout[start:])
        except json.JSONDecodeError:
            pass
    return None


def run(settings, args, verbose=False):
    command = build_command(settings, args)
    if verbose:
        print(f"Foxy command: {command}")

    try:
        proc = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as e:
        raise FoxyError(f"Could not run Foxy CLI '{command[0]}' (set 'command' in [foxy] settings): {e}")

    envelope = _parse_envelope(proc.stdout or "")
    if not isinstance(envelope, dict):
        details = (proc.stderr or proc.stdout or "").strip()
        raise FoxyError(f"Invalid Foxy CLI output (exit code {proc.returncode}){': ' + details if details else ''}")

    if proc.returncode != 0 or not envelope.get("ok", False):
        errors = "; ".join(str(x) for x in envelope.get("errors") or []) or (proc.stderr or "").strip()
        reason = EXIT_CODES.get(proc.returncode, f"exit code {proc.returncode}")
        raise FoxyError(f"Foxy '{args[0]}' failed ({reason}){': ' + errors if errors else ''}")

    return envelope.get("data") or {}


def parse_launch_mods(repo, data):
    """Extract mods from `-mod=` argument of a Foxy launch command."""
    mod_arg = next((x for x in data.get("args", []) if isinstance(x, str) and x.lower().startswith("-mod=")), None)
    if mod_arg is None:
        return []

    mods = []
    for entry in mod_arg[len("-mod="):].split(";"):
        entry = entry.strip()
        if not entry:
            continue
        if "/" in entry or "\\" in entry:
            mods.append(FoxyMod(repo, PureWindowsPath(entry).name, entry))
        else:
            mods.append(FoxyMod(repo, entry, None))
    return mods


def find_missing(mods, data):
    """Enabled required/optional addons of the repository that Foxy did not resolve to a path."""
    resolved = {mod.name.lower() for mod in mods}
    missing = []
    for addon in data.get("addons", []):
        if addon.get("enabled") and addon.get("kind") in ("required", "optional"):
            name = addon.get("name", "")
            if name and name.lower() not in resolved:
                missing.append(name)
    return missing


def resolve(repo, settings, verbose=False):
    """Resolve mods of a Foxy repository (cached per repository)."""
    if repo in _cache:
        return _cache[repo]

    repo_selector = selector(repo, settings)
    data = run(settings, ["launch"] + repo_selector, verbose=verbose)
    mods = parse_launch_mods(repo, data)

    if verbose:
        print(f"Foxy repository '{data.get('repository', repo)}' (profile: {data.get('selected_profile') or 'Default'}): {len(mods)} mods")

    if settings.get("check_missing", True):
        try:
            addons = run(settings, ["addon", "list"] + repo_selector, verbose=verbose)
            for name in find_missing(mods, addons):
                print(f"Warning! Enabled addon not found on disk by Foxy (not loaded): foxy:{repo}\\{name}")
        except FoxyError as e:
            print(f"Warning! Could not check for missing addons: {e}")

    _cache[repo] = mods
    return mods


def match(mods, pattern):
    """Filter mods by folder name glob pattern (case-insensitive), all mods if no pattern."""
    if not pattern:
        return list(mods)
    pattern = pattern.lower()
    return [mod for mod in mods if fnmatch.fnmatchcase(mod.name.lower(), pattern)]
