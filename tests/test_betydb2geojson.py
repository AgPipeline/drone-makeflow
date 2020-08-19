#!/usr/bin/env python3
"""
Purpose: Unit testing for betydb2geojson.py
Author : Chris Schnaufer <schnaufer@arizona.edu
Notes:
    This file assumes it's in a subfolder off the main folder
"""
import json
import os
import re
import subprocess
from subprocess import getstatusoutput
import pytest

# The name of the source file to test and it's path
SOURCE_FILE = 'betydb2geojson.py'
SOURCE_PATH = os.path.abspath(os.path.join('.', SOURCE_FILE))

# BETYdb instance to hit up
BETYDB_URL = 'https://terraref.ncsa.illinois.edu/bety'


def test_exists():
    """Asserts that the source file is available"""
    assert os.path.isfile(SOURCE_PATH)


def test_usage():
    """
    Program prints a "usage" statement when requested
    """

    for flag in ['-h', '--help']:
        ret_val, out = getstatusoutput(f'{SOURCE_PATH} {flag}')
        assert ret_val == 0
        assert re.match('usage', out, re.IGNORECASE)


def test_fail_betydb_url():
    """Test that not specifying a BETYdb URL fails
    """
    # pylint: disable=import-outside-toplevel
    import betydb2geojson as b2j
    with pytest.raises(RuntimeError):
        b2j.query_betydb_experiments()


def test_betydb_url():
    """Test getting BETYdb data
    """
    # pylint: disable=import-outside-toplevel
    import betydb2geojson as b2j

    test_file = open('object.json', 'w+')

    # subprocess.run(b2j.query_betydb_experiments(BETYDB_URL), check=True)

    # subprocess.check_output(b2j.query_betydb_experiments(BETYDB_URL))

    ret_val = b2j.query_betydb_experiments(BETYDB_URL)
    test_file.write(str(ret_val))

    assert ret_val is not None
    subprocess.call(['echo', str(test_file)])
    for key in ['metadata', 'data']:
        assert key in ret_val


def test_command_line():
    """Test running betydb2geojson.py from the command line
    """
    subprocess.run(['python3', SOURCE_FILE, "-u", "https://terraref.ncsa.illinois.edu/bety", "-o", "test_output.json"],
                   check=True)

    assert os.path.isfile("test_output.json")

    with open("test_output.json") as output_file:
        data = json.load(output_file)
        for key in ['metadata', 'data']:
            assert key in data
