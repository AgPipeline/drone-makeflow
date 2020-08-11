"""
Purpose: Unit testing for merge_csv.py
Author : Chris Schnaufer <schnaufer@arizona.edu
Notes:
    This file assumes it's in a subfolder off the main folder
"""
import argparse
import errno
import os
import re
from subprocess import getstatusoutput
import pytest

# The name of the source file to test and it's path
SOURCE_FILE = 'merge_csv.py'
SOURCE_PATH = os.path.abspath(os.path.join('.', SOURCE_FILE))

#  Command line flags
FLAG_NO_HEADER = '-n'
FLAG_HEADER_COUNT = '-c'
FLAG_FILTER_IN = '-f'
FLAG_FILTER_IGNORE = '-i'


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


def test_no_parameters():
    """Test that an error occurs when no parameters are specified"""
    cmd = f'{SOURCE_PATH}'
    ret_val, out = getstatusoutput(cmd)
    assert ret_val == 2
    assert re.search('error', out, re.IGNORECASE)


def test_parameters():
    """Tests the parameter parser with various configurations"""
    # pylint: disable=import-outside-toplevel
    import merge_csv as mc
    parser = mc.get_arg_parser()

    # Check specifying files as the parameters
    filename = 'empty.txt'
    try:
        open(filename, 'w').close()
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    cmd = f'{SOURCE_PATH} {filename} {filename}'
    ret_val, out = getstatusoutput(cmd)
    assert ret_val == 2
    assert re.search('error', out, re.IGNORECASE)

    # Check specifying folder names
    cur_dir = os.getcwd()
    parser.parse_args([cur_dir, cur_dir])

    # Check the command line with no headers flag
    parser.parse_args([FLAG_NO_HEADER, cur_dir, cur_dir])

    # Check the command line with headers count
    parser.parse_args([FLAG_HEADER_COUNT, '3', cur_dir, cur_dir])

    # Check the command line with filters
    parser.parse_args([FLAG_FILTER_IN, 'test.csv, other.csv', FLAG_FILTER_IGNORE, 'bad.csv', cur_dir, cur_dir])


def test_simple():
    """Performs a simple csv file merge with no headers"""
    test_filenames = ['sample.csv']
    saved_csv = []

    # Create a subfolder to put test files in
    work_dir = os.path.realpath(os.path.join(os.getcwd(), 'samples'))
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    # Create the input sub folders and file
    file_index = 1
    for one_subdir in [os.path.join(work_dir, '1'), os.path.join(work_dir, '2')]:
        if not os.path.exists(one_subdir):
            os.makedirs(one_subdir)
        for one_file in test_filenames:
            with open(os.path.join(one_subdir, one_file), 'w') as out_file:
                csv_data = 'data %d, string %d' % (file_index, file_index)
                out_file.write(csv_data)
                saved_csv.append(csv_data)
                file_index += 1

    # Run the merge
    ret_val, _ = getstatusoutput(f'{SOURCE_PATH} {FLAG_NO_HEADER} {work_dir} {work_dir}')
    assert ret_val == 0

    # Check the merge contents - get the total number of matching lines before reporting an error
    total_found = 0
    for one_file in test_filenames:
        merge_file = os.path.join(work_dir, one_file)
        with open(merge_file, 'r') as in_file:
            one_line = in_file.readline().rstrip('\n')
            while one_line:
                try:
                    _ = saved_csv.index(one_line)
                    total_found += 1
                except ValueError:
                    pass

                one_line = in_file.readline().rstrip('\n')

    # Check for any errors
    assert total_found == len(saved_csv)
