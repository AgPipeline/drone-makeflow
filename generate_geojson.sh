#!/bin/bash

FILE_PARAM="${1}"
if [[ "${2}" != "" ]]; then
  DESTINATION_FILE="${2}"
else
  DESTINATION_FILE="/output/plots.json"
fi

if [[ "${3}" != *"--clean"* ]]; then
  if [[ ${FILE_PARAM} == http* ]]; then
    scif run betydb2geojson --betydb_url "${FILE_PARAM}" "${DESTINATION_FILE}"
  elif [[ ${FILE_PARAM} == *.shp ]]; then
    scif run shp2geojson "${FILE_PARAM}" "${DESTINATION_FILE}"
  elif [[ ${FILE_PARAM} == *.json || ${FILE_PARAM} == *.geojson ]]; then
    cp "${SCIF_APPDATA_odm_workflow}/images/${FILE_PARAM}" "${DESTINATION_FILE}"
  else
    echo "Unknown plot geometries file specified: \"${FILE_PARAM}\""
    exit 1
  fi
else
  rm "${DESTINATION_FILE}"
fi