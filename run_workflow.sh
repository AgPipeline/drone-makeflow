#!/bin/bash

WORKFLOW_FILE="run_workflow.jx"
CONFIGURATION_FILE="canopycover_workflow.yml"
SOURCE_IMAGES_DIR="/mnt/test/images/"
EXPERIMENT_FILENAME="experiment.yaml"

if [ -n "${1}" ]; then
  CONFIGURATION_FILE="${1}"
fi;
echo "Using configuration file: ${CONFIGURATION_FILE}"
if [ -n "${2}" ]; then
  SOURCE_IMAGES_DIR="${2}"
fi;
echo "Using source file: ${SOURCE_IMAGES_DIR}"

echo "Converting YAML to JSON for makeflow"
printf "
import yaml
import json
import tempfile
import os
f = open('${CONFIGURATION_FILE}','r')
y = yaml.safe_load(f)
script_folder = os.path.dirname(os.path.realpath('${0}')) + '/'
#if configuration' in y and 'working_space' in y['configuration']:
#    working_folder = tempfile.mkdtemp(dir=y['configuration']['working_space'])
#    y['configuration']['working_space'] = working_folder
if 'configuration' in y:
    y['configuration']['experiment_filename'] = '${EXPERIMENT_FILENAME}'
    y['configuration']['source_data_folder_name'] = 'images'
    y['configuration']['cache_folder_name'] = 'cache'
    y['configuration']['script_folder'] = script_folder
if 'workflow' in y:
    step_source_files = [None] * (len(y['workflow']) + 2)
    step_source_files[1] = '${SOURCE_IMAGES_DIR}'
    for step in y['workflow']:
        next_step = int(step['execution_order']) + 1
        step_source_files[next_step] = os.path.join(os.path.join(y['configuration']['working_space'], os.path.splitext(os.path.basename(step['makeflow_file']))[0]), y['configuration']['cache_folder_name']) + '/'
    for step in y['workflow']:
        step['next_step'] = int(step['execution_order']) + 1
        step['step_folder'] = os.path.splitext(os.path.basename(step['makeflow_file']))[0] + '/'
        step['sources_folder'] = step_source_files[int(step['execution_order'])]
with open('./canopycover_workflow.json','w') as o:
    json.dump(y, o, indent=2)" | python3 -

echo Running workflow: "${WORKFLOW_FILE}"
echo Configuration file: "${CONFIGURATION_FILE}"
#makeflow --jx "${WORKFLOW_FILE}" --jx-args "${CONFIGURATION_FILE}"

