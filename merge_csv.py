#!/usr/bin/env python3
"""Python script merging CSV files into a root folder
"""

import argparse
import os
import shutil


def _merge_csv(source_path: str, target_path: str, has_headers: bool = True, header_count: int = 1) -> None:
    """Merges the source CSV file into the target CSV file
    Arguments:
        source_path: path to the source CSV file
        target_path: path of CSV file to merge into
        has_headers: source files have headers when set to True, otherwise there's no headers
        header_count: the number of header lines in the source file
    """
    # Read in the lines and append to the output file
    skip_lines = header_count if has_headers else 0
    with open(target_path, 'a') as out_file:
        with open(source_path, 'r') as infile:
            # Read in a line, return if everything was read and skip over headers
            one_line = infile.readline()
            while one_line:
                if skip_lines <= 0:
                    # Write to the output file
                    if not one_line.endswith('\n'):
                        one_line = one_line + '\n'
                    out_file.write(one_line)
                else:
                    skip_lines -= 1

                # Read in the next line
                one_line = infile.readline()


def get_arg_parser() -> argparse.ArgumentParser:
    """Prepares the command line argument parser
    Return:
        Returns the argument parser instance
    """
    def dir_type(dir_path: str) -> str:
        """Checks if the path is a folder
        Parameters:
            dir_path: path to a folder
        Return:
            Returns the path of a valid folder
        Exceptions:
            Raises a argparse.ArgumentTypeError if the path is not a folder
        """
        if os.path.isdir(dir_path):
            return dir_path
        raise argparse.ArgumentTypeError('Folder %s is not available or is not valid' % str(dir_path))

    parser = argparse.ArgumentParser('CSV File discovery and merging')

    parser.add_argument('--no_header', '-n', action='store_const', default=False, const=True,
                        help='source CSV files do not have a header')
    parser.add_argument('--header_count', '-c', type=int, default=1, help='number of header lines in files')
    parser.add_argument('--filter', '-f', help='comma separated list of files to filter in')
    parser.add_argument('--ignore', '-i', help='comma separated list of files to ignore')
    parser.add_argument('source_folder', type=dir_type, help='the folder to search in')
    parser.add_argument('target_folder', type=dir_type, help='folder for combined CSV files')

    return parser


def merge():
    """Discovers and merges CSV files
    """
    args = get_arg_parser().parse_args()

    # Prepare any filters for inclusion or exclusion
    have_headers = not args.no_header
    includes = [one_name.strip() for one_name in args.filter.split(',')] if args.filter else []
    excludes = [one_name.strip() for one_name in args.ignore.split(',')] if args.ignore else []

    # Loop through the folders until we run out of folders to process
    # This list only contains complete paths
    check_dirs = [os.path.realpath(args.source_folder)]
    while check_dirs:
        next_dir = check_dirs.pop(0)
        for one_file in os.listdir(next_dir):
            source_path = os.path.join(next_dir, one_file)

            # If it's a folder, save it for recursion
            if os.path.isdir(source_path):
                check_dirs.append(source_path)
                continue

            # Ignore non-CSV files
            if os.path.splitext(one_file)[1].lower() != '.csv':
                continue

            # Get the target path and see if the source and destination are the same
            dest_path = os.path.join(args.target_folder, os.path.basename(one_file))
            if dest_path.lower() == source_path.lower():
                continue

            # Skip over any file not included or explicitly excluded
            if includes:
                if one_file not in includes:
                    continue
            if excludes:
                if one_file in excludes:
                    continue

            _merge_csv(source_path, dest_path, have_headers, args.header_count)


if __name__ == "__main__":
    merge()
    exit()