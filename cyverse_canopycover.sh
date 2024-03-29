#!/bin/bash

WORKING_FOLDER=$(pwd)
# List of folders to exclude from the results
EXCLUDE_FOLDERS=("/logs/")

# Get the file JSON list
if [[ "${1}" == "" ]]; then
  echo "The JSON file containing the file list was not specified for canopycover"
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
cp "${FILE_LIST_JSON}" "/scif/apps/src/canopy_cover_files.json"

echo "Calculating canopy cover using files listed in '${FILE_LIST_JSON}'"
echo "  using options: ${OPTIONS}"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"CANOPYCOVER_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

echo "JSON Args file:"
cat "/scif/apps/src/jx-args.json"
scif run canopycover

# Copy the CSV files to the working folder as output
FOUND_FILES=()
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".csv")
      # Look for the excluded folders
      EXCLUDE_THIS_FILE="false"
      for i in "${EXCLUDE_FOLDERS[@]}"; do
        if [[ "${ONE_FILE}" == *"${i}"* ]]; then
          EXCLUDE_THIS_FILE="true"
          break
        fi
      done
      if [ "${EXCLUDE_THIS_FILE}" == "false" ]; then
        FOUND_FILES+=("${ONE_FILE}")
      fi
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -type f -print0)

DESTINATION_FOLDER="${WORKING_FOLDER}/canopycover"
for i in "${FOUND_FILES[@]}"; do
  FILE_NAME=$(basename "${i}")
  FILE_PATH=$(dirname "${i}")
  LAST_FOLDER_NAME=$(basename "${FILE_PATH}")
  # Only copy files where the destination is not the same as the origin
  if [[ "${i}" != "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}" ]]; then
    mkdir -p "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}"
    mv -v -f "${i}" "${DESTINATION_FOLDER}/${LAST_FOLDER_NAME}/${FILE_NAME}"
  fi
done
