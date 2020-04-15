# Makeflow for Drone Processing Pipeline
<img src="https://github.com/az-digitalag/Drone-Processing-Pipeline/raw/07b1edc34a1faea501c80f583beb07f9d6b290bb/resources/drone-pipeline.png" width="100" />

This repository contains the files used to run containers in the [Makeflow](https://cctools.readthedocs.io/en/latest/makeflow) environment.

## Overview
Each container to be run has its own [.jx](https://cctools.readthedocs.io/en/latest/jx/jx/) file containing everything needed to run the image and locally cache the results.
The basic flow in each of these .jx files is to create needed folders, run the docker container, and cache the results.

Coordination of these smaller workflows is done through the simple `run_makeflow.sh` script.

The sequence of the overall workflow is: `odm_workflow -> soil_mask_workflow -> plot_clip_workflow -> canopy_cover_workflow`.

## YAML file
A simple YAML file is used to define the workflow steps along with any other run-specific information, such as the location of a file containing the experiment information.

A sample YAML file used to process calculate canopy cover from captured images looks like the following:
```
# Runtime environment settings
configuration: {
  # Top level workflow folder
  working_space: /mnt/working_space/,
  # Named volume to use when running inside a docker container
  docker_volume: my_data
}

# The workflow steps
workflow:
  - name: OpenDroneMap                                     # Name of the workflow step
    makeflow_file: odm_workflow.jx                         # The makeflow file to use
    docker_image: agdrone/transformer-opendronemap:2.0     # The docker image to use
    execution_order: 1                                     # Order of execution
  - name: Soil Mask                                        # Name of the workflow step
    makeflow_file: soil_mask_workflow.jx                   # The makeflow file to use
    docker_image: agdrone/transformer-soilmask:2.0         # The docker image to use
    execution_order: 2                                     # Order of execution
  - name: Plot Clip                                        # Name of the workflow step
    makeflow_file: plot_clip_workflow.jx                   # The makeflow file to use
    docker_image: agdrone/transformer-plotclip:2.0         # The docker image to use
    execution_order: 3                                     # Order of execution
  - name: Canopy Cover                                     # Name of the workflow step
    makeflow_file: canopy_cover_workflow.jx                # The makeflow file to use
    docker_image: agdrone/transformer-canopycover:1.0      # The docker image to use
    execution_order: 4                                     # Order of execution}
```

### Configuration
The `configuration` key indicates the start of configuration information.

The following sub-keys are supported:
* _working_space_: the path to where the scratch workspace is located
* _docker_volume_: the named Docker volume that's used when running Docker containers for each workflow step

### Workflow Steps
The `workflow` key indicates the definition of the workflow.
A workflow consists of a series of steps that are run sequentially.
Each workflow can have multiple workers handling its processing.

Each workflow step has the following keys:
- _name_: the human readable name of workflow step
- _makeflow_file_: the name of the Makeflow file that this step uses
- _docker_image_: the docker image to run for the workflow step
- _execution_order_: the order of execution of the current step starting at 1 and incrementing in sequence

## Main Script
The `run_workflow.sh` script converts the configuration YAML to Makeflow-compatible JSON while enhancing the JSON to assist processing.
It also calls the Makeflow entry point and cleans up any changes that it made to the file system.

## Main JX Files <a name="main_jx" />
There are two main `.jx` files used to run workflows are:
* _run_workflow.jx_: is the entry point for running the workflow steps; its role is to run the steps in the correct order
*_sub_workflow.jx_: is called for each workstep; its role is to prepare for running docker containers and ensure things are setup for the next step

## Workflow Step JX Files
Each of the workflow steps has its own .jx file that contain the specific commands needed for it to run.
The [main JX files](#main_jx) prepare the environment for the workflow step so that each workflow step has minimal configuration to concern itself with.

## Supporting Scripts
There `cache_results.py` script is used to move the meaningful outputs as returned from each workflow step into a cache folder.
The files stored in the cache are considered to be the final output of each processing step.
After the files are cached, it's possible to remove the  workspace folders.
If copies of the input files are used for processing, it's also possible to remove the input used by each workflow step after the outputs are cached; cleaning up the input files should not be done if they are the only copy!
 
## Docker
Refer to the Docker specifc README.md on creating and running a Docker image.