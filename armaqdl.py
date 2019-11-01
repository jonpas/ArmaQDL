#!/usr/bin/env python3

import sys
import os
import argparse
import subprocess
import glob
import re
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
    # Name: [file identifier, command, arguments]
    "HEMTT": ["hemtt.toml", "hemtt", "build"],
    "Mikero": [r"tools\build.py", "python", r"tools\build.py"],
    "Make": ["Makefile", "make", "-j4"]
}

OPEN_LOG_DELAY = 3

SERVER_PROFILE = "Server"
SERVER_JOIN = "localhost:2302:test"
# CONFIGURATION END #

VERBOSE = False


def find_arma(executable=True):
    path = ""

    if os.name == "nt":
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Bohemia Interactive\Arma 3")
            path = winreg.EnumValue(k, 1)[1]
            winreg.CloseKey(k)
        except:
            print("Error! Could not find Arma path in registry.")
            return None

        if executable:
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
        req_file, cmd, args = info

        if os.path.exists(os.path.join(path, req_file)):
            print("=> Building [{}] ...".format(build_tool))

            try:
                subprocess.run([cmd, args], cwd=path, shell=True, check=True)
            except subprocess.CalledProcessError:
                print("  -> Failed! Build error.\n")
                return False

            print()
            return True

    print("  -> Failed! No build tool found.\n")
    return False


def process_mods(mods, build_dev):
    if not mods:
        return ""

    paths = []
    wildcards = 0

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

        location_path = MOD_LOCATIONS.get(location)
        if not location_path or not os.path.exists(location_path):
            print("Invalid location: {}".format(location))
            continue
        else:
            path = os.path.join(location_path, mod)

            # Split wildcard (add to the end)
            if "*" in mod:
                mods_wildcard = ["{}:{}".format(location, mod_wildcard[len(location_path) + 1:])
                                 for mod_wildcard in glob.glob(path)]
                mods.extend(mods_wildcard)
                wildcards += 1
                continue

            if not os.path.exists(path):
                print("Invalid mod path: {}".format(path))
                continue

        print("{}  [{}]".format(cli_mod, path))

        # Build
        if build or (build_dev and location in BUILD_DEV_MODS):
            if not build_mod(path):
                continue

        paths.append(path)  # Marks success

    # Some mods are invalid (return at the end to show all invalid locations/paths)
    if len(paths) != len(mods) - wildcards:
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


def process_mission_server(mission):
    if not mission:
        return ""

    if ":" in mission:
        print("Warning! Mission allowed only from root 'MPMissions' folder!")
        _, mission = mission.split(":")

    if "mission.sqm" in mission:
        mission = mission[:-12]  # Remove "/mission.sqm"

    if "/" in mission or "\\" in mission:
        print("Warning! Mission allowed only from root 'MPMissions' folder!")
        mission = mission.rsplit("/", 1)[-1]
        mission = mission.rsplit("\\", 1)[-1]

    # TODO Support special characters (. -> %20)

    arma_path = find_arma(executable=False)
    path = os.path.join(arma_path, "MPMissions", mission)
    if not os.path.exists(path):
        return None

    # Replace server.cfg mission template
    cfg_path = r"{}\server.cfg".format(arma_path)
    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path, "r+") as f:
            cfg = f.read()
            cfg_replaced = re.sub('(template = ").+(";)', r'\1{}\2'.format(mission), cfg)
            f.seek(0)
            f.write(cfg_replaced)
            f.truncate()
    else:
        print("Error! server.cfg not found! [{}]".format(cfg_path))

    return ""


def process_flags(args):
    flags = ["-nosplash", "-hugepages"]

    if args.profile:
        flags.append("-name={}".format(args.profile))
    else:
        print("Waning! No profile given!")

    if not args.no_filepatching:
        flags.append("-filePatching")

    if not args.no_errors:
        flags.append("-showScriptErrors")

    if args.no_pause:
        flags.append("-noPause")

    if args.check_signatures:
        flags.append("-checkSignatures")

    if not args.fullscreen:
        flags.append("-window")

    if args.join_server:
        if args.join_server.count(":") == 2:
            ip, port, password = args.join_server.split(":")
            flags.append("-connect={}".format(ip))
            flags.append("-port={}".format(port))
            flags.append("-password={}".format(password))
        else:
            print("Error! Invalid server data! (expected 2 ':' seperators)")

    return flags


def process_flags_server(args):
    flags = ["-server", "-hugepages", "-loadMissionToMemory", "-config=server.cfg",
             "-name={}".format(SERVER_PROFILE)]

    if not args.no_filepatching:
        flags.append("-filePatching")

    if args.check_signatures:
        flags.append("-checkSignatures")

    return flags


def run_arma(arma_path, params):
    process_cmd = [arma_path] + params

    if VERBOSE:
        print("Process command: {}".format(process_cmd))

    print("Running ...")
    # Don't wait for process to finish (Popen() instead of run())
    subprocess.Popen(process_cmd)


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(description="Quick development Arma 3 launcher")

    parser.add_argument("mods", metavar="loc:mod ...", type=str, nargs="*", help="paths to mods")
    parser.add_argument("-m", "--mission", default="", type=str, help="mission to load")

    parser.add_argument("-s", "--server", action="store_true", help="start server")
    parser.add_argument("-j", "--join-server", nargs="?", const=SERVER_JOIN, type=str, help="join server")

    parser.add_argument("-p", "--profile", default="Dev", type=str, help="profile name")
    parser.add_argument("-nfp", "--no-filepatching", action="store_true", help="disable file patching")
    parser.add_argument("-ne", "--no-errors", action="store_true", help="hide script errors")
    parser.add_argument("-np", "--no-pause", action="store_true", help="don't pause on focus loss")
    parser.add_argument("-c", "--check-signatures", action="store_true", help="check signatures")
    parser.add_argument("-f", "--fullscreen", action="store_true")

    parser.add_argument("-b", "--build", action="store_true", help="build development mods")
    parser.add_argument("-nl", "--no-log", action="store_true", help="don't open last log")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")

    args = parser.parse_args()

    global VERBOSE
    VERBOSE = args.verbose

    # Arma path
    arma_path = find_arma(executable=True)
    if not arma_path:
        print("Error! Invalid Arma path.")
        return 1

    # Mods
    param_mods = process_mods(args.mods, args.build)
    if param_mods is None:
        print("Error! Invalid mod(s).")
        return 2

    # Mission path
    param_mission = None
    if args.server:
        param_mission = process_mission_server(args.mission)
    else:
        param_mission = process_mission(args.mission, args.profile)

    if param_mission is None:
        print("Error! Invalid mission.")
        return 3

    # Flags
    param_flags = process_flags_server(args) if args.server else process_flags(args)

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
