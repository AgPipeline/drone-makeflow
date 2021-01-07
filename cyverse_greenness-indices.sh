#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the file JSON list
if [[ "${1}" == "" ]]; then
  echo "The JSON file containing the file list was not specified for greenness indices"
  exit 1
fi
FILE_LIST_JSON="${1}"

# No command line options are supported at this time
OPTIONS=""

# Look for YAML files to use as metadata
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".yml")
      OPTIONS="${OPTIONS} --metadata ${ONE_FILE}"
      ;;
  esac
  case "${ONE_FILE: -5}" in
    ".yaml")
      OPTIONS="${OPTIONS} --metadata ${ONE_FILE}"
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -maxdepth 1 -type f -print0)

# Copy the json file to the correct place
cp "${FILE_LIST_JSON}" "/scif/apps/src/greenness-indices_files.json"

echo "Calculating greenness indices using files listed in '${FILE_LIST_JSON}'"
echo "  using options: ${OPTIONS}"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"GREENNESS_INDICES_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run greenness-indices

# Copy the CSV files to the working folder as output
FOUND_FILES=()
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".csv")
      FOUND_FILES+=("${ONE_FILE}")
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -type f -print0)

DESTINATION_FOLDER="${WORKING_FOLDER}/greenness"
for i in "${FOUND_FILES[@]}"; do
  FILE_NAME=$(basename "${i}")
  FILE_PATH=$(dirname "${i}")
  LAST_FOLDER_NAME=$(basename "${FILE_PATH}")
  # Only copy files where the destination is not the same as the origin
  if [[ "${i}" != "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}" ]]; then
    mkdir -p "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}"
    cp -f "${i}" "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}"
  fi
done
