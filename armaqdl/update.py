import ctypes
import json
import os
import sys
import time
from pathlib import Path
from urllib import request, error

from ._version import __version_tuple__
from .const import PACKAGE, CONFIG_DIR, LATEST_FILE

GITHUB = f"https://github.com/jonpas/{PACKAGE}" + "/releases/download/v{}/armaqdl.exe"
PYPI = f"https://pypi.org/pypi/{PACKAGE}/json"


def is_exe():
    return getattr(sys, "frozen", False)


def get_exe_old(exe):
    return exe.parent / f"{exe.stem}_old{exe.suffix}"


def is_admin():
    # Linux (no ctypes.windll)
    if os.name == "posix":
        return True

    # Windows
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() == 1
    except AttributeError:
        return False


def get_latest():
    with request.urlopen(PYPI, timeout=1) as f:
        data = f.read()
        encoding = f.info().get_content_charset("utf-8")

    response = json.loads(data.decode(encoding))
    latest = response["info"]["version"]

    with open(CONFIG_DIR / LATEST_FILE, "w", encoding="utf-8") as f:
        f.write(latest)

    return latest


def is_newer(latest):
    latest_cmp = tuple(map(int, latest.split(".")[:3]))
    current_cmp = __version_tuple__[:3]

    return latest_cmp > current_cmp  # True if newer exists


def clean():
    if is_exe():
        old_exe = get_exe_old(Path(sys.executable))
        if old_exe.exists():
            os.remove(old_exe)


def check():
    # Check metadata of cached latest version file
    modified = 0
    if (CONFIG_DIR / LATEST_FILE).exists():
        modified = os.path.getmtime(CONFIG_DIR / LATEST_FILE)
    now = time.time()
    duration = now - modified

    # Only check if the cached latest version is older than 12 hours
    if duration > 12 * 60 * 60:
        try:
            latest = get_latest()
        except (error.HTTPError, error.URLError) as e:
            print(f"Note: Unable to check for updates. => {e}\n")
            return 1
    else:
        with open(CONFIG_DIR / LATEST_FILE, "r", encoding="utf-8") as f:
            latest = f.read()

    if is_newer(latest):
        if is_exe():
            print(f"Note: Update v{latest} is available! Run with '--update' to perform a self-update.\n")
        else:
            print(f"Note: Update v{latest} is available!\n")

    return 0


def update():
    if not is_exe():
        print("Error! Only standalone executable may be updated!")
        return 1

    try:
        latest = get_latest()
    except (error.HTTPError, error.URLError) as e:
        print(f"Error! Unable to retrieve latest version! => {e}")
        return 2

    if not is_newer(latest):
        print("Latest version is already in use.")
        return 0

    if not is_admin():
        # Re-run with admin rights
        print("Administrator permissions required - agree if you would like to continue.")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)

    exe = Path(sys.executable)
    print(f"Location: {exe}")

    # Rename current executable
    old_exe = get_exe_old(exe)
    os.replace(exe, old_exe)

    try:
        request.urlretrieve(GITHUB.format(latest), exe)
    except (error.HTTPError, error.URLError) as e:
        print(f"Error! Unable to download update! => {e}")
        os.replace(old_exe, exe)
        return 3

    print("Update downloaded!")
    return 0
