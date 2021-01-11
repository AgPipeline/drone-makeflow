#!/bin/bash

WORKING_FOLDER=$(pwd)
# List of folders to exclude from the results
EXCLUDE_FOLDERS=("logs")

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

# Add the excluded folders to the options
EXCLUDE_FOLDER_OPTION=""
EXCLUDE_FOLDER_SEPARATOR=""
for i in "${EXCLUDE_FOLDERS[@]}"; do
  EXCLUDE_FOLDER_OPTION="${i}${EXCLUDE_FOLDER_SEPARATOR}${EXCLUDE_FOLDER_OPTION}"
  EXCLUDE_FOLDER_SEPARATOR=","
done
if [[ "${EXCLUDE_FOLDER_OPTION}" != "" ]]; then
  OPTIONS="${OPTIONS} --ignore-dirs \\\"${EXCLUDE_FOLDER_OPTION}\\\" "
fi

mkdir -p "${WORKING_FOLDER}/merged_csv"
echo "Merging CSV files from '${WORKING_FOLDER}/${TOP_LEVEL_FOLDER}' to '${WORKING_FOLDER}/merged_csv'"
echo "  with options: ${OPTIONS}"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"MERGECSV_SOURCE\": \"${WORKING_FOLDER}/${TOP_LEVEL_FOLDER}\","
  echo "\"MERGECSV_TARGET\": \"${WORKING_FOLDER}/merged_csv\","
  echo "\"MERGECSV_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

echo "JSON Args file:"
cat "/scif/apps/src/jx-args.json"
scif run merge_csv
