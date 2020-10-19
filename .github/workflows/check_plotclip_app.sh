#!/bin/bash

# Define some counts that we expect (the number of sub-folders plus the top folder)
EXPECTED_NUM_FOLDERS=58
EXPECTED_NUM_CLIPS=58
# Make file to look for: should match what's in the configuration JSON file
MASK_FILE_NAME="orthomosaicmask.tif"
MASK_FILE_NAME_GREP="orthomosaicmask\\.tif"

# What folder are we looking in for outputs
if [[ ! "${1}" == "" ]]; then
  TARGET_FOLDER="${1}"
else
  TARGET_FOLDER="./outputs"
fi

# Get all the folders and check the count
# shellcheck disable=SC2207
FOLDER_LIST=($(find "${TARGET_FOLDER}/" -maxdepth 1 -type d))
if [[ "${#FOLDER_LIST[@]}" == "${EXPECTED_NUM_FOLDERS}" ]]; then
  echo "Found expected number of folders: ${EXPECTED_NUM_FOLDERS}"
else
  echo "Expected ${EXPECTED_NUM_FOLDERS} folders and found ${#FOLDER_LIST[@]}"
  for i in $(seq 0 $((${#FOLDER_LIST[@]} - 1))); do
    echo "$((i + 1)): ${FOLDER_LIST[$i]}"
  done
  exit 10
fi

# Check the expected number of image mask files
# shellcheck disable=SC2207
EXPECTED_CLIPS=($(find "${TARGET_FOLDER}/" -type f | grep "${MASK_FILE_NAME_GREP}"))
if [[ "${#EXPECTED_CLIPS[@]}" == "${EXPECTED_NUM_CLIPS}" ]]; then
  echo "Found expected number of ${MASK_FILE_NAME} files: ${EXPECTED_NUM_CLIPS}"
else
  echo "Expected ${EXPECTED_NUM_CLIPS} ${MASK_FILE_NAME} files but found ${#EXPECTED_CLIPS[@]}"
  for i in $(seq 0 $((${#EXPECTED_CLIPS[@]} - 1))); do
    echo "$((i + 1)): ${EXPECTED_CLIPS[$i]}"
  done
  exit 30
fi
