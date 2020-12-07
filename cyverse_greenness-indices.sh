#!/bin/bash

# Get the file JSON list
if [[ "${1}" == "" ]]; then
  echo "The JSON file containing the file list was not specified for greenness indices"
  exit 1
fi
FILE_LIST_JSON="${1}"

# No options supported at this time
OPTIONS=""

# Copy the json file to the correct place
cp "${FILE_LIST_JSON}" "/scif/apps/src/greenness-indices_files.json"

echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"GREENNESS_INDICES_OPTIONS\"=\"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run greenness-indices
