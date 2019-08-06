#!/usr/bin/env python3

import sys
import os
import argparse
import subprocess
import glob
import threading
import time

if os.name == "nt":
    import winreg

# CONFIGURATION START #
MOD_LOCATIONS = {
    "local": r"D:\Arma 3" if os.name == "nt" else os.path.expanduser("~/Downloads"),
    "dev": r"E:\Arma 3\Mods",
    "workshop": r"C:\Games\SteamLib\steamapps\common\Arma 3\!Workshop",
    "p": "P:\\"
}
BUILD_DEV_MODS = ["dev", "p"]

BUILD_TOOLS = {
    # Name: [file identifier, subprogram, command]
    "HEMTT": ["hemtt.toml", "", "hemtt build"],
    "Mikero": [r"tools\build.py", "python", r"tools\build.py"],
    "Make": ["Makefile", "", "make -j4"]
}

OPEN_LOG_DELAY = 3
# CONFIGURATION END #

VERBOSE = False


def find_arma():
    path = ""

    if os.name == "nt":
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Bohemia Interactive\Arma 3")
            path = winreg.EnumValue(k, 1)[1]
            winreg.CloseKey(k)
        except:
            print("Error! Could not find Arma path in registry.")
            return None

        path = os.path.join(path, "arma3_x64.exe")

        if not path or not os.path.exists(path):
            return None
    else:
        # Linux support does not exist, this is just for testing
        path = "test_linux"

    return path


def open_last_rpt():
    time.sleep(OPEN_LOG_DELAY)
    rpt_path = os.path.expanduser("~/AppData/Local/Arma 3")
    rpt_list = glob.glob("{}/*.rpt".format(rpt_path))
    last_rpt = max(rpt_list, key=os.path.getctime)
    os.startfile(last_rpt)


def build_mod(path):
    for build_tool, info in BUILD_TOOLS.items():
        req_file, subprogram, cmd = info

        if os.path.exists(os.path.join(path, req_file)):
            print("=> Building [{}]".format(build_tool))
            cmd = os.path.join(path, cmd)
            subprocess.run([subprogram, cmd])
            print()
            return True

    print("  -> Failed! No build tool found.")
    return False


def process_mods(mods, build_dev):
    if not mods:
        return ""

    paths = []

    for mod in mods:
        location = "p"  # Default if not specified
        build = False

        # Path
        cli_mod = mod
        separators = mod.count(":")
        if separators == 1:
            location, mod = mod.split(":")
        elif separators == 2:
            location, mod, build = mod.split(":")

        path = MOD_LOCATIONS.get(location)
        if not path or not os.path.exists(path):
            print("Invalid location: {}".format(location))
            continue
        else:
            path = os.path.join(path, mod)
            if not os.path.exists(path):
                print("Invalid mod path: {}".format(path))
                continue

        paths.append(path)
        print("{}  [{}]".format(cli_mod, path))

        # Build
        if build or (build_dev and location in BUILD_DEV_MODS):
            build_mod(path)

    # Some mods are invalid (return at the end to show all invalid locations/paths)
    if len(paths) != len(mods):
        return None

    return "-mod={}".format(";".join(paths))


def process_mission(mission, profile):
    if not mission:
        return ""

    if ":" in mission:
        # Different profile given
        profile, mission = mission.split(":")

    # TODO Support special characters (. -> %20)

    path = ""
    if "/" in mission or "\\" in mission:
        # Full path
        if "mission.sqm" in mission:
            # With mission.sqm
            path = mission
        else:
            # Without mission.sqm
            path = os.path.join(mission, "mission.sqm")
    else:
        # Profile path
        path = os.path.join("~", "Documents", "Arma 3 - Other Profiles", profile, "missions", mission, "mission.sqm")
        path = os.path.expanduser(path)

    if not os.path.exists(path):
        return None

    return path


def process_flags(args):
    flags = ["-nosplash", "-noPause", "-hugepages"]

    if args.profile:
        flags.append("-name={}".format(args.profile))
    else:
        print("Waning! No profile given!")

    if not args.no_filepatching:
        flags.append("-filePatching")

    if not args.no_errors:
        flags.append("-showScriptErrors")

    if args.signatures:
        flags.append("-checkSignatures")

    if not args.fullscreen:
        flags.append("-window")

    return flags


def run_arma(arma_path, params):
    process_cmd = [arma_path] + params

    if VERBOSE:
        print("Process command: {}".format(process_cmd))

    print("Running ...")
    subprocess.run(process_cmd)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Quick development Arma 3 launcher")

    parser.add_argument("-m", "--mod", nargs="*", type=str, help="path to mod folder")
    parser.add_argument("-e", "--editor", default="", type=str, help="mission to load")

    parser.add_argument("-p", "--profile", default="Dev", type=str, help="profile name")
    parser.add_argument("-nfp", "--no-filepatching", action="store_true", help="disable file patching")
    parser.add_argument("-ne", "--no-errors", action="store_true", help="hide script errors")
    parser.add_argument("-s", "--signatures", action="store_true", help="check signatures")
    parser.add_argument("-f", "--fullscreen", action="store_true")

    parser.add_argument("-b", "--build", action="store_true", help="build development mods")
    parser.add_argument("-nl", "--no-log", action="store_true", help="don't open last log")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    # Arma path
    arma_path = find_arma()
    if not arma_path:
        print("Error! Invalid Arma path.")
        return 1

    # Mods
    param_mods = process_mods(args.mod, args.build)
    if param_mods is None:
        print("Error! Invalid mod(s).")
        return 2

    # Mission path
    param_mission = process_mission(args.editor, args.profile)
    if param_mission is None:
        print("Error! Invalid mission.")
        return 3

    # Flags
    param_flags = process_flags(args)

    print()

    # Open log file
    if not args.no_log:
        print("Opening last log in {}s ...".format(OPEN_LOG_DELAY))
        t = threading.Thread(target=open_last_rpt)
        t.start()

    # Run
    params = param_flags
    if param_mission:
        params.append(param_mission)
    if param_mods:
        params.append(param_mods)

    run_arma(arma_path, params)

    return 0


if __name__ == "__main__":
    sys.exit(main())
