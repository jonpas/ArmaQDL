import argparse
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import quote

if os.name == "nt":
    import winreg

from ._version import __version__
from .const import PACKAGE
from . import config, update


VERBOSE = False
DRY = False
SETTINGS = None


def find_arma(executable=True):
    path = None

    if os.name == "nt":
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Bohemia Interactive\Arma 3")
            path = winreg.EnumValue(k, 1)[1]
            winreg.CloseKey(k)
        except OSError as e:
            print(f"Error! Could not find Arma path in registry.\n{e}")
            return None

        path = Path(path)

        if executable:
            path = path / "arma3_x64.exe"

        if not path.exists():
            return None
    else:
        # Linux support does not exist, this is just for testing
        path = Path()

    return path


def open_last_rpt():
    if os.name == "nt":
        log_open_delay = SETTINGS.get('log', {}).get('open_delay', 3)
        print(f"Opening last log in {log_open_delay}s ...")
        if not DRY:
            time.sleep(log_open_delay)

        rpt_path = Path.home() / "AppData" / "Local" / "Arma 3"
        rpt_list = rpt_path.glob("*.rpt")
        last_rpt = max(rpt_list, key=os.path.getctime)
        if not DRY:
            os.startfile(last_rpt)
    else:
        print("Warning! Opening last log only implemented for Windows.")


def build_mod(path, tool, launch_type=""):
    for build_tool in SETTINGS.get("build", {}):
        req_file = SETTINGS["build"][build_tool]["presence"]
        cmd = SETTINGS["build"][build_tool]["command"]

        if launch_type and cmd[0] == "hemtt":
            cmd[1] = launch_type

        if (tool == "b" or tool.lower() == build_tool.lower()) and (path / req_file).exists():
            print(f"=> Building [{build_tool}] ...")

            if not DRY:
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
    if not mods or "none" in mods:
        return ""

    if VERBOSE:
        print(f"Process mods: {mods}")

    paths, skips = [], []
    ignores = 0

    for i, mod in enumerate(mods):
        location = "abs"  # Default if not specified
        marks = []

        # Path
        cli_mod = mod
        separators = cli_mod.count(":")
        if separators == 1:
            location, mod = cli_mod.split(":")
        elif separators > 1:
            location, mod, marks = cli_mod.split(":", 2)
            marks = marks.split(":")
            marks = [x.lower() for x in marks]

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

        path = Path(location_path) / mod
        path_build = path

        # Split wildcard (add to the end)
        if "*" in mod:
            mods_wildcard = [f"{location}:{str(mod_wildcard)[len(location_path) + 1:]}"
                             for mod_wildcard in path.parent.glob("*") if mod_wildcard.is_dir()]
            mods.extend(mods_wildcard)
            ignores += 1
            continue

        if not path.exists():
            print(f"Invalid mod path: {path}")
            continue

        # Skip mark (add to skip list)
        if "s" in marks or "skip" in marks:
            if VERBOSE:
                print(f"{cli_mod}  [{path}]\n=> Skip in wildcards")

            skips.append(path)
            ignores += 1
            continue

        # Skip mod found in wildcard
        if path in skips:
            print(f"(skip) {cli_mod}  [{path}]")
            ignores += 1
            continue

        # Get just identifiers (first letters) of each mark
        marks_identifiers = [x[0] for x in marks]

        # HEMTT launch type argument
        launch_type = ""  # Empty is path itself (non-HEMTT)
        if (path / ".hemttout").exists():
            launch_type = SETTINGS.get("locations", {}).get(location, {}).get("type", "dev")

        if "t" in marks_identifiers:
            launch_type_index = marks_identifiers.index("t")
            launch_type = marks[launch_type_index][1:]

            if launch_type not in ["", "dev", "build", "release"]:
                print(f"Invalid launch type: {launch_type} (HEMTT)  [{location}:{mod}]")
                continue

        if launch_type:
            path = path / ".hemttout" / launch_type

        # Local build argument
        build_tool = ""
        if "b" in marks_identifiers:
            mark_build_index = marks_identifiers.index("b")
            build_tool = marks[mark_build_index][1:]

            if not build_tool:
                build_tool = "b"

        # Global build argument
        if not build_tool and build_dev_tool is not None and (location == "abs" or SETTINGS["locations"][location].get("build", False)):
            build_tool = build_dev_tool

        print(f"{cli_mod}  [{path}]")

        # Build
        if build_tool:
            if not build_mod(path_build, build_tool, launch_type=launch_type):
                continue

        # Check path existance after build, as HEMTT output does not exist if no build has been performed yet
        if not path.exists():
            print(f"Invalid mod path: {path}")
            continue

        paths.append(path)  # Marks success

    # Some mods are invalid (return at the end to show all invalid locations/paths)
    if VERBOSE:
        print(f"Paths: {len(paths)} processed vs. {len(mods) - ignores} input ({len(mods)} mods - {ignores} ignores)")

    if len(paths) != len(mods) - ignores:
        return None

    print(f"Total mods: {len(paths)}\n")

    return f"-mod={';'.join([str(x) for x in paths])}"


def process_mission(mission, profile):
    if not mission:
        return ""

    if ":" in mission:
        # Different profile given
        profile, mission = mission.split(":")

    if not profile:
        profile = SETTINGS.get("profile", "Dev")

    # Replace special characters (eg. space -> %20)
    profile = quote(profile)

    path = ""
    if "/" in mission or "\\" in mission:
        # Full path
        if "mission.sqm" in mission:
            # With mission.sqm
            path = Path(mission)
        else:
            # Without mission.sqm
            path = Path(mission) / "mission.sqm"
    else:
        # Profile path
        path = Path.home() / "Documents" / "Arma 3 - Other Profiles" / profile / "missions" / mission / "mission.sqm"

        if not path.exists():
            path = Path.home() / "Documents" / "Arma 3 - Other Profiles" / profile / "mpmissions" / mission / "mission.sqm"

    if not path.exists():
        print(f"Error! Mission not found! [{path}]")
        return None

    print(f"Mission: [{path}]")
    return path


def process_mission_server(mission):
    if not mission:
        return ""

    arma_path = find_arma(executable=False)
    if not arma_path:
        return ""

    # Remove "/mission.sqm"
    if mission.name == "mission.sqm":
        mission = mission.parent

    # Copy to server
    target = arma_path / "MPMissions" / mission.name
    if target.exists():
        shutil.rmtree(target)

    print(f"Copying mission to server ... [{target}]\n")
    shutil.copytree(mission, target)

    # Replace server.cfg mission template
    cfg_path = arma_path / "server.cfg"
    if cfg_path.exists():
        if not DRY:
            with open(cfg_path, "r+", encoding="utf-8") as f:
                cfg = f.read()
                cfg_replaced = re.sub('(template = ").+(";)', fr'\1{mission.name}\2', cfg)
                f.seek(0)
                f.write(cfg_replaced)
                f.truncate()
    else:
        print(f"Error! server.cfg not found! [{cfg_path}]")

    return ""


def process_flags(args):
    flags = ["-skipIntro", "-noSplash", "-hugePages"]

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

    if not args.no_debug:
        flags.append("-debug")

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

    if not args.no_debug:
        flags.append("-debug")

    if args.check_signatures:
        flags.append("-checkSignatures")

    return flags


def run_arma(arma_path, params):
    process_cmd = [arma_path] + params

    if VERBOSE:
        print(f"Process command: {process_cmd}")

    print("Running ...")
    if not DRY:
        # Don't wait for process to finish (Popen() instead of run())
        subprocess.Popen(process_cmd)


def main():
    # Generate new config
    config.generate()

    # Cleanup update files
    update.clean()

    # Parse arguments
    parser = argparse.ArgumentParser(
        prog=PACKAGE,
        description=f"Quick development Arma 3 launcher v{__version__}",
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument("mods", metavar="loc:mod[:b[tool]][:s|:skip][:t[type]] ...", type=str, nargs="*", help="paths to mods or 'none' for no mods")
    parser.add_argument("-m", "--mission", default="", type=str, help="mission to load")

    parser.add_argument("-s", "--server", action="store_true", help="start server")
    parser.add_argument("-j", "--join-server", nargs="?", const="", type=str, help="join server")
    parser.add_argument("-hc", "--headless", action="store_true", help="start headess client")

    parser.add_argument("-p", "--profile", default="", type=str, help="profile name")
    parser.add_argument("-nfp", "--no-filepatching", action="store_true", help="disable file patching")
    parser.add_argument("-ne", "--no-errors", action="store_true", help="hide script errors")
    parser.add_argument("-nd", "--no-debug", action="store_true", help="disable debug mode")
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
    parser.add_argument("--dry", action="store_true", help="dry run without actually launching anything (simulate)")
    parser.add_argument("--verbose", action="store_true", help="verbose output")
    parser.add_argument("--update", action="store_true", help="self-update")
    parser.add_argument("-v", "--version", action="store_true", help="show version")

    args = parser.parse_args()

    if args.version:
        print(f"ArmaQDL v{__version__}")
        return 0

    if args.update:
        update.update()
        return 0
    update.check()

    global VERBOSE
    VERBOSE = args.verbose
    global DRY
    DRY = args.dry
    if DRY:
        print("Dry run - simulating only!\n")

    # Config
    global SETTINGS
    SETTINGS = config.load(args.config)
    if not config.validate(SETTINGS):
        return 1

    if args.list:
        epilog = f"Config location: {args.config}\n\n"
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

    if "none" in args.mods:
        print("Warning! Launching without any mods (vanilla!)")
    elif not args.mods:
        print("Empty mod paths - use 'none' to launch without any mods (vanilla).")
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
    param_mission = process_mission(args.mission, args.profile)
    if param_mission is None:
        print("Error! Invalid mission.")
        return 4

    if args.server:
        param_mission = process_mission_server(param_mission)

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
        print("Warning! Launching Arma only implemented for Windows.")

    return 0
