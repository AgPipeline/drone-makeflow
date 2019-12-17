# Makeflow for Drone Processing Pipeline
<img src="https://github.com/az-digitalag/Drone-Processing-Pipeline/raw/07b1edc34a1faea501c80f583beb07f9d6b290bb/resources/drone-pipeline.png" width="100" />

This repository contains the files used to run containers in the [Makeflow](https://cctools.readthedocs.io/en/latest/makeflow) environment.

## Overview
Each container to be run has its own [.jx](https://cctools.readthedocs.io/en/latest/jx/jx/) file containing everything needed to run the image and locally cache the results.
The basic flow in each of these .jx files is to create needed folders, run the docker container, and cache the results.

Coordination of these smaller workflows is done through the simple `run_makeflow.sh` script.

The sequence of the overall workflow is: `odm_workflow -> soil_mask_workflow -> plot_clip_workflow -> canopy_cover_workflow`.


