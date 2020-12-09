#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the file JSON list
if [[ "${1}" == "" ]]; then
  echo "The JSON file containing the file list was not specified for canopycover"
  exit 1
fi
FILE_LIST_JSON="${1}"

# No options supported at this time
OPTIONS=""

# Copy the json file to the correct place
cp "${FILE_LIST_JSON}" "/scif/apps/src/canopy_cover_files.json"

echo "Calculating canopy cover using files listed in '${FILE_LIST_JSON}'"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"CANOPYCOVER_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run canopycover

# Copy the CSV files to the working folder as output
FOUND_FILES=()
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".csv")
      FOUND_FILES+=("${ONE_FILE}")
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -type f -print0)

for i in "${FOUND_FILES[@]}"; do
  FILE_NAME=$(basename "${i}")
  FILE_PATH=$(dirname "${i}")
  LAST_FOLDER_NAME=$(basename "${FILE_PATH}")
  # Only copy files where the destination is not the same as the origin
  if [[ "${i}" != "${WORKING_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}" ]]; then
    mkdir -p "${WORKING_FOLDER}/${LAST_FOLDER_NAME}"
    cp -f "${i}" "${WORKING_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}"
  fi
done
