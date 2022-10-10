#!/usr/bin/env python3

import shutil
from pathlib import Path

import toml
from platformdirs import PlatformDirs

CONFIG_DIR = Path(PlatformDirs("ArmaQDL").user_config_dir)
SETTINGS_FILE = "settings.toml"

SETTINGS_PATH = CONFIG_DIR / SETTINGS_FILE


def generate():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_PATH.exists():
        shutil.copy2("config" / SETTINGS_FILE, SETTINGS_PATH)


def load(folder):
    try:
        settings = toml.load(folder / SETTINGS_FILE)
    except TypeError as e:
        print(f"Error! Invalid settings file!\n{e}")
    except toml.TomlDecodeError as e:
        print(f"Error! Invalid settings format!\n{e}")

    return settings
