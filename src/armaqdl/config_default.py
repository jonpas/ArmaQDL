#!/usr/bin/env python3

MOD_LOCATIONS = {
    "p": "P:\\"
}
BUILD_DEV_MODS = ["p", "abs"]

BUILD_TOOLS = {
    # Name: [file identifier, command, arguments]
    "HEMTT": ["hemtt.toml", "hemtt", "build"],
    "Mikero": [r"tools\build.py", "python", r"tools\build.py"],
    "Make": ["Makefile", "make", "-j4"]
}

OPEN_LOG_DELAY = 3

SERVER_PROFILE = "Server"
SERVER_JOIN = "localhost:2302:test"
