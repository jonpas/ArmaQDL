import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from armaqdl import armaqdl, config, foxy


def envelope(action, data, ok=True, errors=None):
    return json.dumps({"ok": ok, "action": action, "data": data, "errors": errors or []})


class FakeFoxy:
    """Replacement for `subprocess.run` answering Foxy CLI `launch` and `addon list` commands."""

    def __init__(self, repos, addons=None):
        self.repos = repos  # repo name -> list of -mod= entries
        self.addons = addons or {}  # repo name -> addon list data
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        repo = command[command.index("--repo-name") + 1] if "--repo-name" in command else command[command.index("--repo-url") + 1]

        if repo not in self.repos:
            out = envelope("launch", None, ok=False, errors=[f"Repository {repo} not found"])
            return subprocess.CompletedProcess(command, 3, stdout=out, stderr="")

        if "launch" in command:
            entries = self.repos[repo]
            args = ["-skipIntro"] + ([f"-mod={';'.join(entries)}"] if entries else [])
            out = envelope("launch", {"repository": repo, "selected_profile": None, "args": args, "execute": False})
        else:
            out = envelope("addon.list", {"repository": repo, "addons": self.addons.get(repo, [])})
        return subprocess.CompletedProcess(command, 0, stdout=out, stderr="")


class FoxyTests(unittest.TestCase):

    def setUp(self):
        foxy.clear_cache()

        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

        # Repository space shared folder (mods of multiple repositories in one folder)
        self.shared = self.root / "shared"
        for name in ["@cba_a3", "@ace", "@acre2", "@other_repo_mod"]:
            (self.shared / name / "addons").mkdir(parents=True)

        # Local development builds
        self.dev = self.root / "dev"
        for name in ["ace", "acre2"]:
            (self.dev / name / "addons").mkdir(parents=True)

        self.settings = config.load(Path("./config"))
        self.settings["locations"] = {"dev": {"path": str(self.dev), "build": False}}
        self.settings["foxy"]["aliases"] = {"ops": "Operations", "url": "https://example.com/repo/"}
        armaqdl.SETTINGS = self.settings

        self.fake = FakeFoxy({
            "Operations": ["gm", str(self.shared / "@cba_a3"), str(self.shared / "@ace"), str(self.shared / "@acre2")],
            "Training": [str(self.shared / "@cba_a3"), str(self.shared / "@other_repo_mod")],
            "https://example.com/repo/": [str(self.shared / "@cba_a3")],
        })

    def tearDown(self):
        self.tmp.cleanup()
        armaqdl.SETTINGS = None

    def process(self, mods):
        with mock.patch("armaqdl.foxy.subprocess.run", self.fake), io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                result = armaqdl.process_mods(mods, None)
            return result, f.getvalue()

    def mod_param(self, *paths):
        return f"-mod={';'.join(str(x) for x in paths)}"

    def test_parse_spec(self):
        self.assertEqual(foxy.parse_spec("My Repo"), ("My Repo", ""))
        self.assertEqual(foxy.parse_spec("My Repo\\@ace"), ("My Repo", "@ace"))
        self.assertEqual(foxy.parse_spec("My Repo/@ace*"), ("My Repo", "@ace*"))

    def test_parse_launch_mods_windows_paths(self):
        data = {"args": ["-skipIntro", "-mod=gm;C:\\Mods\\Shared\\@cba_a3;D:/Mods/@ace;"]}
        mods = foxy.parse_launch_mods("repo", data)
        self.assertEqual([(x.name, x.is_dlc) for x in mods], [("gm", True), ("@cba_a3", False), ("@ace", False)])

    def test_expand_repository(self):
        result, out = self.process(["foxy:Operations"])
        self.assertEqual(result, self.mod_param("gm", self.shared / "@cba_a3", self.shared / "@ace", self.shared / "@acre2"))
        self.assertNotIn("@other_repo_mod", result)  # Not part of repository despite being in the same folder
        self.assertIn("Total mods: 4", out)

    def test_replace_with_local_builds(self):
        result, out = self.process(["foxy:Operations", "foxy:Operations\\@ace:s", "foxy:Operations/@acre*:skip", "dev:ace", "dev:acre2"])
        self.assertEqual(result, self.mod_param("gm", self.dev / "ace", self.dev / "acre2", self.shared / "@cba_a3"))
        self.assertIn("(skip) foxy:Operations\\@ace", out)
        self.assertIn("(skip) foxy:Operations\\@acre2", out)
        self.assertEqual(len([x for x in self.fake.calls if "launch" in x]), 1)  # Cached

    def test_skip_dlc(self):
        result, _ = self.process(["foxy:Operations", "foxy:Operations\\gm:s"])
        self.assertTrue(result.startswith(f"-mod={self.shared / '@cba_a3'}"))

    def test_include_dlc_disabled(self):
        self.settings["foxy"]["include_dlc"] = False
        result, _ = self.process(["foxy:Operations"])
        self.assertNotIn("gm", result.split("=", 1)[1].split(";"))

    def test_filter_subset(self):
        result, _ = self.process(["foxy:Operations\\@cba*"])
        self.assertEqual(result, self.mod_param(self.shared / "@cba_a3"))

    def test_alias_and_url(self):
        result, _ = self.process(["foxy:url"])
        self.assertEqual(result, self.mod_param(self.shared / "@cba_a3"))
        self.assertIn("--repo-url", self.fake.calls[0])

        result, _ = self.process(["foxy:ops"])
        self.assertIn(str(self.shared / "@ace"), result)

    def test_multiple_repositories_deduplicated(self):
        result, _ = self.process(["foxy:Operations", "foxy:Training"])
        self.assertEqual(result.count("@cba_a3"), 1)
        self.assertIn("@other_repo_mod", result)

    def test_repository_not_found(self):
        result, out = self.process(["foxy:Missing"])
        self.assertIsNone(result)
        self.assertIn("not found", out)

    def test_skip_matches_nothing(self):
        result, out = self.process(["foxy:Operations", "foxy:Operations\\@nope:s"])
        self.assertIsNotNone(result)
        self.assertIn("Skip matched no mods", out)

    def test_filter_matches_nothing(self):
        result, out = self.process(["foxy:Operations\\@nope"])
        self.assertIsNone(result)
        self.assertIn("No mods matched", out)

    def test_missing_mod_path(self):
        self.fake.repos["Operations"].append(str(self.shared / "@deleted"))
        result, out = self.process(["foxy:Operations"])
        self.assertIsNone(result)
        self.assertIn("Invalid mod path", out)

    def test_missing_enabled_addon_warning(self):
        self.fake.addons["Operations"] = [
            {"name": "@ace", "enabled": True, "kind": "required"},
            {"name": "@lost", "enabled": True, "kind": "required"},
            {"name": "@disabled", "enabled": False, "kind": "optional"},
        ]
        result, out = self.process(["foxy:Operations"])
        self.assertIsNotNone(result)
        self.assertIn("foxy:Operations\\@lost", out)
        self.assertNotIn("@disabled", out)

    def test_foxy_not_installed(self):
        with mock.patch("armaqdl.foxy.subprocess.run", side_effect=FileNotFoundError("foxy")), io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                result = armaqdl.process_mods(["foxy:Operations"], None)
            self.assertIsNone(result)
            self.assertIn("Could not run Foxy CLI", f.getvalue())

    def test_command_and_config_dir(self):
        self.settings["foxy"]["command"] = ["C:/Foxy/Foxy.exe"]
        self.settings["foxy"]["config_dir"] = "C:/FoxyConfig"
        self.process(["foxy:Operations"])
        self.assertEqual(self.fake.calls[0][:6], ["C:/Foxy/Foxy.exe", "--config-dir", "C:/FoxyConfig", "--json", "--no-progress", "launch"])

    def test_foxy_location_override(self):
        # A regular location named 'foxy' keeps working as before
        self.settings["locations"]["foxy"] = {"path": str(self.shared)}
        result, _ = self.process(["foxy:@ace"])
        self.assertEqual(result, self.mod_param(self.shared / "@ace"))
        self.assertEqual(self.fake.calls, [])
