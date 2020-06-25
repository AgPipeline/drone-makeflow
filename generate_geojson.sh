#/bin/bash

FILE_PARAM="${1}"

if [[ ${FILE_PARAM} == http* ]]; then
  scif run betydb2geojson "${FILE_PARAM}"
elif [[ ${FILE_PARAM} == *.shp ]]; then
  scif run shp2geojson "${FILE_PARAM}"
elif [[ ${FILE_PARAM} == *.json ]]; then
  cp "${FILE_PARAM}" "${SCIF_APPDATA_soilmask}/plots.json"
else
  echo "Unknown plot geometries file specified: \"${FILE_PARAM}\""
  exit -1
fi
