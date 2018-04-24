#!/usr/bin/env python3
"""Test suite for sample_data.py
This test suite requires a local mongodb instance and writes to/drops a
database named "abe-unittest" for testing.
"""
import unittest

from abe import sample_data

from . import abe_unittest
from .context import abe  # noqa: F401


class SampleDataTestCase(abe_unittest.TestCase):

    def test_load_data(self):
        """Load sample data"""
        sample_data.load_data(self.db)


if __name__ == '__main__':
    unittest.main()
