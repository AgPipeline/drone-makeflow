#!/bin/bash

# Define some counts that we expect
EXPECTED_NUM_CANOPYCOVER_CSV=57

# What folder are we looking in for outputs
if [[ ! "${1}" == "" ]]; then
  TARGET_FOLDER="${1}"
else
  TARGET_FOLDER="./outputs"
fi

# Check the expected number of output files
# shellcheck disable=SC2207
EXPECTED_CSV=($(find "${TARGET_FOLDER}/" -type f | grep 'canopycover\.csv' | grep -v 'test_data'))
if [[ "${#EXPECTED_CSV[@]}" == "${EXPECTED_NUM_CANOPYCOVER_CSV}" ]]; then
  echo "Found expected number of canopycover.csv files: ${EXPECTED_NUM_CANOPYCOVER_CSV}"
else
  echo "Expected ${EXPECTED_NUM_CANOPYCOVER_CSV} canopycover.csv files but found ${#EXPECTED_CSV[@]}"
  for i in $(seq 0 $((${#EXPECTED_CSV[@]} - 1))); do
    echo "$((i + 1)): ${EXPECTED_CSV[$i]}"
  done
  exit 20
fi
