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
OUTPUT_FILE = 'test_output.json'

# BETYdb instance to hit up
BETYDB_URL = 'http://128.196.65.186:8000/bety'


def test_exists():
    """Asserts that the source file is available"""
    assert os.path.isfile(SOURCE_PATH)


def test_usage():
    """Program prints a "usage" statement when requested"""
    for flag in ['-h', '--help']:
        cmd = f'{SOURCE_PATH} {flag}'
        ret_val, out = getstatusoutput(cmd)
        assert ret_val == 0
        assert re.match('usage', out, re.IGNORECASE)


def test_fail_betydb_url():
    """Test that not specifying a BETYdb URL fails"""
    # pylint: disable=import-outside-toplevel
    import betydb2geojson as b2j
    with pytest.raises(RuntimeError):
        b2j.query_betydb_experiments()


def test_betydb_url():
    """Test getting BETYdb data"""
    # pylint: disable=import-outside-toplevel
    import betydb2geojson as b2j
    ret_val = b2j.query_betydb_experiments(BETYDB_URL)
    assert ret_val is not None
    for key in ['metadata', 'data']:
        assert key in ret_val


def test_command_line():
    """Test running betydb2geojson.py from the command line
    """
    subprocess.run(['python3', SOURCE_FILE, "-u", "https://terraref.ncsa.illinois.edu/bety", "-o", OUTPUT_FILE],
                   check=True)

    assert os.path.isfile(OUTPUT_FILE)

    with open(OUTPUT_FILE) as out_file:
        file_data = json.load(out_file)
        for key in ['type', 'name', 'features']:
            assert key in file_data
