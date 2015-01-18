#!/usr/bin/python

# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""CLI script and setuptools bridge for running unit tests"""

import sys
import unittest

class Loader(unittest.TestLoader):

    "Silly glue class to make setuptools support discovery"

    def loadTestsFromNames(self, names, _=None):
        "Called by setuptools, with its test_suite argument as the single name"
        return self.discover(names[0])

def main():
    "CLI entry point"
    loader = unittest.defaultTestLoader
    runner = unittest.TextTestRunner()
    suite = loader.discover('tests')
    result = runner.run(suite)
    return int(not result.wasSuccessful())

if __name__ == '__main__':
    sys.exit(main())
