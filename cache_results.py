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
    print('Usage: %s [--maps <folder mappings>] <results file> <cache folder>' % str(app_name))
    print('  --maps <folder mappings> specifies one or more folder mappings')
    print('  <results file> the file containing the results to interpret')
    print('  <cache folder> is the destination for the copied results')
    print('')
    print('Folder mappings are a comma separated list of source:dest mapping strings.')
    print('For example: /root/foo:/home/user/bar will map folders from "/root/foo" to "/home/user/bar"')
    print('All spaces are maintained when mapping paths')


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


def _get_path_maps(maps_param: str) -> dict:
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


def _check_get_parameters(params: list) -> dict:
    """Checks that the parameters were specified and available
    Arguments:
        params: the list of parameters to use (only the first two unflagged parameters are used)
    Return:
        Returns a dict that contains the named parameters
    Exception:
        Raises RuntimeError if a problem is found
    """
    num_params = len(params)
    if num_params < 3:
        raise RuntimeError("Parameters are missing, use the '--help' parameter for usage information")

    results_file = None
    cache_dir = None
    path_maps = None
    idx = 1
    while idx < num_params:
        if params[idx] and params[idx][0] == '-':
            if params[idx] == "--maps":
                idx += 1
                if idx >= num_params:
                    raise RuntimeError("--maps flag specified without a value")
                path_maps = _get_path_maps(params[idx])
            else:
                logging.warning("Unknown flag specified: %s", str(params[idx]))
        else:
            # Only get the first two non-flag parameters & ignore the rest
            if results_file is None:
                results_file = params[idx]
            elif cache_dir is None:
                cache_dir = params[idx]
        idx += 1

    # Check that we have a valid file and folder
    error_msg = _check_paths_errors(results_file, cache_dir)
    if error_msg:
        logging.error(error_msg)
        raise RuntimeError(error_msg)

    # Load the contents of the results
    with open(results_file, "r") as in_file:
        results = json.load(in_file)

    # Loop through and copy any files (without sub-paths)
    return_dict = {'result_containers': None, 'result_files': None, 'cache_dir': None}

    # Look for containers first
    for key in ['container', 'containers']:
        if key in results:
            return_dict['result_containers'] = results[key]
            return_dict['cache_dir'] = cache_dir
            break
    if return_dict['result_containers'] is None:
        logging.info("No containers found in results")

    for key in ['file', 'files']:
        if key in results:
            return_dict['result_files'] = results[key]
            return_dict['cache_dir'] = cache_dir
            break
    if return_dict['result_files'] is None:
        logging.info("No top-level files found in results")

    # Add in other fields
    return_dict['path_maps'] = path_maps

    return return_dict


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
            append = True

    with open(metadata_file, "a" if append else "w") as out_file:
        if append:
            out_file.write(',')
        json.dump(write_metadata, out_file, indent=2)


def cache_files(result_files: dict, cache_dir: str, path_maps: dict = None) -> list:
    """Copies any files found in the results to the cache location
    Arguments:
        result_files: the dictionary of files to copy
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
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
        logging.debug("Copy file: '%s' to '%s'", str(one_file['src']), str(one_file['dst']))
        shutil.copyfile(one_file['src'], one_file['dst'])
        if 'metadata' in one_file:
            metadata_file_name = os.path.splitext(one_file['dst'])[0] + '.json'
            _save_result_metadata(metadata_file_name, one_file['metadata'])
        copied_files.append(one_file['dst'])

    return copied_files


def cache_containers(container_list: list, cache_dir: str, path_maps: dict = None) -> list:
    """Searches the list of containers for files to copy and copies them to a folder in the cache_dir.
       The folders are named after the container name.
    Arguments:
        container_list: the list of containers to search
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
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
            container_metadata_name = None
            if 'metadata' in container:
                container_metadata_name = os.path.join(cache_dir, container['name'] + '.json')
                _save_result_metadata(container_metadata_name, container['metadata'])

            # Copy files
            for key in ['file', 'files']:
                if key in container:
                    copied_files = cache_files(container[key], working_dir, path_maps)
                    if copied_files:
                        file_list.extend({'files': copied_files, 'metadata': container_metadata_name})
                    break

    return file_list


def cache_results(result_containers: list, result_files: dict, cache_dir: str, path_maps: dict = None) -> None:
    """Handles caching the containers and files found in the results
    Arguments:
        result_containers: the dictionary of containers with files to copy
        result_files: the dictionary of files to copy
        cache_dir: the location to copy the files to
        path_maps: path mappings to use on file paths
    """
    file_list = []

    # Handle containers first
    if result_containers:
        copied_files = cache_containers(result_containers, cache_dir, path_maps)
        if copied_files:
            file_list.extend(copied_files)

    # Handle any top-level files
    if result_files:
        copied_files = cache_files(result_files, cache_dir, path_maps)
        if copied_files:
            file_list.append({'files': copied_files})

    # Save the list of copied files for makeflow use
    makeflow_list_file = os.path.join(cache_dir, "cached_files_makeflow_list.jx")
    with open(makeflow_list_file, "w") as out_file:
        out_file.write('{\n  "FILE_LIST": [')
        separator = ""
        for one_set in file_list:
            metadata_line = ""
            if 'metadata' in one_set:
                metadata_line = '\n    \"METADATA\": \"%s\",\n' % one_set['metadata']

            for one_file in one_set['files']:
                out_file.write('%s\n  {\n%s    \"PATH\": \"%s\",\n    \"NAME\": \"%s\"\n  }' % \
                               (separator, metadata_line, one_file, _strip_mapped_path(one_file, path_maps)))
                separator = ','
            out_file.write('\n  ]\n}')


if __name__ == "__main__":
    # Get the command line arguments and check if help was specified
    ARGS = sys.argv
    if _check_print_help(ARGS):
        sys.exit(0)

    # Process the results
    PARAMS = _check_get_parameters(ARGS)
    cache_results(**PARAMS)
