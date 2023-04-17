from pathlib import Path

from platformdirs import PlatformDirs

PACKAGE = __name__.split(".")[0]

CONFIG_DIR = Path(PlatformDirs("ArmaQDL", False, roaming=True).user_config_dir)
SETTINGS_FILE = "settings.toml"
LATEST_FILE = "latest"
