#!/usr/bin/env python3

import os

MOD_LOCATIONS = {
    "main": r"D:\Steam\steamapps\common\Arma 3",
    "local": r"D:\Arma 3" if os.name == "nt" else os.path.expanduser("~/Downloads"),
    "dev": r"E:\Arma 3\Mods",
    "workshop": r"D:\Steam\steamapps\common\Arma 3\!Workshop",
    "p": "P:\\"
}
BUILD_DEV_MODS = ["local", "dev", "p"]  # Only build mods from those locations

BUILD_TOOLS = {
    # Name: [file identifier, command, arguments]
    "HEMTT": ["hemtt.toml", "hemtt", "build"],
    "Mikero": [r"tools\build.py", "python", r"tools\build.py"],
    "Make": ["Makefile", "make", "-j4"]
}

OPEN_LOG_DELAY = 3

SERVER_PROFILE = "Server"
SERVER_JOIN = "localhost:2302:test"
