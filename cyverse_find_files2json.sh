#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the folder to search
if [[ "${1}" == "" ]]; then
  echo "Top level searching folder not specified"
  exit 1
fi
SEARCH_FOLDER="${1}"

# Check for a file name to search for
if [[ "${2}" == "" ]]; then
  echo "A file to search for was not specified"
  exit 2
fi
SEARCH_NAME="${2}"

# Since CyVerse appears to change parameter order depending upon how the app is defined
# we need to check the parameters and adjust as needed
if [ ! -d "${WORKING_FOLDER}/${SEARCH_FOLDER}" ]; then
  # Check if the other parameter is a folder and swap if it is. Do nothing otherwise
  # allowing the error to be caught later
  if [ -d "${WORKING_FOLDER}/${SEARCH_NAME}" ]; then
    SWAP="${SEARCH_FOLDER}"
    SEARCH_FOLDER="${SEARCH_NAME}"
    SEARCH_NAME="${SWAP}"
    echo "Swapping to use folder: ${SEARCH_FOLDER} and file name: ${SEARCH_NAME}"
  fi
fi

echo "Searching for files named '${SEARCH_NAME}' starting in folder '${WORKING_FOLDER}/${SEARCH_FOLDER}'"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"FILES2JSON_SEARCH_NAME\": \"${SEARCH_NAME}\","
  echo "\"FILES2JSON_SEARCH_FOLDER\": \"${WORKING_FOLDER}/${SEARCH_FOLDER}\","
  echo "\"FILES2JSON_JSON_FILE\": \"${WORKING_FOLDER}/found_files.json\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run find_files2json
