import unittest
import sys
from pathlib import Path

from armaqdl import armaqdl, config


class UnitTests(unittest.TestCase):

    def assertIsFile(self, path):
        if not Path(path).resolve().is_file():
            raise AssertionError(f"File does not exist: {path}")

    def test_config_generate(self):
        config.generate()
        self.assertIsFile(config.CONFIG_DIR / config.SETTINGS_FILE)

    def test_config_load(self):
        settings = config.load(Path("./config"))
        self.assertIsNotNone(settings)

    def test_config_validate(self):
        settings = config.load(Path("./config"))
        valid = config.validate(settings)
        self.assertTrue(valid)

    def test_config_generate_main(self):
        sys.argv = ["armaqdl", "-h"]
        with self.assertRaises(SystemExit):
            armaqdl.main()
        self.assertIsFile(config.CONFIG_DIR / config.SETTINGS_FILE)
