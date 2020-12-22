#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the shapefile name
SHAPEFILE_NAME=""
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".shp")
      SHAPEFILE_NAME=${ONE_FILE#"$(dirname "${ONE_FILE}")/"}
      ;;
  esac
done < <(find "${WORKING_FOLDER}" -type f -print0)

if [[ "${SHAPEFILE_NAME}" == "" ]]; then
  echo "A shapefile was not specified found"
  exit 1
fi

echo "Converting plot geometries from shapefile '${SHAPEFILE_NAME}' to GeoJSON"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"PLOT_SHAPEFILE\": \"${WORKING_FOLDER}/${SHAPEFILE_NAME}\","
  echo "\"PLOT_GEOMETRY_FILE\": \"${WORKING_FOLDER}/plots.json\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

scif run shp2geojson
