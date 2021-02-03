#!/usr/bin/env python3
"""Python script for converting BETYdb plot outlines to GeoJSON format
"""

import argparse
import os
import subprocess

# The default file extension to look for
DEFAULT_FILE_EXT = '.tif'


def get_arguments() -> argparse.Namespace:
    """Adds arguments to the command line parser
    Return:
        Returns the parsed arguments
    """
    parser = argparse.ArgumentParser(description="Checking plotclip results",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-e', '--file-ext',
                        help='the case-insensitive extension of the image files to find; defaults to ' + DEFAULT_FILE_EXT,
                        type=str, default=DEFAULT_FILE_EXT)
    parser.add_argument('-n', '--no-recurse', default=False, action='store_true',
                        help='do not check subfolders for files; default is to check subfolders; implies -t')
    parser.add_argument('-t', '--top-folder', default=False, action='store_true',
                        help='check the top level folders for matching files; default is to skip top folder checks')
    parser.add_argument('truth_folder', type=str,
                        help='path to the top level folder containing the files to use for comparison')
    parser.add_argument('check_folder', type=str,
                        help='path to the top level folder containing the file to check')

    args = parser.parse_args()

    return args


def compare_file_contents(source_file: str, compare_file: str) -> bool:
    """Compares the source file against the comparison file for differences
    Arguments:
        source_file: the file that is checked against
        compare_file: the file that is compared against the source_file
    Returns:
        Returns True if the files are considered the same, and False if they are not
    """
    cmd = ['diff', '--brief', source_file, compare_file]
    res = subprocess.run(cmd, capture_output=True, check=True)
    return len(res.stdout) == 0


def find_compare_files(truth_folder: str, compare_folder: str, file_ext: str, check_subfolders: bool = True) -> None:
    """Searches the folders for files with the matching extension and compares the contents
    Arguments:
        truth_folder: the folder containing the copies that are the truth
        compare_folder: the folder to compare the truth files against
        file_ext: the file extension to look for
        check_subfolders: also look for files in the subfolders off the truth_folder
    Exceptions:
        Throws a RuntimeError when an image file doesn't match the expected contents, or isn't found in
        the compare folder
    Notes:
        The truth_folder is searched for matching file extensions, the compare_folder is not. This means
        that additional matching files in the compare_folder are ignored
    """
    # Initialize folders to check with the top-level folder
    check_folders = [""]
    # Make sure the extension is in the correct format
    check_ext = file_ext.lower() if file_ext[0] == '.' else '.' + file_ext.lower()

    # While we have folders to process
    while len(check_folders) > 0:
        cur_subpath = check_folders.pop(0)
        cur_truth = os.path.join(truth_folder, cur_subpath)
        cur_compare = os.path.join(compare_folder, cur_subpath)

        # Check truth folder for matching files and sub-folders
        for one_file in os.listdir(cur_truth):
            if os.path.splitext(one_file)[1].lower() == check_ext:
                if not os.path.exists(os.path.join(cur_compare, one_file)):
                    raise RuntimeError('Unable to find expected file "%s"' % os.path.join(cur_subpath, one_file))
                if not compare_file_contents(os.path.join(cur_truth, one_file), os.path.join(cur_compare, one_file)):
                    raise RuntimeError('File content mismatch "%s"' % os.path.join(cur_subpath, one_file))
            elif check_subfolders and os.path.isdir(os.path.join(cur_truth, one_file)):
                # Queue the subfolder for later comparison
                check_folders.append(os.path.join(cur_subpath, one_file))


def check_details() -> None:
    """Checks the plot clipping details to ensure that the contents of the clipped plots
       match what's expected
    Exceptions:
        A RuntimeError is thrown when an image file doesn't match the expected contents, or there's
        a folder content mismatch
    Notes:
        The truth_folder is searched for matching file extensions, the compare_folder is not. This means
        that additional matching files in the compare_folder are ignored
    """
    # Get the command line parameters
    args = get_arguments()

    # Check the folder parameters
    bad_folders = []
    if not os.path.exists(args.truth_folder):
        bad_folders.append(args.truth_folder)
    if not os.path.exists(args.check_folder):
        bad_folders.append(args.check_folder)
    if len(bad_folders) > 0:
        raise ValueError("Please correct folder paths and try again: %s" %
                         ",".join(['"' + folder + '"' for folder in bad_folders]))

    # Start searching folders
    if args.no_recurse or args.top_folder:
        find_compare_files(args.truth_folder, args.check_folder, args.file_ext, False)
    else:
        for one_file in os.listdir(args.truth_folder):
            cur_path = os.path.join(args.truth_folder, one_file)
            if os.path.isdir(cur_path):
                test_path = os.path.join(args.check_folder, one_file)
                find_compare_files(cur_path, test_path, args.file_ext)


if __name__ == "__main__":
    check_details()
