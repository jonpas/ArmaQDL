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

from . import settings
from ._version import version as __version__


VERBOSE = False


def find_arma(executable=True):
    path = ""

    if os.name == "nt":
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Bohemia Interactive\Arma 3")
            path = winreg.EnumValue(k, 1)[1]
            winreg.CloseKey(k)
        except OSError as e:
            print(f"Error! Could not find Arma path in registry.\n{e}")
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
    if os.name == "nt":
        print(f"Opening last log in {settings.OPEN_LOG_DELAY}s ...")
        time.sleep(settings.OPEN_LOG_DELAY)

        rpt_path = os.path.expanduser("~/AppData/Local/Arma 3")
        rpt_list = glob.glob(f"{rpt_path}/*.rpt")
        last_rpt = max(rpt_list, key=os.path.getctime)
        os.startfile(last_rpt)
    else:
        print("Warning: Opening last log only implemented for Windows")


def build_mod(path, tool):
    for build_tool, info in settings.BUILD_TOOLS.items():
        req_file, cmd, args = info

        if (tool == "b" or tool.lower() == build_tool.lower()) and os.path.exists(os.path.join(path, req_file)):
            print(f"=> Building [{build_tool}] ...")

            try:
                subprocess.run([cmd, args], cwd=path, shell=True, check=True)
            except subprocess.CalledProcessError:
                print("  -> Failed! Build error.\n")
                return False

            print()
            return True

    if tool == "b":
        print("=> Building failed! No build tool found.\n")
    else:
        print(f"=> Building failed! Specified build tool not found: {tool}\n")
    return False


def process_mods(mods, build_dev_tool):
    if not mods:
        return ""

    paths = []
    wildcards = 0

    for mod in mods:
        location = "abs"  # Default if not specified
        build_tool = None

        # Path
        cli_mod = mod
        separators = cli_mod.count(":")
        if separators == 1:
            location, mod = cli_mod.split(":")
        elif separators == 2:
            location, mod, build_tool = cli_mod.split(":")

        if location not in settings.MOD_LOCATIONS.keys():
            # Absolute path
            mod = f"{location}:{mod}"
            location = "abs"
            location_path = ""
        else:
            # Predefined path
            location_path = settings.MOD_LOCATIONS.get(location)
            if location_path is None:
                print(f"Invalid location: {location}")
                continue

        path = os.path.join(location_path, mod)

        # Split wildcard (add to the end)
        if "*" in mod:
            mods_wildcard = [f"{location}:{mod_wildcard[len(location_path) + 1:]}"
                             for mod_wildcard in glob.glob(path)]
            mods.extend(mods_wildcard)
            wildcards += 1
            continue

        if not os.path.exists(path):
            print(f"Invalid mod path: {path}")
            continue

        print(f"{cli_mod}  [{path}]")

        # Build
        if build_tool is not None or (build_dev_tool is not None and location in settings.BUILD_DEV_MODS + ["abs"]):
            if not build_mod(path, build_tool if build_tool is not None else build_dev_tool):
                continue

        paths.append(path)  # Marks success

    # Some mods are invalid (return at the end to show all invalid locations/paths)
    if len(paths) != len(mods) - wildcards:
        return None

    return f"-mod={';'.join(paths)}"


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
    cfg_path = fr"{arma_path}\server.cfg"
    if cfg_path and os.path.exists(cfg_path):
        with open(cfg_path, "r+") as f:
            cfg = f.read()
            cfg_replaced = re.sub('(template = ").+(";)', fr'\1{mission}\2', cfg)
            f.seek(0)
            f.write(cfg_replaced)
            f.truncate()
    else:
        print(f"Error! server.cfg not found! [{cfg_path}]")

    return ""


def process_flags(args):
    flags = ["-nosplash", "-hugepages"]

    if args.profile:
        flags.append(f"-name={args.profile}")
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
            flags.append(f"-connect={ip}")
            flags.append(f"-port={port}")
            flags.append(f"-password={password}")
        else:
            print("Error! Invalid server data! (expected 2 ':' seperators)")

    return flags


def process_flags_server(args):
    flags = ["-server", "-hugepages", "-loadMissionToMemory", "-settings.server.cfg",
             f"-name={settings.SERVER_PROFILE}"]

    if not args.no_filepatching:
        flags.append("-filePatching")

    if args.check_signatures:
        flags.append("-checkSignatures")

    return flags


def run_arma(arma_path, params):
    process_cmd = [arma_path] + params

    if VERBOSE:
        print(f"Process command: {process_cmd}")

    print("Running ...")
    # Don't wait for process to finish (Popen() instead of run())
    subprocess.Popen(process_cmd)


def main():
    epilog = "preset mod locations:\n"
    for location in settings.MOD_LOCATIONS:
        epilog += f"  {location} => {settings.MOD_LOCATIONS[location]}\n"

    epilog += "\npreset build tools:\n"
    for tool in settings.BUILD_TOOLS:
        epilog += f"  {tool} ({settings.BUILD_TOOLS[tool][0]}) => {settings.BUILD_TOOLS[tool][1]} {settings.BUILD_TOOLS[tool][2]}\n"

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="armaqdl",
        description=f"Quick development Arma 3 launcher v{__version__}", epilog=epilog,
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("mods", metavar="loc:mod[:b|:tool] ...", type=str, nargs="*", help="paths to mods")
    parser.add_argument("-m", "--mission", default="", type=str, help="mission to load")

    parser.add_argument("-s", "--server", action="store_true", help="start server")
    parser.add_argument("-j", "--join-server", nargs="?", const=settings.SERVER_JOIN, type=str, help="join server")

    parser.add_argument("-p", "--profile", default="Dev", type=str, help="profile name")
    parser.add_argument("-nfp", "--no-filepatching", action="store_true", help="disable file patching")
    parser.add_argument("-ne", "--no-errors", action="store_true", help="hide script errors")
    parser.add_argument("-np", "--no-pause", action="store_true", help="don't pause on focus loss")
    parser.add_argument("-c", "--check-signatures", action="store_true", help="check signatures")
    parser.add_argument("-f", "--fullscreen", action="store_true")
    parser.add_argument("-par", "--parameters", nargs="+", type=str,
                        help="other parameters to pass directly (use with '=' to pass '-<arg>')")

    parser.add_argument("-b", "--build", metavar="TOOL", nargs="?", const="", type=str,
                        help="build mods (auto-determine tool if unspecified)")
    parser.add_argument("-nl", "--no-log", action="store_true", help="don't open last log")

    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("--version", action="store_true", help="show version")

    args = parser.parse_args()

    if args.version:
        print(f"ArmaQDL v{__version__}")
        return 0

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
    if args.parameters is not None:
        param_flags.extend(args.parameters)
    print(f"Flags: {param_flags}\n")

    # Open log file
    if not args.no_log:
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
