import unittest

class TestCase(unittest.TestCase):
    def add_patch(self, patch):
        patch.start()
        self.patches.append(patch)

    def setUp(self):
        self.patches = []

    def tearDown(self):
        for p in self.patches:
            p.stop()
