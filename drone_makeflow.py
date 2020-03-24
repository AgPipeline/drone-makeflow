"""Handles preparing and starting a makeflow run
"""

from copy import deepcopy
import datetime
import json
import logging
import os
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Union, Optional
import yaml
import requests

import pyclowder.connectors as connectors
import pyclowder.datasets as datasets
import pyclowder.files as files
import terrautils.extractors as extractors
from terrautils.secure import encrypt_pipeline_string

# Timeouts relating to processing
PROC_WAIT_SLEEP_SEC = 5  # Amount of time to sleep before checking process status
PROC_WAIT_TOTAL_SEC = 24 * 60 * 60  # Total wait time for process to finish
PROC_COMMUNICATE_TIMEOUT_SEC = 2  # Number of seconds to wait for a communicate call to complete

# Access permissions for folders we create
CREATED_FOLDER_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |\
                             stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH

# Name of mount point on Docker images
IMAGE_MOUNT_POINT_NAME = '/mnt/'

# Result file names
WORKFLOW_STEP_RESULT_FILE_NAME = 'result.json'                      # Results from a workflow step
WORKFLOW_STEP_CACHE_FILE_NAME = 'cached_files_makeflow_list.json'   # Results from caching a workflow step

# docker run --network pipeline_clowder -v /var/run/docker.sock:/var/run/docker.sock -v "testing:/mnt" --user root
# -e 'RABBITMQ_URI=amqp://rabbitmq/%2F' -e 'RABBITMQ_EXCHANGE=terra' -e 'TZ=/user/share/zoneinfo/US/Central' -e
# "PIPELINE_KEY=\x84\n'\x08\xbd\\\xef\xe1\x00\r\xe5\xf6=\x80\x1c\xc6\xd1o\xc3\xad\\:\xce\x92\x14^\xf0\x8c\xf4\x1c\`\x0b"
# -e 'WORKING_SPACE=/mnt' -e 'NAMED_VOLUME=testing' -d --restart=always --name=extractor-dronemakeflow chrisatua/development:drone_makeflow


def _preprocess_canopy_cover_json(env: dict, json_file: str) -> str:
    """Preprocesses canopy cover JSON files
    Arguments:
        env: runtime environment for commands
        files: list of JSON files to preprocess
    """
    dest_dir = os.path.join(env['BASE_DIR'], env['DATA_FOLDER_NAME'].lstrip('/'))
    return_filename = json_file
    logging.debug("Looking into canopy cover makeflow preprocess file: '%s' to folder '%s'", json_file, dest_dir)
    try:
        new_json = None
        with open(json_file, 'r') as in_file:
            target_json = json.load(in_file)
            logging.debug("Checking for FILE_LIST key in %s", str(target_json.keys()))
            if 'FILE_LIST' in target_json:
                new_json = []
                for one_file in target_json['FILE_LIST']:
                    logging.debug("Looking for METADATA in %s", str(one_file))
                    if 'METADATA' in one_file:
                        logging.debug("Adding to new JSON")
                        new_json.append(one_file)

        if new_json is not None:
            new_json_file = os.path.join(dest_dir, WORKFLOW_STEP_CACHE_FILE_NAME)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
            logging.debug("Saving new JSON to '%s' with %s entries", new_json_file, str(len(new_json)))
            with open(new_json_file, 'w') as out_file:
                json.dump({'FILE_LIST': new_json}, out_file)
                return_filename = new_json_file
        else:
            logging.debug("No new data stored")

    except Exception as ex:
        msg = "Ignoring exception while pre processing canopy cover JSON file: '%s' %s" % (json_file, str(ex))
        logging.debug(msg)
        logging.exception(msg)

    return return_filename

WORKFLOW = [
    {
        'name': 'OpenDroneMap',                                 # Name of the workflow step
        'makeflow_file': 'odm_workflow.jx',                     # The makeflow file to use
        'docker_version_number': '2.0',                         # The version of the docker image to use
        'arguments': None,                                      # Additional arguments for makeflow command
        'return_code_success': lambda code: int(code) == 0,     # Function that indicates success based upon return code
        'force_dataset': True,                                  # Force the output to a dataset if not specified
        'dataset_name_template': '{date}_{experiment}_{name}'   # Template for dataset names
    },
    {
        'name': 'Soil Mask',                                    # Name of the workflow step
        'makeflow_file': 'soil_mask_workflow.jx',               # The makeflow file to use
        'docker_version_number': '2.0',                         # The version of the docker image to use
        'arguments': None,                                      # Additional arguments for makeflow command
        'return_code_success': lambda code: int(code) == 0,     # Function that indicates success based upon return code
        'force_dataset': False,                                 # Force the output to a dataset if not specified
        'dataset_name_template': '{date}_{experiment}_{name}'   # Template for dataset names
    },
    {
        'name': 'Plot Clip',                                    # Name of the workflow step
        'makeflow_file': 'plot_clip_workflow.jx',               # The makeflow file to use
        'docker_version_number': '2.0',                         # The version of the docker image to use
        'arguments': None,                                      # Additional arguments for makeflow command
        'return_code_success': lambda code: int(code) == 0,     # Function that indicates success based upon return code
        'force_dataset': False,                                 # Force the output to a dataset if not specified
        'dataset_name_template': '{date}_{experiment}_{name}'   # Template for dataset names
    },
    {
        'name': 'Canopy Cover',                                 # Name of the workflow step
        'makeflow_file': 'canopy_cover_workflow.jx',            # The makeflow file to use
        'docker_version_number': '1.0',                         # The version of the docker image to use
        'arguments': None,                                      # Additional arguments for makeflow command
        'return_code_success': lambda code: int(code) == 0,     # Function that indicates success based upon return code
        'force_dataset': False,                                 # Force the output to a dataset if not specified
        'dataset_name_template': '{date}_{experiment}_{name}',  # Template for dataset names
        'preprocess_json': _preprocess_canopy_cover_json,       # Function for preprocessing JSON
        'copy_cached_folders': True,                            # Do we copy cached folders from previous step
        'use_extended_results_path': True,                      # Use a path specifier for results that's not the default
        'discover_run_results': True                            # Perform a folder search for results file instead of the default
    }
]


class __internal__():
    """Internal use class"""
    def __init__(self):
        """Initializes class instance"""

    @staticmethod
    def prepare_metadata(host: str, version: str, creator_name: str, metadata: dict, target_id: str, target_is_dataset: bool = True) -> dict:
        """Prepares the metadata as JSONLD if it isn't already
        Arguments:
            host: the host for the metadata
            version: the version associated with the metadata
            creator_name: name to associate with the metadata
            metadata: the metadata to fix up
            target_id: the Clowder ID of the metadata target
            target_is_dataset: True indicates the target_id is a dataset, and False a file
        Return:
            Returns the JSONLD compatible metadata
        """
        if '@context' in metadata:
            return metadata

        context = ["https://clowder.ncsa.illinois.edu/contexts/metadata.jsonld"]

        return_md = {
            "@context": context,
            "content": metadata,
            "agent": {
                "@type": "cat:extractor",
                "extractor_id": host + ("" if host.endswith("/") else "/") + "api/extractors/" + creator_name,
                "version": version,
                "name": creator_name
            }
        }

        if target_is_dataset:
            return_md['dataset_id'] = target_id
        else:
            return_md['file_id'] = target_id

        def clean_md(clean_metadata: dict) -> dict:
            """Cleans up the copied metadata
            Arguments:
                clean_metadata: the metadata to clean
            Return:
                The cleaned up metadata
            Notes:
                Replaces None values with an empty string
            """
            for key in clean_metadata.keys():
                if clean_metadata[key] is None:
                    clean_metadata[key] = ''
                elif isinstance(clean_metadata[key], dict):
                    clean_metadata[key] = clean_md(clean_metadata[key])
                if '.' in key:
                    new_key = key.replace('.', '_')
                    clean_metadata[new_key] = clean_metadata[key]
                    clean_metadata.pop(key)
            return clean_metadata

        return clean_md(return_md)

    @staticmethod
    def create_folder_default_perms(folder_path: str) -> None:
        """Convenience function for creating folders with the correct permissions
        Arguments:
            folder_path: the path to the folder to create
        """
        logging.debug("HACK: Creating folder at '%s':", folder_path)
        os.makedirs(folder_path, exist_ok=True)
        logging.debug("HACK:     changing folder permissions: %s", str(CREATED_FOLDER_PERMISSIONS))
        os.chmod(folder_path, CREATED_FOLDER_PERMISSIONS)

    @staticmethod
    def create_env_json(out_folder: str, image_subfolder: str, mount_volume_name: str, workflow_step: dict, resources: dict) -> dict:
        """Creates the json used by executing workflow steps
        Arguments:
            out_folder: the folder to write the json to
            image_subfolder: subfolder for where Docker image-specific runtime data can be found
            mount_volume_name: the name of the volume to mount to running containers
            workflow_step: the information on the current workflow step
            resources: the resources associated with the request
        Return:
            The environment dict for the specified step
        Exceptions:
            Raises RuntimeError if an experiment JSON file isn't found (the first file with a '.json' extension is
            assumed to be the experiment JSON file)
        """
        # Build up our environment JSON object
        # The working folder for the workflow on our file system
        data_folder_name = os.path.splitext(os.path.basename(workflow_step['makeflow_file']))[0].lstrip('/\\')

        # Docker images mounting point
        env = {'IMAGE_MOUNT_SOURCE': mount_volume_name,
               'DOCKER_VERSION': workflow_step['docker_version_number'],
               # The working folder for the docker base folder
               'BASE_DIR': "/mnt/",
               # The relative working folder
               'RELATIVE_WORKING_FOLDER': os.path.join(image_subfolder, data_folder_name).lstrip('/\\').rstrip('/\\') + '/'
               }
        env['CACHE_DIR'] = os.path.join(env['BASE_DIR'], env['RELATIVE_WORKING_FOLDER'], "cache") + '/'
        # Get the folders for our files
        env['DATA_FOLDER_NAME'] = os.path.join(env['RELATIVE_WORKING_FOLDER'], 'images').lstrip('/\\')

        # Get the experiment information file
        found_experiment = None
        for one_file in resources['local_paths']:
            if one_file.lower().endswith('.yaml'):
                found_experiment = one_file
                break
        if found_experiment:
            env['EXPERIMENT_METADATA_FILENAME'] = os.path.basename(found_experiment)
            logging.info("Experiment file: '%s' ('%s')", env['EXPERIMENT_METADATA_FILENAME'], found_experiment)
        else:
            raise RuntimeError("Unable to find an experiment JSON file")

        # Where we want the results.json file to be located
        env['RESULTS_FILE_PATH'] = out_folder.rstrip('/\\') + '/'
        if 'use_extended_results_path' in workflow_step:
            env['RESULTS_FILE_PATH'] = os.path.join(env['RESULTS_FILE_PATH'], data_folder_name) + '/'
        env['RESULTS_FILE_NAMES'] = [WORKFLOW_STEP_RESULT_FILE_NAME, WORKFLOW_STEP_CACHE_FILE_NAME]

        return env

    @staticmethod
    def relocate_files(env: dict, resources: Union[dict, str], copy_folders: bool = False) -> tuple:
        """Prepares the files for processing by relocating them
        Arguments:
            env: the environment to be used for this workflow step
            resources: the resources associated with the request or path of a folder on disk
            copy_folders: copy any found subfolders; defaults to False
        """
        # pylint: disable=unused-argument
        # We need to copy the files to the right spot
        dest_dir = os.path.join(env['BASE_DIR'], env['DATA_FOLDER_NAME'].lstrip('/'))
        updated_experiment_metadata_path = None
        logging.debug("Copying files to folder: '%s", dest_dir)
        __internal__.create_folder_default_perms(dest_dir)
        if isinstance(resources, dict):
            source_list = resources['local_paths']
        elif isinstance(resources, str):
            source_list = [os.path.join(resources, file_name) for file_name in os.listdir(resources)]
        else:
            raise RuntimeError("Parameter 'resource' must be of type dict or str for relocate_files() call")
        for one_file in source_list:
            if one_file.endswith(env['EXPERIMENT_METADATA_FILENAME']):
                updated_experiment_metadata_path = os.path.join(env['BASE_DIR'], env['RELATIVE_WORKING_FOLDER'], os.path.basename(one_file))
                logging.debug("Copying experiment metadata '%s' to '%s'", one_file, updated_experiment_metadata_path)
                shutil.copyfile(one_file, updated_experiment_metadata_path)
            elif os.path.isfile(one_file):
                if not os.path.basename(one_file).lower() == WORKFLOW_STEP_RESULT_FILE_NAME:
                    dest_filename = os.path.join(dest_dir, os.path.basename(one_file))
                    logging.debug("Copying file '%s' to '%s'", one_file, dest_filename)
                    shutil.copyfile(one_file, dest_filename)
                else:
                    logging.debug("Skipping result file: '%s'", one_file)
            elif os.path.isdir(one_file):
                if copy_folders:
                    dest_folder = os.path.join(dest_dir, os.path.basename(one_file))
                    logging.debug("Copying folder '%s' to '%s'", one_file, dest_folder)
                    try:
                        shutil.copytree(one_file, dest_folder)
                    except Exception as ex:
                        logging.warning("Copying folder '%s' to '%s'", one_file, dest_folder)
                        logging.warning("Exception caught copying folder: %s", str(ex))
                else:
                    logging.debug("Skipping copying of folder '%s'", one_file)
            else:
                logging.warning("Skipping copying of unknown path type: '%s'", one_file)

        # Copy any needed scripts
        source_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cache_results.py')
        dest_filename = os.path.join(env['BASE_DIR'], env['RELATIVE_WORKING_FOLDER'], os.path.basename(source_filename))
        logging.debug("Copying script '%s' to '%s'", source_filename, dest_filename)
        shutil.copyfile(source_filename, dest_filename)

        return dest_dir, updated_experiment_metadata_path

    @staticmethod
    def setup_processing_step(env: dict, out_folder: str, workflow_step: dict) -> None:
        """Creates the json file to be used by the workflow step
        Arguments:
            env: the environment to be used for this workflow step
            out_folder: the folder to write the json to
            workflow_step: the information on the current workflow step
        """
        # pylint: disable=unused-argument

        # Write out the environment JSON file
        env_filename = os.path.join(out_folder, 'env.json')
        logging.debug("Creating env.json file: '%s'", env_filename)
        with open(env_filename, 'w') as out_file:
            json.dump(env, out_file, indent=2)

    @staticmethod
    def create_dataset(host: str, request_key: str, dataset_name: str) -> str:
        """Creates a dataset on the remote host. Assumes dataset does not exist already
        Arguments:
            host: the URL of the origination request
            request_key: the key associated with request
            dataset_name: the name of the dataset to create
        """
        url = '%sapi/datasets/createempty?key=%s' % (host, request_key)

        result = requests.post(url, headers={'Content-Type': 'application/json'},
                               data=json.dumps({'name': dataset_name, 'description': ''}))
        result.raise_for_status()

        return_json = result.json()
        if 'id' not in return_json:
            logging.debug("Unknown result JSON from create dataset: %s", str(return_json))
            raise RuntimeError("Return result from creating dataset has changed and is not supported")

        return return_json['id']

    @staticmethod
    def update_file_metadata(file_id: str, replace_metadata: bool, metadata: Union[str, dict], connector: connectors.Connector,
                             host: str, request_key: str) -> None:
        """Handles updating metadata associated with the file. Will add metadata if it doesn't exist already
        Arguments:
            file_id: Clowder ID of the file for which metadata is to be updated
            replace_metadata: set to True if existing metadata is to be removed
            metadata: the metadata to update with. If a string is specified, metadata is replaced
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
        Exceptions:
            Raises RuntimeError if the metadata is not properly formatted or other problems are found
        """
        try:
            # Remove metadata if asked
            if replace_metadata is True:
                url = '%sapi/files/%s/metadata.jsonld?key=%s' % (host, file_id, request_key)
                logging.debug("Deleting file metadata: '%s'", url)
                result = requests.delete(url)
                result.raise_for_status()
#        else:
#            # Merge with existing metadata
#            original_md = files.download_metadata(connector, host, request_key, file_id)
#            if isinstance(original_md, list):
#                update_metadata = [*original_md, update_metadata]
#            elif original_md:
#                update_metadata = [original_md, update_metadata]

            # Update the metadata
            logging.debug("Updating file '%s' metadata with: %s", file_id, str(metadata))
            files.upload_metadata(connector, host, request_key, file_id, metadata)
        except Exception as ex:
            logging.warning("update_file_metadata failed: %s", str(ex))

    @staticmethod
    def update_dataset_metadata(dataset_id: str, replace_metadata: bool, connector: connectors.Connector, host: str,
                                request_key: str, container_metadata: dict = None) -> None:
        """Updates the metadata for the dataset
        Arguments:
            dataset_id: the Clowder ID of the dataset to update
            replace_metadata: set to True if existing metadata is to be removed, only relevant if container_metadata specified
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
            container_metadata: optional metadata for the container
        Exceptions:
            Raises RuntimeError if the metadata is not properly formatted or other problems are found
        """
        # Update the metadata for the dataset, we handle process specific metadata after that
        try:
            if container_metadata:
                logging.debug("HACK: update_dataset_metadata: have container metadata, checking for replacing")
                # Remove metadata if asked
                if replace_metadata is True:
                    logging.debug("HACK: update_dataset_metadata: about to remove dataset metadata: %s", dataset_id)
                    datasets.remove_metadata(connector, host, request_key, dataset_id)
    #            else:
    #               # Merge with existing metadata
    #                original_md = datasets.download_metadata(connector, host, request_key, dataset_id)
    #                if isinstance(original_md, list):
    #                    update_metadata = [*original_md, update_metadata]
    #                elif original_md:
    #                    update_metadata = [original_md, update_metadata]

                # Update the metadata
                logging.debug("HACK: update_dataset_metadata: about to upload container metadata: %s %s", dataset_id, container_metadata)
                datasets.upload_metadata(connector, host, request_key, dataset_id, container_metadata)
        except Exception as ex:
            logging.debug("HACK: update_dataset_metadata: EXCEPTION CAUGHT: %s", str(ex))

    @staticmethod
    def upload_files(dataset_id: str, file_results: list, workflow_step: dict, connector: connectors.Connector, host: str,
                     request_key: str) -> list:
        """Uploads the specified files into the dataset
        Arguments:
            dataset_id: the ID of the dataset to upload files into
            file_results: the results file set to upload
            workflow_step: the information on the current workflow step
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
        Return:
            Returns a list of information on the uploaded files.
            [{
                'path': <file path>,    # Path of the uploaded file (same as file_results entries)
                'key': <file key>,      # Key associated with the file (same as file_results entries)
                'id': <ID of uploaded file> # The Clowder ID of the file
            },
            ...]
        """
        uploaded_files = []
        for one_result in file_results:
            # Perform either an upload or a soft upload
            logging.debug("Uploading one file to dataset %s: '%s'", dataset_id, str(one_result['path']))
            file_id = files.upload_to_dataset(connector, host, request_key, dataset_id, one_result['path'])
            if file_id is None:
                logging.error("Unable to upload file to dataset %s: '%s'", dataset_id, one_result['path'])
                raise RuntimeError("Unable to upload file to dataset ID %s: '%s'" % (dataset_id, one_result['path']))
            logging.debug("    file ID: %s", str(file_id))

            # Check if there's metadata associated with the file
            if 'metadata' in one_result:
                logging.debug("Uploading file metadata %s: '%s' %s", file_id, one_result['path'], str(one_result['metadata']))
                replace_metadata = True
                if 'replace' in one_result['metadata']:
                    replace_metadata = (not one_result['metadata']['replace']) is False
                if 'data' in one_result['metadata']:
                    working_metadata = one_result['metadata']['data']
                else:
                    working_metadata = one_result['metadata']

                prepared_metadata = __internal__.prepare_metadata(host, workflow_step['docker_version_number'],
                                                                  workflow_step['makeflow_file'], working_metadata,
                                                                  file_id, target_is_dataset=False)
                logging.debug("Prepared metadata for file upload: %s", str(prepared_metadata))
                __internal__.update_file_metadata(file_id, replace_metadata, prepared_metadata, connector, host, request_key)

            # Save the file information
            uploaded_files.append({**one_result, **{'id': file_id}})

        logging.debug("Uploaded %s files", str(len(uploaded_files)))
        return uploaded_files

    @staticmethod
    def process_result_file(file_results: list, experiment_info: dict, workflow_step: dict, process_metadata: dict,
                            connector: connectors.Connector, host: str, request_key: str, workstep_metadata: dict,
                            clowder_credentials: dict, resources: dict) -> list:
        """Processes the results as a Clowder dataset
        Arguments:
            file_results: the results file set to upload
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            process_metadata: additional metadata for the container; may be None
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
            workstep_metadata: the metadata associated with this workstep
            clowder_credentials: the access information for clowder
            resources: the resources associated with this request
        Return:
            Returns a list of information on the files that were uploaded
        Exceptions:
            Raises RuntimeException if a problem is found
        """
        # pylint: disable=unused-argument
        # Check to see if we force a new dataset to be generated and generate the new dataset
        dataset_id = None
        logging.debug("process_result_file: looking for dataset ID in %s", str(resources))
        if 'type' in resources and 'id' in resources and resources['type'] == 'dataset':
            dataset_id = resources['id']
        elif 'type' in resources and 'parent' in resources and resources['type'] == 'file':
            if 'type' in resources['parent'] and 'id' in resources['parent'] and resources['parent']['type'] == 'dataset':
                dataset_id = resources['parent']['id']
        if dataset_id is None:
            logging.error("Unable to find dataset ID for file uploads")
            raise RuntimeError("Unable to find dataset ID to place files into")

        # Load the files to the dataset
        logging.debug("process_result_file: found dataset ID: %s", str(dataset_id))
        return __internal__.upload_files(dataset_id, file_results, workflow_step, connector, host, request_key)

    @staticmethod
    def process_result_dataset(container_results: list, experiment_info: dict, workflow_step: dict, process_metadata: dict,
                               connector: connectors.Connector, host: str, request_key: str, workstep_metadata: dict,
                               clowder_credentials: dict, resources: dict) -> list:
        """Processes the results as a Clowder dataset
        Arguments:
            container_results: the results for a container
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            process_metadata: additional metadata for the container; may be None
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
            workstep_metadata: the metadata associated with this workstep
            clowder_credentials: the access information for clowder
            resources: the resources associated with this request
        Return:
            Returns a list of dataset information consisting of dict for each dataset.
            [{
                'id': <dataset ID>,     # The Clowder ID of the dataset
                'created': <bool>,      # True if the dataset is newly created; False if it already exists
                'file_ids': <list of file>  # List of information on files uploaded to the dataset
            },
            ...]
        """
        # pylint: disable=unused-argument
        return_info = []
        template_metadata = deepcopy(workstep_metadata)
        for one_container in container_results:
            # Create the name of the dataset
            template_metadata['name'] = one_container['name']
            if 'dataset_name_template' in workflow_step:
                dataset_name = workflow_step['dataset_name_template'].format(**template_metadata).replace(' ', '_')
            else:
                dataset_name = '{name}_{date}_{experiment}'.format(**template_metadata).replace(' ', '_')

            # Check for dataset existence and create it if needed
            created_dataset = False
            logging.debug("Getting the ID for the dataset: %s", dataset_name)
            dataset_id = extractors.get_datasetid_by_name(host, request_key, dataset_name)
            if dataset_id is None:
                logging.debug("Creating dataset: %s", dataset_name)
                dataset_id = __internal__.create_dataset(host, request_key, dataset_name)
                created_dataset = True
            logging.debug("Using dataset ID: %s", str(dataset_id))

            # Load the files into the dataset
            uploaded_files = []
            logging.debug("Looking for 'file' key in container results keys: %s", str(one_container.keys()))
            for key in ['file', 'files']:
                if key in one_container:
                    logging.debug("Uploading files to dataset [key: %s]: %s", key, str(one_container[key]))
                    uploaded_files = __internal__.upload_files(dataset_id, one_container[key], workflow_step, connector, host, request_key)

            # Update the dataset metadata
            replace_metadata = True
            container_metadata = None
            if 'metadata' in one_container:
                if 'replace' in one_container['metadata']:
                    replace_metadata = (not one_container['metadata']['replace']) is False
                if 'data' in one_container['metadata']:
                    working_metadata = one_container['metadata']['data']
                else:
                    working_metadata = one_container['metadata']

                if process_metadata:
                    logging.debug("Merging container metadata with process metadata")
                    working_metadata = {**working_metadata, **process_metadata}

                container_metadata = __internal__.prepare_metadata(host, workflow_step['docker_version_number'],
                                                                   workflow_step['makeflow_file'], working_metadata,
                                                                   dataset_id, target_is_dataset=True)
                logging.debug("Prepared metadata for dataset upload: %s", str(container_metadata))

            __internal__.update_dataset_metadata(dataset_id, replace_metadata, connector, host, request_key, container_metadata)

            return_info.append({'id': dataset_id, 'created': created_dataset, 'file_ids': uploaded_files})

        logging.debug("Done processing result datasets")
        return return_info

    @staticmethod
    def process_results_json(proc_results: dict, experiment_info: dict, workflow_step: dict, connector: connectors.Connector,
                             host: str, request_key: str, workstep_metadata: dict, clowder_credentials: dict, resources: dict) -> bool:
        """Handles processing the results of running a workflow
        Arguments:
            proc_results: the results of the workflow process
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
            workstep_metadata: the metadata associated with this workstep
            clowder_credentials: the access information for clowder
            resources: the resources associated with this request
        """
        # Check the return code for success
        if not workflow_step['return_code_success'](proc_results['code']):
            logging.error("Error code from processing: %s", str(proc_results['code']))
            logging.debug("Processing results: %s", str(proc_results))
            return False

        # Get additional information in the processing results
        process_metadata_keys = set(proc_results.keys()).difference(frozenset(['container', 'file', 'files', 'code', 'error', 'message']))
        logging.debug("Found process metadata keys: %s", str(process_metadata_keys))
        process_metadata = {}
        for one_key in process_metadata_keys:
            process_metadata[one_key] = proc_results[one_key]

        # Get the results sent to Clowder
        logging.debug("About to check for 'container' in results")
        if 'container' in proc_results:
            logging.debug("Processing container as dataset: %s", proc_results['container'])
            __internal__.process_result_dataset(proc_results['container'], experiment_info, workflow_step, process_metadata,
                                                connector, host, request_key, workstep_metadata, clowder_credentials, resources)
        logging.debug("About to check for 'file' in results")
        for file_key in ['file', 'files']:
            if file_key in proc_results:
                logging.debug("Processing file (%s): %s", file_key, proc_results[file_key])
                __internal__.process_result_file(proc_results[file_key], experiment_info, workflow_step, process_metadata,
                                                 connector, host, request_key, workstep_metadata, clowder_credentials, resources)

        logging.debug("Finished processing return JSON")
        return True

    @staticmethod
    def discover_result_files(source_folder: str, file_name: str) -> list:
        """Recursively searches the specified folder for first instances of the file name
        Arguments:
            source_folder: the folder to search
            file_name: the name of the file to find
        Return:
            A list of all the fully qualified names of the files found
        """
        found = []
        if not os.path.isdir(source_folder):
            logging.debug("Ignoring invalid folder parameter while recursively searching for result file")
            return found

        found_dirs = []
        for one_file in os.listdir(source_folder):
            found_name = os.path.join(source_folder, one_file)
            if os.path.basename(found_name) == file_name:
                if found_name not in found:
                    found.append(found_name)
            elif os.path.isdir(found_name):
                found_dirs.append(found_name)

        if not found:
            for one_dir in found_dirs:
                found.extend(__internal__.discover_result_files(one_dir, file_name))

        return found

    @staticmethod
    def find_dict_key(haystack: dict, key: str, case_insensitive: bool = True) -> Optional[tuple]:
        """Searches the metadata for a particular key using a breadth-first method
        Arguments:
            haystack: the dict to search
            key: the key to search for
            case_insensitive: case-insensitive search for key (True, default), or case-sensitive (False)
        Return:
            Returns a tuple of the found key and its value. Will return None if the key was not found
        """
        if case_insensitive:
            check_key = key.lower()
        else:
            check_key = key

        # For breadth-first we need to keep track of dicts we haven't look into
        dict_checks = []
        for one_key, value in haystack.items():
            if one_key == check_key or (case_insensitive and one_key.lower() == check_key):
                return one_key, value
            if isinstance(value, dict):
                dict_checks.append(value)

        # We didn't find it yet, check any found dicts
        for one_check in dict_checks:
            found = __internal__.find_dict_key(one_check, check_key, False)
            if found is not None:
                return found

        return None

    @staticmethod
    def secure_string(plain_text: str) -> str:
        """Secures the plain text string
        Arguments:
            plain_text: the text to secure
        Return:
            Returns the secured string. If the plain_text can't be directly secured, the string '<removed> is returned
        """
        encrypted = encrypt_pipeline_string(plain_text)
        if encrypted is not None:
            return "secured:" + encrypted
        return "<removed>"


class DroneMakeflow(extractors.TerrarefExtractor):
    """Class instance for running makeflow"""

    def __init__(self):
        """Initializes class instance
        """
        super(DroneMakeflow, self).__init__()

        self.parser.add_argument('--working_space', default=os.getenv("WORKING_SPACE"),
                                 help="the folder to use as a workspace - will be created if it doesn't exist")
        self.parser.add_argument('--named_volume', default=os.getenv("NAMED_VOLUME"),
                                 help="the name of the Docker volume to use when starting other images (must contain working_space)")

        self.setup(sensor='stereoTop')

        #logging.getLogger().setLevel(logging.INFO)
        logging.getLogger().setLevel(logging.DEBUG)

    def process_message(self, connector: connectors.Connector, host: str, secret_key: str, resource: dict, parameters: dict) -> dict:
        """Processes the request message
        Arguments:
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            secret_key: the key associated with request
            resource: the resources associated with this request
            parameters: the message body
        """
        # TODO:
        #  1. cache to date stamped folder, per key, w/ user & experiment
        #  2. file metadata when no container specified
        #  3. support force_dataset
        #  4. use latest dataset ID for subsequent steps
        #  5. add docker environment variables such as BETYDB_KEY
        #  6.
        self.start_message(resource)
        super(DroneMakeflow, self).process_message(connector, host, secret_key, resource, parameters)

        # Get the Docker volume name to use
        if not self.args.named_volume:
            raise RuntimeError("No named volume was specified. Try setting the NAMED_VOLUME environment variable"
                               " (if using Docker set to a named volume to use)")

        # Get a working folder to use
        if self.args.working_space:
            logging.info("Folder for our working space: '%s'", self.args.working_space)
            # Assume we're sharing out working space with other instances, create a temporary folder
            working_folder = tempfile.mkdtemp(dir=self.args.working_space)
#            working_folder = os.path.join(self.args.working_space, 'tmpjhvq63gh')
            working_subfolder = working_folder[len(self.args.working_space):]
            logging.debug("Creating working space folder for our instance: '%s'", working_folder)
            __internal__.create_folder_default_perms(working_folder)
        else:
            raise RuntimeError("No working space folder was specified. Try setting the WORKING_SPACE environment variable "
                               "(if using Docker set to a folder to mount)")

        # Process the steps sequentially
        env = {}
        step_number = 0
        previous_step_cache_dir = None
        previous_step_cached_file = None
        for current_step in WORKFLOW:
            step_number += 1
            logging.info("Starting workflow step %s: '%s' with named volume '%s'", str(step_number), current_step['name'],
                         self.args.named_volume)

            # Get the environment information and setup for the run
            if env:
                previous_step_cache_dir = env['CACHE_DIR']
                previous_step_cached_file = os.path.join(env['RESULTS_FILE_PATH'], WORKFLOW_STEP_CACHE_FILE_NAME)
                if not os.path.exists(previous_step_cached_file):
                    logging.warning("Continuing after not finding cache file results from previous step: %s", previous_step_cached_file)
                    previous_step_cached_file = None
            env = __internal__.create_env_json(working_folder, working_subfolder, self.args.named_volume, current_step, resource)
            logging.debug("Makefile data: %s", str(env))

            # Relocate the files so docker-within-docker images can access them
            copy_cached_folders = False
            if 'copy_cached_folders' in current_step and current_step['copy_cached_folders']:
                copy_cached_folders = True
            if step_number <= 1:
                current_working_folder, new_experiment_path = __internal__.relocate_files(env, resource,
                                                                                          copy_cached_folders)
            else:
                current_working_folder, new_experiment_path = __internal__.relocate_files(env, previous_step_cache_dir,
                                                                                          copy_cached_folders)
            if not current_working_folder:
                raise RuntimeError("No working folder was determined for processing")
            if not new_experiment_path:
                raise RuntimeError("No experiment metadata file is available")
            logging.debug("Current working folder: '%s'", current_working_folder)
            logging.debug("New experiment path: '%s'", new_experiment_path)

            # Check for pre-processing the cache copying JSON file
            if previous_step_cached_file and 'preprocess_json' in current_step:
                logging.info("Preprocessing cached file JSON: '%s'", previous_step_cached_file)
                previous_step_cached_file = current_step['preprocess_json'](env, previous_step_cached_file)
                logging.debug("Preprocessed cached file JSON to new file: '%s'", previous_step_cached_file)

            # Make sure the experiment file name is correct (not a full path, but a path particle)
            if os.path.exists(new_experiment_path) and not new_experiment_path.startswith(env['BASE_DIR']):
                raise RuntimeError("Experiment metadata path does not start with the specified BASE_DIR folder '%s'" % env['BASE_DIR'])
            if new_experiment_path.startswith(env['BASE_DIR']):
                env['EXPERIMENT_METADATA_FILENAME'] = new_experiment_path[len(env['BASE_DIR']):]

            # Prepare for processing
            logging.debug("Working env.json file: %s", str(env))
            __internal__.setup_processing_step(env, working_folder, current_step)

            # Run the command
            cmd = [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cctools/bin/makeflow'),
                   '--jx', current_step['makeflow_file'],
                   '--jx-args', os.path.join(working_folder, 'env.json')]
            if previous_step_cached_file:
                cmd.append('--jx-args')
                cmd.append(previous_step_cached_file)
            logging.debug("Running command: %s", str(cmd))
            proc = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

            # Wait for it to finish
            loop_iteration = 1
            start_time = datetime.datetime.now()
            while (datetime.datetime.now() - start_time).total_seconds() <= PROC_WAIT_TOTAL_SEC:
                if proc.returncode is None:
                    logging.info("Waiting for process to finish %s", str(loop_iteration))
                    if proc.stdout:
                        try:
                            while True:
                                line = proc.stdout.readline()
                                if line:
                                    logging.debug(line.rstrip(b'\n'))
                                else:
                                    break
                        except Exception as ex:
                            logging.debug("Ignoring exception while waiting for process %s", str(ex))
                    proc.poll()
                    time.sleep(PROC_WAIT_SLEEP_SEC)
                else:
                    logging.info("Process completed")
                    logging.debug("Process return code: %s", str(proc.returncode))
                    break

                loop_iteration += 1

                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                if processing_time > PROC_WAIT_TOTAL_SEC:
                    msg = "Processing is running too long (%s sec): %s" % (str(processing_time), str(cmd))
                    logging.error(msg)
                    raise RuntimeError(msg)

            # Load the experiment data into a form processing the results file can use
            experiment_path = os.path.join(env['BASE_DIR'], env['EXPERIMENT_METADATA_FILENAME'])
            logging.debug("Loading experiment metadata before looking at result: '%s'", experiment_path)
            workstep_metadata = deepcopy(current_step)
            clowder_info = {}
            if os.path.splitext(experiment_path)[1] in ('.yml', '.yaml'):
                load_func = yaml.safe_load
            else:
                load_func = json.load
            with open(experiment_path, 'r') as in_file:
                experiment_metadata = load_func(in_file)
                if 'pipeline' in experiment_metadata:
                    logging.debug("Found 'pipeline' key in experiment metadata, using its value as top level metadata")
                    experiment_metadata = experiment_metadata['pipeline']
                experiment_info = {}
                if experiment_metadata:
                    # Fix up experiment information
                    for key, value in experiment_metadata.items():
                        experiment_info[key] = str(value)
                    if 'observationTimeStamp' in experiment_info:
                        workstep_metadata['date'] = experiment_info['observationTimeStamp'][0:10]
                    elif 'date' in experiment_info:
                        workstep_metadata['date'] = experiment_info['date']
                    else:
                        logging.info("No timestamp or date was specified in experiment metadata, using current date")
                        workstep_metadata['date'] = datetime.datetime.now().strftime('%Y-%m-%d')
                    if 'studyName' in experiment_info:
                        workstep_metadata['experiment'] = experiment_info['studyName']
                    # Check for a username and password for Clowder
                    clowder_md = __internal__.find_dict_key(experiment_metadata, 'clowder')
                    if clowder_md:
                        space = __internal__.find_dict_key(clowder_md[1], 'space')
                        username = __internal__.find_dict_key(clowder_md[1], 'username')
                        password = __internal__.find_dict_key(clowder_md[1], 'password')
                        if space:
                            clowder_info['space'] = space[1]
                            workstep_metadata['password'] = space[1]
                        if username:
                            clowder_info['username'] = username[1]
                            workstep_metadata['password'] = username[1]
                        if password:
                            clowder_info['password'] = password[1]
                            workstep_metadata['password'] = __internal__.secure_string(clowder_info['password'])

            # Process the results file
            if 'discover_run_results' in current_step:
                result_filenames = __internal__.discover_result_files(env['RESULTS_FILE_PATH'], WORKFLOW_STEP_RESULT_FILE_NAME)
                if not result_filenames:
                    logging.warning("Did not find any result files through discovery for step %s, this may not be an issue",
                                    current_step['name'])
            else:
                result_filenames = [os.path.join(env['RESULTS_FILE_PATH'], WORKFLOW_STEP_RESULT_FILE_NAME)]
            logging.info("Loading and processing results: '%s'", str(result_filenames))
            for one_filename in result_filenames:
                if os.path.exists(one_filename):
                    logging.debug("Result processing for file: '%s'", one_filename)
                    with open(one_filename, 'r') as in_file:
                        proc_results = json.load(in_file)
                        __internal__.process_results_json(proc_results, experiment_info, current_step, connector, host, secret_key,
                                                          workstep_metadata, clowder_info, resource)
                    logging.debug("Removing copied result file: '%s'", one_filename)
#                    os.unlink(one_filename)
                else:
                    msg = "Result file from current step '%s' is not found: %s" % (current_step['name'], env['RESULTS_FILE_PATH'])
                    logging.error(msg)
                    raise RuntimeError(msg)

        # Finish up
        logging.debug("Finished processing message")
        self.end_message(resource)


if __name__ == "__main__":
    EXTRACTOR = DroneMakeflow()
    EXTRACTOR.start()
