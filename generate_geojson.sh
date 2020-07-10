#/bin/bash

FILE_PARAM="${1}"
if [[ ! "${2}" == "" ]]; then
  DESTINATION_FILE="${2}"
else
  DESTINATION_FILE="/output/plots.json"
fi

if [[ ${FILE_PARAM} == http* ]]; then
  scif run betydb2geojson "${FILE_PARAM}" "${DESTINATION_FILE}"
elif [[ ${FILE_PARAM} == *.shp ]]; then
  scif run shp2geojson "${FILE_PARAM}" "${DESTINATION_FILE}"
elif [[ ${FILE_PARAM} == *.json ]]; then
  cp "${FILE_PARAM}" "${DESTINATION_FILE}"
else
  echo "Unknown plot geometries file specified: \"${FILE_PARAM}\""
  exit -1
fi
