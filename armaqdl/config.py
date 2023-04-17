import os
import shutil
from pathlib import Path

import toml

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
        settings = toml.load(folder / SETTINGS_FILE)
    except TypeError as e:
        print(f"Error! Invalid settings file!\n{e}")
        return None
    except toml.TomlDecodeError as e:
        print(f"Error! Invalid settings format!\n{e}")
        return None

    return settings


def validate(settings):
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

    if not settings.get('server'):
        print("Error! No '[server]' defined.")
        ok = False

    return ok
