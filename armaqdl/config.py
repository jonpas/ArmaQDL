import os
import shutil
import tomllib
from pathlib import Path

from .const import CONFIG_DIR, SETTINGS_FILE

DIST_CONFIG_DIR = Path(__file__).parent / "config"
if not DIST_CONFIG_DIR.exists():  # editable install fall-back location
    DIST_CONFIG_DIR = Path(__file__).parent.parent / "config"


def generate():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    settings_path = CONFIG_DIR / SETTINGS_FILE
    if not settings_path.exists() or os.stat(settings_path).st_size == 0:
        shutil.copy2(DIST_CONFIG_DIR / SETTINGS_FILE, settings_path)
        print("Generated new settings file.\n")


def load(folder):
    try:
        with open(folder / SETTINGS_FILE, "rb") as f:
            settings = tomllib.load(f)
    except OSError as e:
        print(f"Error! Invalid settings file!\n{e}")
        return None
    except tomllib.TOMLDecodeError as e:
        print(f"Error! Invalid settings format!\n{e}")
        return None

    return settings


def validate(settings):
    if settings is None:
        return False

    ok = True

    for location in settings.get('locations', {}):
        if not settings['locations'][location].get('path'):
            print(f"Error! No 'path' defined for location '{location}'.")
            ok = False

    for build_tool in settings.get('build', {}):
        if not settings['build'][build_tool].get('presence'):
            print(f"Error! No 'presence' defined for build tool '{build_tool}'.")
            ok = False
        if not settings['build'][build_tool].get('command'):
            print(f"Error! No 'command' defined for build tool '{build_tool}'.")
            ok = False

    foxy = settings.get('foxy', {})
    command = foxy.get('command', ["foxy"])
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        print("Error! Foxy 'command' must be a non-empty list of strings.")
        ok = False
    for alias, target in foxy.get('aliases', {}).items():
        if not isinstance(target, str) or not target:
            print(f"Error! Foxy alias '{alias}' must be a non-empty repository name or URL.")
            ok = False

    if not settings.get('server'):
        print("Error! No '[server]' defined.")
        ok = False

    return ok
