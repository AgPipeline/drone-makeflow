#!/bin/bash
ORTHOMOSAIC_NAME="${1}_mask.tif"
OUTPUT_FOLDER="/output"
echo "Orthomosaic name to look for: ${ORTHOMOSAIC_NAME}"
clips=("${OUTPUT_FOLDER}/*")
echo "${clips}"

found_files=0
echo "{\"CANOPYCOVER_FILE_LIST\": [" >>"${OUTPUT_FOLDER}/canopycover_fileslist.json"
sep=""
for entry in ${clips[@]}; do
  possible="${entry}/${ORTHOMOSAIC_NAME}"
  echo "Checking possible ${possible}"
  if [ -f "${possible}" ]; then
    echo "${sep}{\"FILE\": \"${possible}\"," >>"${OUTPUT_FOLDER}/canopycover_fileslist.json"
    echo "\"DIR\": \"${entry}/\"}" >>"${OUTPUT_FOLDER}/canopycover_fileslist.json"
    sep=","
    ((found_files++))
  fi
done
echo "]}" >>"${OUTPUT_FOLDER}/canopycover_fileslist.json"

if [ "$found_files" -eq "0" ]; then
  rm "${OUTPUT_FOLDER}/canopycover_fileslist.json"
fi
