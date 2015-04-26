import unittest
import os

class TestCase(unittest.TestCase):
    ROOT_DIR = os.path.realpath(os.path.join(__file__, '..', '..'))

    def add_patch(self, patch):
        patch.start()
        self.patches.append(patch)

    def setUp(self):
        self.patches = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
