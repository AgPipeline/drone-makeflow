#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the image file
if [[ "${1}" == "" ]]; then
  echo "Image to clip to plots is not specified"
  exit 1
fi
SOURCE_FILE="${1}"

# Get the geometry file
if [[ "${2}" == "" ]]; then
  echo "The plot geometry GeoJSON file is not specified"
  exit 2
fi
PLOTGEOMETRY_FILE="${2}"

# No supported options at this time
OPTIONS=""

echo "Merging CSV files from '${WORKING_FOLDER}/${TOP_LEVEL_FOLDER}' to '${WORKING_FOLDER}'"
  echo "{" >"/scif/apps/src/jx-args.json"
  {
    echo "\"PLOTCLIP_SOURCE_FILE\"=\"${SOURCE_FILE}\","
    echo "\"PLOTCLIP_PLOTGEOMETRY_FILE\"=\"${PLOTGEOMETRY_FILE}\","
    echo "\"PLOTCLIP_WORKING_FOLDER\"=\"${WORKING_FOLDER}\","
    echo "\"PLOTCLIP_OPTIONS\"=\"${OPTIONS}\""
    echo "}"
  } >>"/scif/apps/src/jx-args.json"

scif run plotclip
