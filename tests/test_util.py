import unittest
import doctest

import parse_host_string_doctest

def load_tests(loader, tests, ignore):
    flags = doctest.REPORT_NDIFF
    tests.addTests(doctest.DocTestSuite(parse_host_string_doctest, optionflags = flags))
    return tests

class UtilTest(unittest.TestCase):
    pass
