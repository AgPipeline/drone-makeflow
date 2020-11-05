#!/bin/bash

# Check for a filename override
FILENAME="canopycover.csv"
if [[ ! "${1}" == "" ]]; then
  FILENAME="${1}"
fi;
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

TRUTH_FOLDER_LEN="${#TRUTH_FOLDER}"
FOLDER_LIST=($(find "${TRUTH_FOLDER}/" -maxdepth 1 -type d))

# Get the line count of differences between the files
for subfolder in "${FOLDER_LIST[@]}"
do
  WORKING_FOLDER="${subfolder:${TRUTH_FOLDER_LEN}}"

  if [[ "${WORKING_FOLDER}" == ""  ]]; then
    continue
  fi
  if [[ "${WORKING_FOLDER}" == "/"  ]]; then
    continue
  fi

  DIFF_RESULT="$(./csvdiff/csvdiff "${TRUTH_FOLDER}/${WORKING_FOLDER}/${FILENAME}" "${COMPARE_FOLDER}/${WORKING_FOLDER}/${FILENAME}" --columns 1 --primary-key 4 --format rowmark 2>&1 | grep -A 5 'Rows:' | wc -l  | tr -d '[:space:]')"

  if [[ "${DIFF_RESULT}" == "1" ]]; then
    echo "No differences: ${TRUTH_FOLDER}/${WORKING_FOLDER} for file ${FILENAME}"
  else
    echo "Error: folder ${TRUTH_FOLDER}/${WORKING_FOLDER} file ${FILENAME} doesn't match"
    echo "Folder listing"
    ls -l "${COMPARE_FOLDER}/${WORKING_FOLDER}"
    echo "File contents"
    cat "${COMPARE_FOLDER}/${WORKING_FOLDER}/${FILENAME}"
    exit 10
  fi
done
