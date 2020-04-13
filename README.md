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
 
