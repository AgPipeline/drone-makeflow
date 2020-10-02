#!/bin/bash

# Define some counts that we expect (the number of sub-folders plus the top folder)
EXPECTED_NUM_FOLDERS=58
EXPECTED_NUM_CANOPYCOVER_CSV=56
# The same number of CSV files + original, un-clipped mask file
EXPECTED_NUM_MASK_TIF=$((EXPECTED_NUM_CANOPYCOVER_CSV + 1))

# What folder are we looking in for outputs
if [[ ! "${1}" == "" ]]; then
  TARGET_FOLDER="${1}"
else
  TARGET_FOLDER="./outputs"
fi

# Check for the mask output file
CHECK_FILE="${TARGET_FOLDER}/orthomosaic_mask.tif"
if [[ -f "${CHECK_FILE}" ]]; then
  echo "Mask file found: ${CHECK_FILE}"
else
  echo "Unable to find mask file: ${CHECK_FILE}"
  exit 1
fi

# Get all the folders and check the count
FOLDER_LIST=($(find "${TARGET_FOLDER}/" -maxdepth 1 -type d))
if [[ "${#FOLDER_LIST[@]}" == "${EXPECTED_NUM_FOLDERS}" ]]; then
  echo "Found expected number of folders: ${EXPECTED_NUM_FOLDERS}"
else
  echo "Expected ${EXPECTED_NUM_FOLDERS} folders and found ${#FOLDER_LIST[@]}"
  for i in $(seq 0 $((${#FOLDER_LIST[@]} - 1))); do
    echo "$((${i} + 1)): ${FOLDER_LIST[$i]}"
  done
  exit 10
fi

# Check the expected number of output files
EXPECTED_CSV=($(find "${TARGET_FOLDER}/" -type f | grep 'canopycover\.csv'))
if [[ "${#EXPECTED_CSV[@]}" == "${EXPECTED_NUM_CANOPYCOVER_CSV}" ]]; then
  echo "Found expected number of canopycover.csv files: ${EXPECTED_NUM_CANOPYCOVER_CSV}"
else
  echo "Expected ${EXPECTED_NUM_CANOPYCOVER_CSV} canopycover.csv files but found ${#EXPECTED_CSV[@]}"
  for i in $(seq 0 $((${#EXPECTED_CSV[@]} - 1))); do
    echo "$((${i} + 1)): ${EXPECTED_CSV[$i]}"
  done
  exit 20
fi

# Check the expected number of image mask files
EXPECTED_MASK=($(find "${TARGET_FOLDER}/" -type f | grep 'orthomosaic_mask\.tif'))
if [[ "${#EXPECTED_MASK[@]}" == "${EXPECTED_NUM_MASK_TIF}" ]]; then
  echo "Found expected number of orthomosaic_mask.tif files: ${EXPECTED_NUM_MASK_TIF}"
else
  echo "Expected ${EXPECTED_NUM_MASK_TIF} orthomosaic_mask.tif files but found ${#EXPECTED_MASK[@]}"
  for i in $(seq 0 $((${#EXPECTED_MASK[@]} - 1))); do
    echo "$((${i} + 1)): ${EXPECTED_MASK[$i]}"
  done
  exit 30
fi
