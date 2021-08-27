#!/usr/bin/env python3
"""Python script for comparing two JSON files
"""

import argparse
import json
import logging
import hashlib
import sys


def _get_params() -> tuple:
    """Get the paths to the files
    Returns:
        A tuple containing the two paths
    """
    parser = argparse.ArgumentParser(description='Compares two JSON files by size and pixel value')

    parser.add_argument('--strip', action='append', help='Period (dot) separated key names for value to ignore')
    parser.add_argument('first_file', type=argparse.FileType('r'), help='The first json file to compare')
    parser.add_argument('second_file', type=argparse.FileType('r'), help='The second json file to compare')

    args = parser.parse_args()

    return args.first_file.name, args.second_file.name


def other_contents_match(val1, val2, key: str) -> bool:
    """Checks the two values to see if they're the same
    Arguments:
        val1: first value to compare
        val2: second value to compare
        key: key name associated with the values
    Return:
        Return True if the values appear to be the same and False otherwise
    Notes:
        The parameter types are assumed to be the same
    """
    # Disabling pylint to keep readable
    # pylint: disable=too-many-branches,too-many-statements
    logging.debug("HACK: other Working on key %s %s", key, type(val1))
    if isinstance(val1, str):
        logging.debug("HACK: other HERE WE HAVE A STRING!")
        if val1 != val2:
            logging.error('Strings don''t match for key "%s"', key)
            logging.error('  1. %s', str(val1))
            logging.error('  2. %s', str(val2))
            return False
        return True

    can_iterate = True
    try:
        iter(val1)
    except TypeError:
        can_iterate = False

    logging.debug("HACK: other Can iterate: %s", str(can_iterate))
    if can_iterate:
        len1 = len(val1)
        len2 = len(val2)
        if len1 != len2:
            logging.error('Different lengths found for key "%s"', key)
            return False
        hash1 = []
        hash1_src = []
        hash2 = []
        hash2_src = []
        for idx in range(0, len1):
            sub_val1 = val1[idx]
            sub_val2 = val2[idx]
            logging.debug("HACK: other Index %d: %s", idx, type(sub_val1))
            if isinstance(sub_val1, dict):
                # Hash values for later comparison
                logging.debug("HACK: Saving dict hash at index %d for later comparison", idx)
                cur_hash = hashlib.sha256(json.dumps(sub_val1).encode('utf-8')).hexdigest()
                hash1.append(cur_hash)
                hash1_src.append([idx, sub_val1])
                logging.debug("    hash1: %s", str(cur_hash))
                cur_hash = hashlib.sha256(json.dumps(sub_val2).encode('utf-8')).hexdigest()
                hash2.append(cur_hash)
                hash2_src.append([idx, sub_val2])
                logging.debug("    hash2: %s", str(cur_hash))
            else:
                if not other_contents_match(sub_val1, sub_val2, key):
                    logging.error('Iterable contents index %d don''t match for key "%s"', idx, key)
                    logging.error('  1. %s', (str(sub_val1)))
                    logging.error('  2. %s', (str(sub_val2)))
                    return False
                logging.debug("HACK: other Done matching OTHER")
        # Check any hashes we may have
        for idx, _ in enumerate(hash1):
            if not hash1[idx] in hash2:
                logging.error('Hashed iterable at index %d isn''t matched for key "%s"', hash1_src[idx][0], key)
                logging.error('  %s', hash1_src[idx][1])
                return False
        hash2_diff = list(set(hash2) - set(hash1))
        if hash2_diff:
            idx = hash2.index(hash2_diff[0])
            logging.error('Hashed iterable in second list at index %d not found in first list for key "%s"', idx, key)
            logging.error(' %s', hash2_src[idx][1])
            return False
    else:
        if val1 != val2:
            logging.error('Different values found for key "%s"', key)
            logging.error('  1. %s', str(val1))
            logging.error('  2. %s', str(val2))
            return False

    return True


def dict_contents_match(first: dict, second: dict) -> bool:
    """Compares the two dictionaries
    Arguments:
        first: the first data to check
        second: the second data to check
    """
    # Check keys
    first_keys = first.keys()
    for one_key in first_keys:
        if one_key not in second:
            logging.error('Key "%s" in first JSON isn\'t found in comparison json', one_key)
            return False
    if len(first_keys) != len(second.keys()):
        logging.error('The two JSON instances have different number of keys')
        return False

    # Check key values
    for one_key in first_keys:
        val1 = first[one_key]
        val2 = second[one_key]
        logging.debug('HACK:dict %s: Types %s %s', one_key, type(val1), type(val2))
        if not isinstance(val2, type(val2)):
            logging.error('Mismatch type for key "%s"', one_key)
            return False

        if isinstance(val1, dict):
            if not dict_contents_match(val1, val2):
                return False
        # Check for other iterable types and handle iterable, or other
        elif not other_contents_match(val1, val2, one_key):
            return False

    return True


def check_json(first_path: str, second_path: str) -> None:
    """Compares the two JSON files and throws an exception if they don't match
    Arguments:
        first_path: the path to the first file to compare
        second_path: the path to the second file to compare
    """
    with open(first_path, 'r', encoding='utf-8') as in_file:
        first = json.load(in_file)
    with open(second_path, 'r', encoding='utf-8') as in_file:
        second = json.load(in_file)

    # Loop through and compare the contents
    if not dict_contents_match(first, second):
        print("JSON files are not the same")
        logging.error("JSON files are not the same")
        sys.exit(1)


if __name__ == '__main__':
    path1, path2 = _get_params()
    check_json(path1, path2)
