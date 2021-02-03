#!/bin/bash

# Check for a filename override
FILENAME="canopycover.csv"
if [[ ! "${1}" == "" ]]; then
  FILENAME="${1}"
fi
echo "Checking files named ${FILENAME}"

TRUTH_FOLDER="test_data"
if [[ ! "${2}" == "" ]]; then
  TRUTH_FOLDER="${2}"
fi
echo "Searching folder ${TRUTH_FOLDER}"

COMPARE_FOLDER="outputs"
if [[ ! "${3}" == "" ]]; then
  COMPARE_FOLDER="${3}"
fi
echo "Comparison folder ${COMPARE_FOLDER}"

PRIMARY_KEY_COLUMNS="4"
if [[ ! "${4}" == "" ]]; then
  PRIMARY_KEY_COLUMNS="${4}"
fi
echo "Primary key columns ${PRIMARY_KEY_COLUMNS}"

COMPARE_COLUMNS="1"
if [[ ! "${5}" == "" ]]; then
  COMPARE_COLUMNS="${5}"
fi
echo "Columns to compare ${COMPARE_COLUMNS}"

TRUTH_FOLDER_LEN="${#TRUTH_FOLDER}"
# shellcheck disable=SC2207
FOLDER_LIST=($(find "${TRUTH_FOLDER}/" -maxdepth 1 -type d))

# Get the line count of differences between the files
for subfolder in "${FOLDER_LIST[@]}"; do
  WORKING_FOLDER="${subfolder:${TRUTH_FOLDER_LEN}}"

  if [[ "${WORKING_FOLDER}" == "" ]]; then
    continue
  fi
  if [[ "${WORKING_FOLDER}" == "/" ]]; then
    continue
  fi

  # shellcheck disable=SC2126
  DIFF_RESULT="$(./csvdiff/csvdiff "${TRUTH_FOLDER}/${WORKING_FOLDER}/${FILENAME}" "${COMPARE_FOLDER}/${WORKING_FOLDER}/${FILENAME}" --columns 1 --primary-key "${PRIMARY_KEY_COLUMNS}" --format rowmark 2>&1 | grep -A 5 'Rows:' | wc -l | tr -d '[:space:]')"

  if [[ "${DIFF_RESULT}" == "1" ]]; then
    echo "No differences: ${TRUTH_FOLDER}/${WORKING_FOLDER} for file ${FILENAME}"
  else
    echo "Error: folder ${TRUTH_FOLDER}/${WORKING_FOLDER} file ${FILENAME} doesn't match"
    echo "Comparison folder listing"
    ls -l "${COMPARE_FOLDER}/${WORKING_FOLDER}"
    echo "Generated file contents"
    cat "${TRUTH_FOLDER}/${WORKING_FOLDER}/${FILENAME}"
    echo "Comparison file contents"
    cat "${COMPARE_FOLDER}/${WORKING_FOLDER}/${FILENAME}"
    echo "CSV differences result"
    ./csvdiff/csvdiff "${TRUTH_FOLDER}/${WORKING_FOLDER}/${FILENAME}" "${COMPARE_FOLDER}/${WORKING_FOLDER}/${FILENAME}" --columns 1 --primary-key 4 --format rowmark
    exit 10
  fi
done
