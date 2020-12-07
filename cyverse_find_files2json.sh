#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the folder to search
if [[ "${1}" == "" ]]; then
  echo "Top level searching folder not specified"
  exit 1
fi
SEARCH_FOLDER="{1}"

# Check for a file name to search for
if [[ "${2}" == "" ]]; then
  echo "A file to search for was not specified"
  exit 2
fi
SEARCH_NAME="${2}"

echo "Searching for files named '${SEARCH_NAME}' starting in folder '${WORKING_FOLDER}/${SEARCH_FOLDER}'"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"FILES2JSON_SEARCH_NAME\"=\"${SEARCH_NAME}\","
  echo "\"FILES2JSON_SEARCH_FOLDER\"=\"${WORKING_FOLDER}/${SEARCH_FOLDER}\","
  echo "\"FILES2JSON_JSON_FILE\"=\"${WORKING_FOLDER}/found_files.json\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run find_files2json
