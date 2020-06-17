# Drone Makeflow Docker
This folder contains the files used to build a Docker image of the makeflow.

## Building an image
When building a Docker image of the drone workflow, the following command can be run in the folder above this one:
```docker build -f docker/Dockerfile -t drone/makeflow .```

This will build an image named `drone/makeflow:latest` with everything needed to run workflows.
You can change the name to something else if desired.

## Running the image <a name="running" />
For this section we're going to continue using the example Docker image named `drone/makeflow:latest`.
If you built the image using a different name, use that name instead.

When running the image there are a few considerations:
1) Run the image as as the `root` user
2) A single named volume needs to have the source files and is used to store the output
3) When specifying paths to files they need to be relative to the volume folder

A sample command line could be ```docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v my_data:/mnt -e "CONFIGURATION_FILE=/mnt/capture/workflow_config.yml" -e "SOURCES_DIR=/mnt/capture/img/" -e "EXPERIMENT_FILE=/mnt/capture/experiment.yaml" drone/makeflow:latest workflow```

The following list explains the different components of the command line:
* _docker run_: tells the docker app to run an image
* _--rm_: removes the stopped container once it's finished processing
* _-v /var/run/docker.sock:/var/run/docker.sock_: mounts needed Docker information which allows running Docker containers inside of other Docker containers 
* _-v my_data:/mnt_: mounts the Docker named volume `my_data` to the `/mnt` folder of the running container
* _-e "CONFIGURATION_FILE=/mnt/capture/workflow_config.yml"_: defines a variable containing the complete path to the workflow configuration file starting at the named volume mount point
* _-e "SOURCES_DIR=/mnt/capture/img/"_: defines a variable containing the complete path to the folder containing the source images
* _-e "EXPERIMENT_FILE=/mnt/capture/experiment.yaml"_: defines a variable containing the complete path to the file containing experiment information
* _drone/makeflow:latest_: the Docker image to run
* _workflow_: the command to run in the container

Since the workflow runs Docker containers within the main Docker container, it's necessary that the user used to run the commands in the container has permissions to do so.

## Docker container parameters
Running the Docker container with the `-h` help flag will display the parameters and variables that can be used to control the behavior of the workflow.
This section defines the current set of parameters and variables, but be sure to run the Docker image with the `-h` flag to get the supported fields.
An example command to display the help for the image: `docker run --rm drone/makeflow:latest -h`.

The following commands are supported:
- _workflow_: run the workflow (see [Running the image](#running) above for an example)
- _clean_: clean a previously run workflow (the rest of the command line is the same as for 'workflow' - substitute with the 'clean' command)
- _-h_: display the help for the container

The following variables are supported:
- _CONFIGURATION_FILE_: the workflow configuration file
- _SOURCES_DIR_: the path to the source files
- _EXPERIMENT_FILE_: the file containing experiment information
