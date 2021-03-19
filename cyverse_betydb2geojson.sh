#!/bin/bash

WORKING_FOLDER=$(pwd)

# Check the BETYdb URL
if [[ "${1}" == "" ]]; then
  echo "A BETYdb URL has not been specified"
  exit 1
fi
BETYDB_URL="${1}"

# Check for BETYdb filter options
if [[ "${2}" != "" ]]; then
  BETYDB_FILTERS="${2}"
else
  BETYDB_FILTERS=""
fi

echo "Fetching plot geometries from '${BETYDB_URL}' to save as GeoJSON"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"PLOT_GEOMETRY_FILE\": \"${WORKING_FOLDER}/plots.json\","
  echo "\"BETYDB_URL\": \"${BETYDB_URL}\","
  echo "\"BETYDB_OPTIONS\": \"${BETYDB_FILTERS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

echo "JSON Args file:"
cat "/scif/apps/src/jx-args.json"
scif run betydb2geojson
