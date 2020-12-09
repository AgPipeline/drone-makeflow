#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the folder that's top level
if [[ "${1}" == "" ]]; then
  echo "Top level folder not specified"
  exit 1
fi
TOP_LEVEL_FOLDER="${1}"

# Check for options
if [[ "${2}" != "" ]]; then
  OPTIONS="${2}"
else
  OPTIONS=""
fi

echo "Merging CSV files from '${WORKING_FOLDER}/${TOP_LEVEL_FOLDER}' to '${WORKING_FOLDER}'"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"MERGECSV_SOURCE\": \"${WORKING_FOLDER}/${TOP_LEVEL_FOLDER}\","
  echo "\"MERGECSV_TARGET\": \"${WORKING_FOLDER}/merged_csv\","
  echo "\"MERGECSV_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run merge_csv
