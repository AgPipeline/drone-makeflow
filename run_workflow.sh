#!/bin/bash

CLEANING="NO"

while getopts ch opt; do
  case $opt in
    c)
      CLEANING="YES"
      ;;
    h)
      echo "Supported environment variables:"
      echo "  CONFIGURATION_FILE the .yml or .yaml file defining the workflow to run"
      echo "  SOURCES_DIR the folder containing the source files"
      echo "  EXPERIMENT_FILE the file containing experiment data used by the workflow"
      exit 0
      ;;
  esac
done

WORKFLOW_FILE="run_workflow.jx"
CONFIGURATION_FILE=${CONFIGURATION_FILE:-"/canopycover_workflow.yml"}
CONFIGURATION_JSON_FILE="workflow_configuration.json"
SOURCES_DIR=${SOURCES_DIR:-"/images/"}
EXPERIMENT_FILE=${EXPERIMENT_FILE:-"/experiment.yaml"}

echo "Using workflow: ${WORKFLOW_FILE}"
echo "Using configuration file: ${CONFIGURATION_FILE}"
echo "Using source file: ${SOURCES_DIR}"
echo "Using experiment information file: ${EXPERIMENT_FILE}"

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
    y['configuration']['experiment_file'] = '${EXPERIMENT_FILE}'
    y['configuration']['experiment_filename'] = os.path.basename('${EXPERIMENT_FILE}')
    y['configuration']['source_data_folder_name'] = 'images'
    y['configuration']['cache_folder_name'] = 'cache'
    y['configuration']['script_folder'] = script_folder
    if 'betydb_url' not in y['configuration']:
        y['configuration']['betydb_url'] = ''
    if 'betydb_key' not in y['configuration']:
        y['configuration']['betydb_key'] = ''
if 'workflow' in y:
    step_source_files = [None] * (len(y['workflow']) + 2)
    step_source_files[1] = '${SOURCES_DIR}'
    for step in y['workflow']:
        next_step = int(step['execution_order']) + 1
        step_source_files[next_step] = os.path.join(os.path.join(y['configuration']['working_space'], os.path.splitext(os.path.basename(step['makeflow_file']))[0]), y['configuration']['cache_folder_name']) + '/'
    for step in y['workflow']:
        step['next_step'] = int(step['execution_order']) + 1
        step['step_folder'] = os.path.splitext(os.path.basename(step['makeflow_file']))[0] + '/'
        step['sources_folder'] = step_source_files[int(step['execution_order'])]
with open('${CONFIGURATION_JSON_FILE}','w') as o:
    json.dump(y, o, indent=2)
if 'workflow' in y:
    for idx in range(1, len(y['workflow'])+1):
        link_name = 'sub_workflow{}.jx'.format(idx)
        if os.path.isfile(link_name):
            os.unlink(link_name)
        os.link('sub_workflow.jx', link_name)
" | python3 -

if [ "${CLEANING}" == "YES" ]; then
  if [ -s "${CONFIGURATION_JSON_FILE}" ]; then
    echo "Cleaning previous run."
    makeflow --jx "${WORKFLOW_FILE}" --jx-args "${CONFIGURATION_JSON_FILE}" --clean --skip-file-check
  else
    echo "Missing configuration file needed for cleanup: '${CONFIGURATION_JSON_FILE}'"
    echo "Unable to run cleanup"
  fi
  exit 0
fi

echo Running workflow: "${WORKFLOW_FILE}"
echo Configuration JSON file: "${CONFIGURATION_JSON_FILE}"
makeflow --jx "${WORKFLOW_FILE}" --jx-args "${CONFIGURATION_JSON_FILE}"

printf "
import yaml
import os
f = open('${CONFIGURATION_FILE}','r')
y = yaml.safe_load(f)
if 'workflow' in y:
    for idx in range(1, len(y['workflow'])+1):
        link_name = 'sub_workflow{}.jx'.format(idx)
        if os.path.isfile(link_name):
            os.unlink(link_name)
" | python3 -
