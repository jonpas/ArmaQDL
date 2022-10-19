import contextlib
import io
import sys
import unittest

from armaqdl import armaqdl


class UnitTests(unittest.TestCase):

    def test_version(self):
        sys.argv = ["armaqdl", "--version"]
        with io.StringIO() as f:
            with contextlib.redirect_stdout(f):
                ret = armaqdl.main()
            self.assertEqual(ret, 0)
            self.assertTrue("ArmaQDL v" in f.getvalue())
