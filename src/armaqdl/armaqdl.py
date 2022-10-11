#!/usr/bin/env python3

import argparse
import glob
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

if os.name == "nt":
    import winreg

from ._version import version as __version__
from . import config


VERBOSE = False
SETTINGS = None


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
        log_open_delay = SETTINGS.get('log', {}).get('open_delay', 3)
        print(f"Opening last log in {log_open_delay}s ...")
        time.sleep(log_open_delay)

        rpt_path = os.path.expanduser("~/AppData/Local/Arma 3")
        rpt_list = glob.glob(f"{rpt_path}/*.rpt")
        last_rpt = max(rpt_list, key=os.path.getctime)
        os.startfile(last_rpt)
    else:
        print("Warning: Opening last log only implemented for Windows.")


def build_mod(path, tool):
    for build_tool in SETTINGS.get("build", {}):
        req_file = SETTINGS["build"][build_tool]["presence"]
        cmd = SETTINGS["build"][build_tool]["command"]

        if (tool == "b" or tool.lower() == build_tool.lower()) and os.path.exists(os.path.join(path, req_file)):
            print(f"=> Building [{build_tool}] ...")

            try:
                subprocess.run(cmd, cwd=path, shell=True, check=True)
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

        if location not in SETTINGS.get("locations", {}).keys():
            # Absolute path
            mod = f"{location}:{mod}"
            location = "abs"
            location_path = ""
        else:
            # Predefined path
            location_path = SETTINGS.get("locations", {}).get(location, {}).get('path')
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
        if build_tool is not None or (build_dev_tool is not None and (location == "abs" or SETTINGS["locations"][location].get("build", False))):
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

    if not profile:
        profile = SETTINGS.get("profile", "Dev")

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

    profile = args.profile
    if args.headless:
        flags.append("-client")

        if not profile:
            profile = SETTINGS.get("headless", {}).get("profile", "headlessclient")
    else:
        if not profile:
            profile = SETTINGS.get("profile", "Dev")

    flags.append(f"-name={profile}")

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

    # Headless always wants to connect
    if args.join_server is None and args.headless:
        args.join_server = ""

    if args.join_server is not None:
        if args.join_server == "":
            ip = SETTINGS.get("server", {}).get("ip", "localhost")
            port = SETTINGS.get("server", {}).get("port", 2302)
            password = SETTINGS.get("server", {}).get("password", "test")
            flags.append(f"-connect={ip}")
            flags.append(f"-port={port}")
            flags.append(f"-password={password}")
        elif args.join_server.count(":") == 2:
            ip, port, password = args.join_server.split(":")
            flags.append(f"-connect={ip}")
            flags.append(f"-port={port}")
            flags.append(f"-password={password}")
        else:
            print("Error! Invalid server data! (expected 2 ':' seperators)")

    return flags


def process_flags_server(args):
    server_profile = SETTINGS.get("server", {}).get("profile", "Server")

    flags = ["-server", "-hugepages", "-loadMissionToMemory", "-config=server.cfg",
             f"-name={server_profile}"]

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
    # Generate new config
    config.generate()

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog="armaqdl",
        description=f"Quick development Arma 3 launcher v{__version__}",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("mods", metavar="loc:mod[:b|:tool] ...", type=str, nargs="*", help="paths to mods")
    parser.add_argument("-m", "--mission", default="", type=str, help="mission to load")

    parser.add_argument("-s", "--server", action="store_true", help="start server")
    parser.add_argument("-j", "--join-server", nargs="?", const="", type=str, help="join server")
    parser.add_argument("-hc", "--headless", action="store_true", help="start headess client")

    parser.add_argument("-p", "--profile", default="", type=str, help="profile name")
    parser.add_argument("-nfp", "--no-filepatching", action="store_true", help="disable file patching")
    parser.add_argument("-ne", "--no-errors", action="store_true", help="hide script errors")
    parser.add_argument("-np", "--no-pause", action="store_true", help="don't pause on focus loss")
    parser.add_argument("-c", "--check-signatures", action="store_true", help="check signatures")
    parser.add_argument("-f", "--fullscreen", action="store_true")
    parser.add_argument("-par", "--parameters", nargs="+", type=str,
                        help="other parameters to pass directly (use with '=' to pass '-<arg>')")

    parser.add_argument("-b", "--build", metavar="TOOL", nargs="?", const="b", type=str,
                        help="build mods (auto-determine tool if unspecified)")
    parser.add_argument("-nl", "--no-log", action="store_true", help="don't open last log")

    parser.add_argument("--config", default=config.CONFIG_DIR, type=Path, help="load config from specified folder")
    parser.add_argument("--list", action="store_true", help="list active config locations and build tools")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output")
    parser.add_argument("--version", action="store_true", help="show version")

    args = parser.parse_args()

    if args.version:
        print(f"ArmaQDL v{__version__}")
        return 0

    global VERBOSE
    VERBOSE = args.verbose

    # Config
    global SETTINGS
    SETTINGS = config.load(args.config)
    if not config.validate(SETTINGS):
        return 1

    if args.list:
        epilog = f"ArmaQDL config location: {args.config}\n\n"
        epilog += "Mod Locations:"
        for location in SETTINGS.get("locations", {}):
            epilog += f"\n  {location} => {SETTINGS['locations'][location]['path']}"
            if SETTINGS['locations'][location].get('build', False):
                epilog += " (build)"

        epilog += "\n\nBuild Tools:"
        for tool in SETTINGS.get("build", {}):
            epilog += f"\n  {tool} ({SETTINGS['build'][tool]['presence']}) => {' '.join(SETTINGS['build'][tool]['command'])}"

        print(epilog)
        return 0

    # Arma path
    arma_path = find_arma(executable=True)
    if not arma_path:
        print("Error! Invalid Arma path.")
        return 2

    # Mods
    param_mods = process_mods(args.mods, args.build)
    if param_mods is None:
        print("Error! Invalid mod(s).")
        return 3

    # Mission path
    param_mission = None
    if args.server:
        param_mission = process_mission_server(args.mission)
    else:
        param_mission = process_mission(args.mission, args.profile)

    if param_mission is None:
        print("Error! Invalid mission.")
        return 4

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

    if os.name == "nt":
        run_arma(arma_path, params)
    else:
        print("Warning: Launching Arma only implemented for Windows.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
