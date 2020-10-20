#!/bin/bash

# Make sure we have our parameters
if [[ "${1}" == "" ]]; then
  echo "Missing filename to search for"
  exit 1
fi
if [[ "${2}" == "" ]]; then
  echo "Missing folder to search through"
  exit 2
fi
if [[ "${3}" == "" ]]; then
  echo "Missing destination file for JSON"
  exit 3
fi

SEARCH_NAME="${1}"
SEARCH_FOLDER="${2}"
JSON_FILE="${3}"

echo "File name to look for: ${SEARCH_NAME}"
echo "Searching in folder: ${SEARCH_FOLDER}"

# shellcheck disable=SC2206
clips=(${SEARCH_FOLDER}/*)
echo "${clips[@]}"

found_files=0
echo "{\"FILE_LIST\": [" >>"${JSON_FILE}"
sep=""
for entry in "${clips[@]}"; do
  possible="${entry}/${SEARCH_NAME}"
  echo "Checking possible ${possible}"
  if [ -f "${possible}" ]; then
    echo "${sep}{\"FILE\": \"${possible}\"," >>"${JSON_FILE}"
    echo "\"DIR\": \"${entry}/\"}" >>"${JSON_FILE}"
    sep=","
    ((found_files++))
  fi
done
echo "]}" >>"${JSON_FILE}"

if [ "$found_files" -eq "0" ]; then
  rm "${JSON_FILE}"
fi

echo "Found ${found_files} files"
