"""Handles preparing and starting a makeflow run
"""

import datetime
import json
import logging
import os
import shutil
import stat
import subprocess
import tempfile
import time
from typing import Union
import yaml
import requests

import pyclowder.connectors as connectors
import pyclowder.datasets as datasets
import pyclowder.files as files
import terrautils.extractors as extractors

# Timeouts relating to processing
PROC_WAIT_SLEEP_SEC = 5  # Amount of time to sleep before checking process status
PROC_WAIT_TOTAL_SEC = 24 * 60 * 60  # Total wait time for process to finish
PROC_COMMUNICATE_TIMEOUT_SEC = 2  # Number of seconds to wait for a communicate call to complete

# Access permissions for folders we create
CREATED_FOLDER_PERMISSIONS = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP |\
                             stat.S_IROTH | stat.S_IWOTH | stat.S_IXOTH

# Name of mount point on Docker images
IMAGE_MOUNT_POINT_NAME = '/mnt/'

# docker run --network pipeline_clowder -v /var/run/docker.sock:/var/run/docker.sock -v "testing:/mnt" --user root -e 'RABBITMQ_URI=amqp://rabbitmq/%2F' -e 'RABBITMQ_EXCHANGE=terra' -e 'TZ=/user/share/zoneinfo/US/Central' -e "PIPELINE_KEY=\x84\n'\x08\xbd\\\xef\xe1\x00\r\xe5\xf6=\x80\x1c\xc6\xd1o\xc3\xad\\:\xce\x92\x14^\xf0\x8c\xf4\x1c\`\x0b" -e 'WORKING_SPACE=/mnt' -e 'NAMED_VOLUME=testing' -d --restart=always --name=extractor-dronemakeflow chrisatua/development:drone_makeflow

WORKFLOW = [
    {
        'name': 'OpenDroneMap workflow',                        # Name of the workflow step
        'makeflow_file': 'odm_workflow.jx',                     # The makeflow file to use
        'arguments': None,                                      # Additional arguments for makeflow command
        'return_code_success': lambda code: int(code) == 0,     # Function that indicates success based upon return code
        'force_dataset': True,                                  # Force the output to a dataset if not specified
        'dataset_name_template': '{name}_{date}_{experiment}'   # Template for dataset names
    }
]


class __internal__():
    """Internal use class"""
    def __init__(self):
        """Initializes class instance"""

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
        step_out_folder_name = os.path.splitext(os.path.basename(workflow_step['makeflow_file']))[0].lstrip('/\\')

        # Docker images mounting point
        env = {'IMAGE_MOUNT_POINT': IMAGE_MOUNT_POINT_NAME,
               'IMAGE_MOUNT_SOURCE': mount_volume_name,
               # Starting folder within Docker images we run
               'IMAGE_BASE_DIR': os.path.join(IMAGE_MOUNT_POINT_NAME, image_subfolder.lstrip('/\\'),
                                              step_out_folder_name).rstrip('/\\') + '/',
               # The working folder for the workflow on our file system
               'BASE_DIR': os.path.join(out_folder, step_out_folder_name).rstrip('/\\') + '/',
               # Get the folders for our files
               'IMAGES_FOLDER': 'images'
               }

        # Get the experiment information file
        found_experiment = None
        for one_file in resources['local_paths']:
            if one_file.lower().endswith('.yaml'):
                found_experiment = one_file
                break
        if found_experiment:
            env['EXPERIMENT_METADATA'] = os.path.basename(found_experiment)
            logging.info("Experiment file: '%s' ('%s')", env['EXPERIMENT_METADATA'], found_experiment)
        else:
            raise RuntimeError("Unable to find an experiment JSON file")

        # Where we want the results.json file to be located
        env['RESULTS_FILE_PATH'] = os.path.join(env['BASE_DIR'], 'results.json')

        # Setup the versions of docker images to use
        env['ODM_DOCKER_IMAGE_VERSION'] = '2.0'
        env['SOIL_MASK_DOCKER_IMAGE_VERSION'] = '2.0'
        env['PLOT_CLIP_DOCKER_IMAGE_VERSION'] = '2.0'
        env['CANOPY_COVER_DOCKER_IMAGE_VERSION'] = '0.1'

        return env

    @staticmethod
    def relocate_files(env: dict, resources: dict) -> tuple:
        """Prepares the files for processing by relocating them
        Arguments:
            env: the environment to be used for this workflow step
            resources: the resources associated with the request
        """
        # pylint: disable=unused-argument
        # We need to hard link the files to the right spot
        dest_dir = os.path.join(env['BASE_DIR'], env['IMAGES_FOLDER'].lstrip('/'))
        updated_experiment_metadata_path = None
        logging.debug("Copying files to folder: '%s", dest_dir)
        __internal__.create_folder_default_perms(dest_dir)
        for one_file in resources['local_paths']:
            if one_file.endswith(env['EXPERIMENT_METADATA']):
                updated_experiment_metadata_path = os.path.join(env['BASE_DIR'], os.path.basename(one_file))
                logging.debug("Copying experiment metadata '%s' to '%s'", one_file, updated_experiment_metadata_path)
                #os.link(one_file, dest_filename)
                shutil.copyfile(one_file, updated_experiment_metadata_path)
            else:
                dest_filename = os.path.join(dest_dir, os.path.basename(one_file))
                logging.debug("Copying file '%s' to '%s'", one_file, dest_filename)
                #os.link(one_file, dest_filename)
                shutil.copyfile(one_file, dest_filename)

        # Copy any needed scripts
        source_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cache_results.py')
        dest_filename = os.path.join(env['BASE_DIR'], os.path.basename(source_filename))
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
            resources: the resources associated with the request
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
    def update_file_metadata(file_id: str, metadata: Union[str, dict], connector: connectors.Connector, host: str,
                             request_key: str) -> None:
        """Handles updating metadata associated with the file. Will add metadata if it doesn't exist already
        Arguments:
            file_id: Clowder ID of the file for which metadata is to be updated
            metadata: the metadata to update with. If a string is specified, metadata is replaced
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
        Exceptions:
            Raises RuntimeError if the metadata is not properly formatted or other problems are found
        """
        # Prepare the metadata information
        replace_metadata = True
        if isinstance(metadata, dict):
            if 'replace' in metadata:
                replace_metadata = (not metadata['replace']) is False
            if 'data' in metadata:
                update_metadata = metadata['data']
            else:
                raise RuntimeError("Invalid metadata specified for file ID %s - missing 'data' key" % file_id)
        else:
            update_metadata = metadata

        # Remove metadata if asked
        if replace_metadata is True:
            url = '%sapi/files/%s/metadata.jsonld?key=%s' % (host, file_id, request_key)
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
        files.upload_metadata(connector, host, request_key, file_id, update_metadata)

    @staticmethod
    def update_dataset_metadata(dataset_id: str, connector: connectors.Connector, host: str, request_key: str,
                                container_metadata: dict = None, process_metadata: dict = None) -> None:
        """Updates the metadata for the dataset
        Arguments:
            dataset_id: the Clowder ID of the dataset to update
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
            container_metadata: optional metadata for the container
            process_metadata: metadata associated with the current process
        Exceptions:
            Raises RuntimeError if the metadata is not properly formatted or other problems are found
        """
        # Prepare the metadata information
        replace_metadata = True
        update_metadata = ''
        if container_metadata:
            if isinstance(container_metadata, dict):
                if 'replace' in container_metadata:
                    replace_metadata = (not container_metadata['replace']) is False
                if 'data' in container_metadata:
                    update_metadata = container_metadata['data']
                else:
                    raise RuntimeError("Invalid metadata specified for dataset ID %s - missing 'data' key" % dataset_id)
            else:
                update_metadata = container_metadata

        # Update the metadata for the dataset, we handle process specific metadata after that
        if update_metadata:
            # Remove metadata if asked
            if replace_metadata is True:
                datasets.remove_metadata(connector, host, request_key, dataset_id)
#            else:
#               # Merge with existing metadata
#                original_md = datasets.download_metadata(connector, host, request_key, dataset_id)
#                if isinstance(original_md, list):
#                    update_metadata = [*original_md, update_metadata]
#                elif original_md:
#                    update_metadata = [original_md, update_metadata]

            # Update the metadata
            datasets.upload_metadata(connector, host, request_key, dataset_id, update_metadata)

        # We just add any process metadata
        if process_metadata:
            datasets.upload_metadata(connector, host, request_key, dataset_id, process_metadata)

    @staticmethod
    def upload_files(dataset_id: str, file_results: dict, connector: connectors.Connector, host: str, request_key: str) -> list:
        """Uploads the specified files into the dataset
        Arguments:
            dataset_id: the ID of the dataset to upload files into
            file_results: the results file set to upload
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

            # Check if there's metadata associated with the file
            if 'metadata' in one_result:
                logging.debug("Uploading file metadata %s: '%s' %s", file_id, one_result['path'], str(one_result['metadata']))
                __internal__.update_file_metadata(file_id, one_result['metadata'], connector, host, request_key)

            # Save the file information
            uploaded_files.append({**one_result, **{'id': file_id}})

        logging.debug("Uploaded %s files", str(len(uploaded_files)))
        return uploaded_files

    @staticmethod
    def process_result_file(file_results: dict, experiment_info: dict, workflow_step: dict, process_metadata: dict,
                            connector: connectors.Connector, host: str, request_key: str, resources: dict) -> list:
        """Processes the results as a Clowder dataset
        Arguments:
            file_results: the results file set to upload
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            process_metadata: additional metadata for the container; may be None
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
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
        return __internal__.upload_files(dataset_id, file_results, connector, host, request_key)

    @staticmethod
    def process_result_dataset(container_results: dict, experiment_info: dict, workflow_step: dict, process_metadata: dict,
                               connector: connectors.Connector, host: str, request_key: str, resources: dict) -> list:
        """Processes the results as a Clowder dataset
        Arguments:
            container_results: the results for a container
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            process_metadata: additional metadata for the container; may be None
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
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
        # Create the name of the dataset
        if 'dataset_name_template' in workflow_step:
            dataset_name = workflow_step['dataset_name_template'].format(**experiment_info)
        else:
            dataset_name = '{name}_{date}_{experiment}'.format(**experiment_info)

        # Check for dataset existence and create it if needed
        created_dataset = False
        dataset_id = extractors.get_datasetid_by_name(host, request_key, dataset_name)
        if dataset_id is None:
            dataset_id = __internal__.create_dataset(host, request_key, dataset_name)
            created_dataset = True

        # Load the files into the dataset
        uploaded_files = []
        for key in ['file', 'files']:
            if key in container_results:
                uploaded_files = __internal__.upload_files(dataset_id, container_results[key], connector, host, request_key)

        # Update the dataset metadata
        container_metadata = None
        if 'metadata' in container_results:
            container_metadata = container_results['metadata']
        __internal__.update_dataset_metadata(dataset_id, connector, host, request_key, container_metadata, process_metadata)

        return [{'id': dataset_id, 'created': created_dataset, 'file_ids': uploaded_files}]

    @staticmethod
    def process_results_json(proc_results: dict, experiment_info: dict, workflow_step: dict, connector: connectors.Connector,
                             host: str, request_key: str, resources: dict) -> bool:
        """Handles processing the results of running a workflow
        Arguments:
            proc_results: the results of the workflow process
            experiment_info: the experimental information
            workflow_step: the information on the current workflow step
            connector: an instance of the pyclowder connector object
            host: the URL of the origination request
            request_key: the key associated with request
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
        if 'container' in proc_results:
            logging.debug("Processing container as dataset: %s", proc_results['container'])
            __internal__.process_result_dataset(proc_results['container'], experiment_info, workflow_step, process_metadata,
                                                connector, host, request_key, resources)
        for file_key in ['file', 'files']:
            if file_key in proc_results:
                logging.debug("Processing file (%s): %s", file_key, proc_results[file_key])
                __internal__.process_result_file(proc_results[file_key], experiment_info, workflow_step, process_metadata,
                                                 connector, host, request_key, resources)

        return True


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
            working_subfolder = working_folder[len(self.args.working_space):]
            logging.debug("Creating working space folder for our instance: '%s'", working_folder)
            __internal__.create_folder_default_perms(working_folder)
        else:
            raise RuntimeError("No working space folder was specified. Try setting the WORKING_SPACE environment variable"
                               " (if using Docker set to a folder to mount)")

        # Process the steps sequentially
        for current_step in WORKFLOW:
            logging.info("Starting workflow step: '%s' with named volume '%s'", current_step['name'], self.args.named_volume)

            # Get the environment information and setup for the run
            env = __internal__.create_env_json(working_folder, working_subfolder, self.args.named_volume, current_step, resource)
            logging.debug("Makefile data: %s", str(env))

            # Relocate the files so sub-docker images can access them
            if not os.path.exists(env['BASE_DIR']):
                logging.debug("Creating work step base folder: '%s'", env['BASE_DIR'])
                __internal__.create_folder_default_perms(env['BASE_DIR'])
            current_working_folder, new_experiment_path = __internal__.relocate_files(env, resource)
            logging.debug("Current working folder: '%s'", current_working_folder)
            logging.debug("New experiment path: '%s'", new_experiment_path)
            # Make sure the experiment file name is correct (not a full path, but a path particle)
            if os.path.exists(new_experiment_path) and not new_experiment_path.startswith(env['BASE_DIR']):
                raise RuntimeError("Experiment metadata path does not start with the specified BASE_DIR folder")
            if new_experiment_path.startswith(env['BASE_DIR']):
                env['EXPERIMENT_METADATA'] = new_experiment_path[len(env['BASE_DIR']):]

            # Prepare for processing
            logging.debug("Working env.json file: %s", str(env))
            __internal__.setup_processing_step(env, working_folder, current_step)

            # Run the command
            cmd = [os.path.join(os.path.dirname(os.path.realpath(__file__)), 'cctools/bin/makeflow'),
                   '--jx', current_step['makeflow_file'],
                   '--jx-args', os.path.join(working_folder, 'env.json')]
            logging.debug("Running command: %s", str(cmd))
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Wait for it to finish
            return_code = None
            loop_iteration = 1
            start_time = datetime.datetime.now()
            while (datetime.datetime.now() - start_time).total_seconds() <= PROC_WAIT_TOTAL_SEC:
                return_code = proc.poll()
                if return_code is None:
                    logging.info("Waiting for process to finish %s", str(loop_iteration))
                    try:
                        proc_stdout, proc_stderr = proc.communicate(timeout=PROC_COMMUNICATE_TIMEOUT_SEC)
                        if proc_stdout:
                            logging.debug("Proc stdout: %s", str(proc_stdout))
                        if proc_stderr:
                            logging.warning("Proc stderr: %s", str(proc_stderr))
                            logging.warning("Continuing to wait on process %s", str(loop_iteration))
                        time.sleep(PROC_WAIT_SLEEP_SEC)
                    except subprocess.TimeoutExpired as ex:
                        logging.debug("Timed out waiting for process to respond %s", str(ex))
                else:
                    logging.info("Process completed")
                    logging.debug("Process return code: %s", str(return_code))
                    break

                loop_iteration += 1

                processing_time = (datetime.datetime.now() - start_time).total_seconds()
                if processing_time > PROC_WAIT_TOTAL_SEC:
                    msg = "Processing is running too long (%s sec): %s" % (str(processing_time), str(cmd))
                    logging.error(msg)
                    raise RuntimeError(msg)

            # Load the experiment data into a form processing the results file can use
            experiment_path = os.path.join(env['IMAGE_BASE_DIR'], env['EXPERIMENT_METADATA'])
            logging.debug("Loading experiment metadata before looking at result: '%s'", experiment_path)
            if os.path.splitext(experiment_path)[1] in ('.yml', '.yaml'):
                load_func = yaml.safe_load
            else:
                load_func = json.load
            with open(experiment_path, 'r') as in_file:
                experiment_json = load_func(in_file)
                experiment_info = {}
                if experiment_json:
                    for key, value in experiment_json.items():
                        experiment_info[key] = str(value)

            # Process the results file
            logging.info("Loading and processing results: '%s'", env['RESULTS_FILE_PATH'])
            with open(env['RESULTS_FILE_PATH'], 'r') as in_file:
                proc_results = json.load(in_file)
                __internal__.process_results_json(proc_results, experiment_info, current_step, connector, host, secret_key, resource)

        # Finish up
        self.end_message(resource)


if __name__ == "__main__":
    EXTRACTOR = DroneMakeflow()
    EXTRACTOR.start()
