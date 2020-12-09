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

# Search for YAML files that can be used as metadata
OPTIONS=""
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".yml")
      OPTIONS=${OPTIONS}" --metadata ${ONE_FILE}"
      ;;
  esac
  case "${ONE_FILE: -5}" in
    ".json")
      if [[ "${PLOTGEOMETRY_FILE}" != "${ONE_FILE}" ]]; then
        OPTIONS=${OPTIONS}" --metadata ${ONE_FILE}"
      fi
      ;;
    ".yaml")
      OPTIONS=${OPTIONS}" --metadata ${ONE_FILE}"
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -type f -print0)

echo "Clipping image '${WORKING_FOLDER}/${SOURCE_FILE}' using geometries from '${WORKING_FOLDER}/${PLOTGEOMETRY_FILE}'"
echo "  Options: '${OPTIONS}'"
  echo "{" >"/scif/apps/src/jx-args.json"
  {
    echo "\"PLOTCLIP_SOURCE_FILE\": \"${WORKING_FOLDER}/${SOURCE_FILE}\","
    echo "\"PLOTCLIP_PLOTGEOMETRY_FILE\": \"${WORKING_FOLDER}/${PLOTGEOMETRY_FILE}\","
    echo "\"PLOTCLIP_WORKING_FOLDER\": \"${WORKING_FOLDER}/plot_clip\","
    echo "\"PLOTCLIP_OPTIONS\": \"${OPTIONS}\""
    echo "}"
  } >>"/scif/apps/src/jx-args.json"

scif run plotclip
