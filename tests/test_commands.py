import unittest
import sys

from armaqdl import armaqdl


class UnitTests(unittest.TestCase):

    def test_version(self):
        sys.argv = ["armaqdl", "-v"]
        self.assertEqual(armaqdl.main(), 0)
