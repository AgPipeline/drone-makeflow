#!/usr/bin/python3
"""Script for caching results from a transformer run
"""

import argparse
import json
import logging
import os
import shutil
from typing import Optional


def _find_results_files(source_path: str, search_depth: int = 2) -> list:
    """Looks for results.json files in the path specified
    Arguments:
        source_path: the path to use when looking for result files
        search_depth: the maximum folder depth to search
    Return:
        Returns a list containing found files
    Notes:
        A search depth of less than 2 will not recurse into sub-folders; a search depth of 2 will only recurse into
        immediate sub-folders and no deeper; a search depth of 3 will recurse into the sub-folders of sub-folders; and
        so on
    """
    res_name = 'results.json'
    res_name_len = len(res_name)

    # Common expression declared once outside of recursion
    # Checks that the file name matches exactly the testing string (res_name)
    name_check_passes = lambda name: name.endswith(res_name) and os.path.isdir(name[:-res_name_len])

    if not source_path:
        return []

    # Declare embedded function to do the work
    def perform_recursive_find(path: str, depth: int) -> list:
        """Recursively finds results files
        Arguments:
            path: the path to check for results files
            depth: the maximum folder depth to recurse (starting at 1)
        Return:
            Returns a list of found files
        """
        return_list = []

        # Basic checks
        if os.path.isfile(path):
            if name_check_passes(path):
                logging.debug("Result file check specified result file: '%s'", path)
                return [path]

            logging.debug("Result file check name is not valid: '%s'", path)
            return return_list

        # We only process folders after the above checks
        if not os.path.isdir(path):
            logging.debug("Error: result file check path is not a file or folder: '%s'", path)
            return return_list

        # Loop over current folder looking for other folders and for a results file
        for one_name in os.listdir(path):
            check_name = os.path.join(path, one_name)
            if name_check_passes(check_name):
                logging.debug("Found result file: '%s'", check_name)
                return_list.append(check_name)
            elif depth > 1 and os.path.isdir(check_name):
                logging.debug("Searching folder for result files: '%s'", check_name)
                found_results = perform_recursive_find(check_name, depth - 1)
                if found_results:
                    return_list.extend(found_results)

        return return_list

    # Find those files!
    return perform_recursive_find(source_path, search_depth)


def _get_path_maps(maps_param: str) -> Optional[dict]:
    """Parses the map parameter and returns a dictionary of mappings
    Arguments:
        maps_param: the parameter to parse into a mapping dictionary
    Return:
        A dict of mappings of they're found and valid, or None
    """
    if not maps_param:
        return None

    if ',' in maps_param:
        maps_list = maps_param.split(',')
    else:
        maps_list = [maps_param]

    # Build up the dict
    path_maps = {}
    for one_map in maps_list:
        if ':' in one_map:
            map_src, map_dst = one_map.split(':')
            map_src = map_src.rstrip('/\\')
            map_dst = map_dst.rstrip('/\\')
            path_maps[map_src] = map_dst
            logging.debug("Path map found: '%s' to '%s'", map_src, map_dst)
        else:
            logging.warning("Invalid mapping found and ignored: %s", one_map)

    if not path_maps:
        logging.info("Path mappings specified but none were found")
    return path_maps if path_maps else None


def _check_paths_errors(file_path: str, dir_path: str) -> str:
    """Performs checks on the file path and directory
    Arguments:
        file_path: path to the file to check
        dir_path: path to the directory to check
    Return:
        Returns an error string if a problem is found and None if everything checks out
    """
    error_msg = ""
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        error_msg += ("\n" if error_msg else "") + "Result file is invalid: '%s'" % str(file_path)
    if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
        error_msg += ("\n" if error_msg else "") + "Cache folder is invalid: '%s'" % str(dir_path)
    return error_msg if error_msg else None


def _combine_results(source_results: list, new_results: list) -> list:
    """Combines the specified dictionaries
    Arguments:
        source_results: the source dictionary to merge into
        new_results: the dictionary to add
    Return:
        Returns the combined dictionary
    Notes:
        Runtime parameters that evaluate to False are transparently handled (for example, receiving an empty dict
        runtime parameter will not raise an error and will return a list - which may also be empty)
    """
    if not source_results:
        source_results = []

    # Handle edge cases
    if not source_results:
        if not new_results:
            return []
        return new_results
    if not new_results:
        return source_results

    return source_results + new_results


def _map_path(file_path: str, path_maps: dict = None) -> str:
    """Looks up the path in the dictionary and maps that portion of the path to its replacement
    Arguments:
        file_path: the path to look into modifying
        path_maps: the dictionary of path mappings
    Return:
        The path to use. This is the original path if the starting path particle is not found in the mappings.
        Otherwise, the start of the path will be replaced as specified by the associated path_map value.
    Notes:
        No checks for best (maximal) fit is made; the first found match is the one that's used.
        White space is maintained; for example, '/usr/bin:/usr/local/bin ' will change '/usr/bin/x.sh' to
        '/usr/local/bin /x.sh'.
        Partial folder name mappings are not supported; for example, the path
        '/home/foo' will not match '/home/foobar' but will match '/home/foo' and '/home/foo/my_file.txt'
    """
    if not path_maps:
        return file_path

    # Loop through looking for a good match
    file_path_len = len(file_path)
    for one_path in path_maps:
        if file_path.startswith(one_path):
            path_len = len(one_path)
            if path_len == file_path_len:
                return file_path
            if path_len < file_path_len:
                sep_char = file_path[path_len]
                if sep_char in ['/', '\\']:
                    new_path = os.path.join(path_maps[one_path], file_path[path_len + 1:])
                    logging.info("Mapping file '%s' to '%s'", file_path, new_path)
                    return new_path

    logging.debug("No mapping found for: '%s", file_path)
    return file_path


def _strip_mapped_path(file_path: str, path_maps: dict = None) -> str:
    """Searches the path maps for a previously mapped path and strips it from the source path.
       The values in the path maps are used for comparison, not the keys.
    Arguments:
        file_path: the path to look into modifying
        path_maps: the dictionary of path mappings
    Return:
        The path with the starting matched part stripped when a match is found, otherwise the original file_path
    """
    if not path_maps:
        return file_path

    # Loop through looking for a matching path
    file_path_len = len(file_path)
    for _, one_path in path_maps.items():
        if file_path.startswith(one_path):
            path_len = len(one_path)
            if path_len == file_path_len:
                logging.debug("Full path match for stripping folder mapping, returning empty string")
                return ""
            if path_len < file_path_len:
                sep_char = file_path[path_len]
                if sep_char in ['/', '\\']:
                    new_path = file_path[path_len + 1:]
                    logging.info("Stripping mapped file '%s' to '%s'", file_path, new_path)
                    return new_path

    logging.debug("No mapped path found for: '%s", file_path)
    return file_path


def _save_result_metadata(metadata_file: str, metadata: dict) -> None:
    """Saves the container's metadata to the specified file path.
    Arguments:
        metadata_file: the path to save the metadata to
        metadata: the metadata to save
    Notes:
        Looks for a 'replace' key to determine if the metadata is appended to existing metadata or not (as
        specified by the file name passed in). If 'replace' is missing, or evaluates to False, any existing metadata
        is replaced. Otherwise the metadata is appended to the end of the file - the current file contents are not
        loaded first.
        A 'data' key is looked for as an indication of what metadata to save. If a 'data' key isn't specified, the
        entire metadata parameter is written to the file.
    """
    append = False

    write_metadata = metadata if 'data' not in metadata else metadata['data']

    # If the metadata file already exists, check what the caller wants to have happen (see Notes in docstring)
    if os.path.exists(metadata_file):
        if 'replace' in metadata:
            append = not metadata['replace']

    with open(metadata_file, "a" if append else "w") as out_file:
        if append:
            out_file.write(',')
        json.dump(write_metadata, out_file, indent=2)


def cache_files(result_files: dict, cache_dir: str, path_maps: dict = None, file_handlers: dict = None) -> list:
    """Copies any files found in the results to the cache location
    Arguments:
        result_files: the dictionary of files to copy
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
        file_handlers: special handling of files instead of normal copy
    Return:
        Returns a list of copied files
    """
    # Loop through and build up a list of files to copy
    copied_files = []
    copy_list = []
    total_count = 0
    problem_count = 0
    skip_count = 0
    for one_file in result_files:
        if 'path' in one_file:
            total_count += 1
            source_path = _map_path(one_file['path'], path_maps)
            if os.path.exists(source_path):
                dest_path = os.path.join(cache_dir, os.path.basename(one_file['path']))
                copy_info = {'src': source_path, 'dst': dest_path}
                if 'metadata' in one_file:
                    copy_info['metadata'] = one_file['metadata']
                copy_list.append(copy_info)
            else:
                logging.warning("File is missing and will not be copied: '%s'", one_file['path'])
                problem_count += 1
        else:
            logging.debug("File entry is missing 'path' key to file: %s", str(one_file))
            logging.debug("    skipping file entry")
            skip_count += 1

    # Don't copy anything if we've found a problem
    if problem_count:
        msg = "Found %s missing files out of %s; stopping processing" % (str(problem_count), str(total_count))
        logging.error(msg)
        raise RuntimeError(msg)

    # Other messages
    if skip_count:
        logging.info("Skipping %s entries that are missing the 'path' key", str(skip_count))

    # Copy the files
    for one_file in copy_list:
        file_ext = os.path.splitext(one_file['src'])[1]
        file_metadata = one_file['metadata'] if 'metadata' in one_file else None

        if file_handlers and file_ext and file_ext in file_handlers:
            file_handlers[file_ext](one_file['src'], cache_dir, file_metadata)
        else:
            logging.debug("Copy file: '%s' to '%s'", str(one_file['src']), str(one_file['dst']))
            shutil.copyfile(one_file['src'], one_file['dst'])
            if file_metadata:
                metadata_file_name = os.path.splitext(one_file['dst'])[0] + '.json'
                logging.debug("Saving metadata to file: %s", metadata_file_name)
                _save_result_metadata(metadata_file_name, file_metadata)
            copied_files.append(one_file['dst'])

    return copied_files


def cache_containers(container_list: list, cache_dir: str, path_maps: dict = None, file_handlers: dict = None) -> list:
    """Searches the list of containers for files to copy and copies them to a folder in the cache_dir.
       The folders are named after the container name.
    Arguments:
        container_list: the list of containers to search
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
        file_handlers: special handling of files instead of normal copy
    Return:
        Returns a list of copied files
    """
    file_list = []

    for container in container_list:
        if 'name' in container:
            working_dir = os.path.join(cache_dir, container['name'])
            try:
                os.makedirs(working_dir, exist_ok=True)
            except FileExistsError:
                # Directory already exists
                pass

            # Save metadata
            container_metadata_path = None
            if 'metadata' in container:
                container_metadata_path = os.path.join(cache_dir, container['name'] + '.json')
                _save_result_metadata(container_metadata_path, container['metadata'])

            # Copy files
            for key in ['file', 'files']:
                if key in container:
                    copied_files = cache_files(container[key], working_dir, path_maps, file_handlers)
                    if copied_files:
                        file_list.append({'files': copied_files, 'metadata_path': container_metadata_path})
                    break

    return file_list


def _append_metadata_to_file(metadata: dict, metadata_file: str) -> None:
    """Appends metadata to a file as a JSON array element
    Arguments:
        metadata: the metadata to store in the file
        metadata_file: path to the metadata file to save to
    """
    write_metadata = metadata if 'data' not in metadata else metadata['data']

    if not os.path.exists(metadata_file):
        with open(metadata_file, "w") as out_file:
            out_file.write("{\n[\n")
            json.dump(write_metadata, out_file, indent=2)
            out_file.write("]\n}\n")
    else:
        reverse_find_chars = '}]}'
        with open(metadata_file, "a+") as out_file:
            try:
                for one_char in reverse_find_chars:
                    found_char = False
                    while not found_char:
                        os.lseek(out_file.fileno(), -1, os.SEEK_END)
                        if out_file.buffer.peek().decode('utf-8').startswith(one_char):
                            found_char = True
            except Exception as ex:
                msg = "Unable to find end of metadata to append to in file: '%s'" % metadata_file
                logging.error(msg)
                if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
                    logging.error("Exception caught")
                raise RuntimeError("Unable to append metadata to file") from ex

            # Truncate the file and write out the new metadata
            out_file.truncate()
            out_file.write("},\n")
            json.dump(write_metadata, out_file, indent=2)
            out_file.write("]\n}\n")


def _handle_csv_merge(csv_path: str, cache_dir: str, metadata: dict = None, header_lines: int = 0) -> None:
    """Handles merging CSV files into a file off the specified cache folder
    Arguments:
        csv_path: the path to the source CSV file
        cache_dir: the path to the cache to store CSV data
        metadata: optional metadata associated with the file
        header_lines: the number of header lines in the source CSV file (headers are discarded after first CSV file)
    Exceptions:
        Exceptions may be raised when accessing the file system or reading the CSV file
    """
    # Generate the destination filename
    dest_file = os.path.join(cache_dir, os.path.basename(csv_path))

    # If the destination isn't there, just copy the file. Otherwise assume it's configured correctly and copy content
    if not os.path.exists(dest_file):
        shutil.copyfile(csv_path, dest_file)
    else:
        with open(dest_file, "a") as out_file:
            # We don't use shutil.copyfileobj to allow for ending line break (aka: newline, carriage return, etc)
            with open(csv_path, "r") as in_file:
                for line in in_file:
                    # Skip over headers
                    while header_lines > 0:
                        header_lines -= 1
                        continue
                    # Write the data line: ensure we have one newline
                    out_file.write(line.strip('\n') + '\n')

    # If we have metadata merge it with existing metadata
    if metadata:
        metadata_file = os.path.splitext(dest_file)[0] + '.json'
        _append_metadata_to_file(metadata, metadata_file)


def _check_get_parameters(args: argparse.Namespace) -> dict:
    """Checks that the parameters were specified and are available
    Arguments:
        args: the command line parameters to use
    Return:
        Returns a dict that contains the named parameters
    Exception:
        Raises RuntimeError if a problem is found
    """
    # Check that we have a valid file and folder
    error_msg = _check_paths_errors(args.results_file, args.cache_folder)
    if error_msg:
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Load the contents of the results
    with open(args.results_file, "r") as in_file:
        results = json.load(in_file)

    # Loop through and copy any files (without sub-paths)
    return_dict = {'result_containers': None, 'result_files': None, 'cache_dir': None}

    # Loop through and copy any files (without sub-paths)
    if os.path.isdir(args.results_file):
        results_files = _find_results_files(args.results_file)
    else:
        results_files = [args.results_file]

    for one_file in results_files:
        with open(one_file, "r") as in_file:
            results = json.load(in_file)

        # Look for containers first
        found_containers = None
        for key in ['container', 'containers']:
            if key in results:
                found_containers = results[key]
                return_dict['result_containers'] = _combine_results(return_dict['result_containers'], found_containers)
                break
        if found_containers is None:
            logging.info("No containers found in results: '%s'", one_file)

        # Look file top-level files
        found_files = None
        for key in ['file', 'files']:
            if key in results:
                found_files = results[key]
                return_dict['result_files'] = _combine_results(return_dict['result_files'], found_files)
                break
        if found_files is None:
            logging.info("No top-level files found in results: '%s'", one_file)

    # Prepare the mappings
    mappings = None
    if args.maps:
        mappings = _get_path_maps(args.maps)

    # Determine if we have special handlers to configure
    file_handlers = {}
    if args.merge_csv:
        file_handlers['.csv'] = lambda source_file, cache_dir, metadata: _handle_csv_merge(source_file, cache_dir,
                                                                                           metadata, args.csv_header_lines)

    # Add in other fields
    return_dict['cache_dir'] = args.cache_folder
    return_dict['path_maps'] = mappings
    return_dict['file_handlers'] = file_handlers if file_handlers else None

    return return_dict


def cache_results(result_containers: list, result_files: dict, cache_dir: str, path_maps: dict = None, file_handlers: dict = None) -> None:
    """Handles caching the containers and files found in the results
    Arguments:
        result_containers: the dictionary of containers with files to copy
        result_files: the dictionary of files to copy
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
        file_handlers: special handling of files instead of normal copy
    """
    file_list = []

    # Handle containers first
    if result_containers:
        copied_files = cache_containers(result_containers, cache_dir, path_maps, file_handlers)
        if copied_files:
            file_list.extend(copied_files)

    # Handle any top-level files
    if result_files:
        copied_files = cache_files(result_files, cache_dir, path_maps, file_handlers)
        if copied_files:
            file_list.append({'files': copied_files})

    # Save the list of copied files for makeflow use
    makeflow_list_file = os.path.join(cache_dir, "cached_files_makeflow_list.jx")
    with open(makeflow_list_file, "w") as out_file:
        out_file.write('{\n  "FILE_LIST": [')
        separator = ""
        for one_set in file_list:
            definition_lines = []
            if 'metadata_path' in one_set:
                definition_lines.append('\"METADATA\": \"%s\"' % one_set['metadata_path'])
                definition_lines.append('\"METADATA_NAME\": \"%s\"' % _strip_mapped_path(one_set['metadata_path'], path_maps))
                definition_lines.append('\"BASE_METADATA_NAME\": \"%s\"' % os.path.splitext(os.path.basename(one_set['metadata_path']))[0])

            for one_file in one_set['files']:
                definition_lines.append('\"PATH\": \"%s\"' % one_file)
                definition_lines.append('\"NAME\": \"%s\"' % _strip_mapped_path(one_file, path_maps))
                definition_lines.append('\"BASE_IMAGE_NAME\": \"%s\"' % os.path.splitext(os.path.basename(one_file))[0])

            out_file.write('%s\n  {\n    %s\n  }' % (separator, ',\n    '.join(definition_lines)))
            separator = ','

        out_file.write('\n  ]\n}')


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Adds arguments to command line parser
    Parameters:
        parser: parser instance to add arguments to
    """
    parser.add_argument('--merge_csv', action='store_true', default=False,
                        help='merge same-name CSV files into one file of the same name (default=False)')
    parser.add_argument('--csv_header_lines', nargs='?', default=0,
                        help='expected number of header lines in any CSV file when merging CSV files (default=0)')
    parser.add_argument('--maps', nargs='?', type=str,
                        help='one or more comma separated folder mappings of <source path>:<destination path>')
    parser.add_argument('results_file', metavar='<results>', type=str,
                        help='the path to the results file to act upon')
    parser.add_argument('cache_folder', metavar='<cache>', type=str,
                        help='the path to cache the results into')

    parser.epilog = 'Mappings are exact character matches from the start of file paths; no checks are made to ensure complete' +\
                    ' folder names are matched. For example, a mapping of "/home/tom:/home/sue" will map the path "/home/tomorrow"' +\
                    ' to "/home/sueorrow".'


if __name__ == "__main__":
    # Setup command line parameters and parse them
    PARSER = argparse.ArgumentParser(description="Handles results for pipeline Docker containers by copying files and saving metadata")
    add_arguments(PARSER)
    ARGS = PARSER.parse_args()

    # Process the results
    PARAMS = _check_get_parameters(ARGS)
    cache_results(**PARAMS)
