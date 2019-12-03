#!/usr/bin/python3
"""Script for caching results from a transformer run
"""

import json
import logging
import os
import shutil
import sys


def _print_help(app_name: str = None) -> None:
    """Prints the help for the script
    Arguments:
        app_name: the name to use for the application name. If None, executing file name is used
    """
    if not app_name:
        app_name = os.path.basename(__file__)
    print('Usage: %s <results file> <cache folder>' % str(app_name))
    print('  <results file> the file containing the results to interpret')
    print('  <cache folder> is the destination for the copied results')


def _check_print_help(params: list) -> bool:
    """Checks if help was specified in the parameters
    Arguments:
        params: the list of parameters to check
    Return:
        Returns True if help was requested (resulting in help being printed) and
        False if help wasn't found in the parameters
    """
    # Look through the parameters
    if params:
        help_found = False
        for one_param in params:
            if one_param in ['-h', '--help']:
                help_found = True
                break
    else:
        help_found = True

    # Display help if requested
    if help_found:
        app_name = None
        if params:
            if params[0] and params[0] not in ['-c']:
                app_name = os.path.splitext(os.path.basename(__file__))[0]
        _print_help(app_name)

    return help_found


def _check_get_parameters(params: list) -> dict:
    """Checks that the parameters were specified and available
    Arguments:
        params: the list of parameters to use; only index 1 and 2 are used
    Return:
        Returns a dict that contains the named parameters
    Exception:
        Raises RuntimeError if a problem is found
    """
    num_params = len(params)
    if num_params < 3:
        raise RuntimeError("Parameters are missing, use the '--help' parameter for usage information")
    results_file = params[1]
    cache_dir = params[2]

    # Check that we have a valid file and folder
    error_msg = ""
    if not os.path.exists(results_file) or not os.path.isfile(results_file):
        error_msg += ("\n" if error_msg else "") + "Result file is invalid: '%s'" % str(results_file)
    if not os.path.exists(cache_dir) or not os.path.isdir(cache_dir):
        error_msg += ("\n" if error_msg else "") + "Cache folder is invalid: '%s'" % str(cache_dir)
    if error_msg:
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Load the contents of the results
    with open(results_file, "r") as in_file:
        results = json.load(in_file)

    # Loop through and copy any files (without sub-paths)
    return_dict = {'result_files': None, 'cache_dir': None}
    if 'files' in results:
        return_dict['result_files'] = results['files']
        return_dict['cache_dir'] = cache_dir
    else:
        logging.info("No files specified in results. Nothing copied")

    return return_dict


def cache_files(result_files: dict, cache_dir: str) -> None:
    """Copies any files found in the results to the cache location
    Arguments:
        result_files: the dictionary of files to copy
        cache_dir: the location to copy the files to
    """
    # Loop through and build up a list of files to copy
    copy_list = []
    total_count = 0
    problem_count = 0
    skip_count = 0
    for one_file in result_files:
        if 'path' in one_file:
            total_count += 1
            if os.path.exists(one_file['path']):
                dest_path = os.path.join(cache_dir, os.path.basename(one_file['path']))
                copy_list.append({'src': one_file['path'], 'dst': dest_path})
            else:
                logging.warning("File is missing and will not be copied: '%s'", one_file['path'])
                problem_count += 1
        else:
            logging.debug("File entry is missing 'path' key to file: %s", str(one_file))
            logging.debug("    skipping file entry")
            skip_count += 1

    # Don't copy anything if we've found a problem
    if problem_count:
        msg = "Found %s missing files out of %s; stopping processing", str(problem_count), str(total_count)
        logging.error(msg)
        raise RuntimeError(msg)

    # Other messages
    if skip_count:
        logging.info("Skipping %s entries that are missing the 'path' key", str(skip_count))

    # Copy the files
    for one_file in copy_list:
        logging.debug("Copy file: '%s' to '%s'", str(one_file['src']), str(one_file['dst']))
        shutil.copyfile(one_file['src'], one_file['dst'])


if __name__ == "__main__":
    # Get the command line arguments and check if help was specified
    ARGS = sys.argv
    if _check_print_help(ARGS):
        sys.exit(0)

    # Process the results
    PARAMS = _check_get_parameters(ARGS)
    cache_files(**PARAMS)
