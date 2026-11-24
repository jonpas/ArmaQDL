import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from armaqdl import update

ROOT = Path(__file__).parent.parent
MANIFEST = ROOT / "bucket" / "armaqdl.json"

spec = importlib.util.spec_from_file_location("scoop_manifest", ROOT / "tools" / "scoop_manifest.py")
scoop_manifest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scoop_manifest)

HASH = "a" * 64


class ManifestTests(unittest.TestCase):

    def setUp(self):
        with open(MANIFEST, encoding="utf-8") as f:
            self.manifest = json.load(f)

    def test_manifest_valid(self):
        for key in ["version", "description", "homepage", "license", "url", "hash", "bin", "checkver", "autoupdate"]:
            self.assertIn(key, self.manifest)
        self.assertEqual(self.manifest["url"], self.manifest["autoupdate"]["url"].replace("$version", self.manifest["version"]))
        self.assertRegex(self.manifest["hash"], r"^[0-9a-f]{64}$")

    def test_update(self):
        updated = scoop_manifest.update(self.manifest, "1.2.3", HASH.upper())
        self.assertEqual(updated["version"], "1.2.3")
        self.assertEqual(updated["url"], "https://github.com/jonpas/ArmaQDL/releases/download/v1.2.3/armaqdl.exe")
        self.assertEqual(updated["hash"], HASH)
        self.assertEqual(list(updated), list(self.manifest))

    def test_update_without_hash(self):
        del self.manifest["hash"]
        keys = list(scoop_manifest.update(self.manifest, "1.2.3", HASH))
        self.assertEqual(keys.index("hash"), keys.index("url") + 1)

    def test_update_invalid(self):
        with self.assertRaises(ValueError):
            scoop_manifest.update(self.manifest, "v1.2.3", HASH)
        with self.assertRaises(ValueError):
            scoop_manifest.update(self.manifest, "1.2.3", "abc")

    def test_main_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "armaqdl.json"
            path.write_text(MANIFEST.read_text(encoding="utf-8"), encoding="utf-8")
            self.assertEqual(scoop_manifest.main(["", str(path), "2.0.0", HASH]), 0)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["version"], "2.0.0")


class DistTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()

    def tearDown(self):
        self.tmp.cleanup()

    def dist(self, exe, env=None):
        with mock.patch.object(update, "is_exe", return_value=True), \
             mock.patch.object(update, "get_exe", return_value=exe), \
             mock.patch.dict(os.environ, env or {}, clear=False):
            return update.get_dist()

    def test_scoop_env_root(self):
        exe = self.root / "scoop" / "apps" / "armaqdl" / "1.0.0" / "armaqdl.exe"
        self.assertEqual(self.dist(exe, {"SCOOP": str(self.root / "scoop")}), "scoop")

    def test_scoop_custom_root(self):
        (self.root / "tools" / "shims").mkdir(parents=True)
        exe = self.root / "tools" / "apps" / "armaqdl" / "1.0.0" / "armaqdl.exe"
        self.assertEqual(self.dist(exe), "scoop")

    def test_standalone(self):
        exe = self.root / "apps" / "armaqdl" / "1.0.0" / "armaqdl.exe"  # No shims, not a Scoop root
        self.assertEqual(self.dist(exe), "standalone")
        self.assertEqual(self.dist(self.root / "armaqdl.exe"), "standalone")

    def test_scoop_update_refused(self):
        with mock.patch.object(update, "get_dist", return_value="scoop"), \
             mock.patch.object(update, "get_latest") as latest:
            self.assertEqual(update.update(), 1)
            latest.assert_not_called()
        self.assertIn("scoop update armaqdl", update.get_update_info("scoop"))
