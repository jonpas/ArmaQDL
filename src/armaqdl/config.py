#!/usr/bin/env python3

import shutil
from pathlib import Path

import toml
from platformdirs import PlatformDirs

CONFIG_DIR = Path(PlatformDirs("ArmaQDL", False, roaming=True).user_config_dir)
SETTINGS_FILE = "settings.toml"


def generate():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not (CONFIG_DIR / SETTINGS_FILE).exists():
        shutil.copy2(Path("config") / SETTINGS_FILE, CONFIG_DIR / SETTINGS_FILE)
        print("Generated new settings file.")


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
