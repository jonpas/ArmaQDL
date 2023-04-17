import contextlib
import io
import sys
import unittest

from armaqdl import armaqdl


class UnitTests(unittest.TestCase):

    def test_empty(self):
        sys.argv = ["armaqdl"]
        with io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                ret = armaqdl.main()
            self.assertEqual(ret, 0)
            self.assertTrue("Empty mod paths" in f.getvalue())

    def test_none_dry(self):
        sys.argv = ["armaqdl", "none", "--dry"]
        with io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                ret = armaqdl.main()
            self.assertIn(ret, [0, 2])  # 2 is invalid Arma path
            self.assertTrue("Launching without any mods" in f.getvalue())
            self.assertTrue("Dry run" in f.getvalue())

    def test_version(self):
        sys.argv = ["armaqdl", "--version"]
        with io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                ret = armaqdl.main()
            self.assertEqual(ret, 0)
            self.assertTrue("ArmaQDL v" in f.getvalue())
