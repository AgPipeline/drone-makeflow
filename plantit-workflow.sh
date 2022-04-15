#!/bin/bash

# INPUT=$PWD/test_data  WORKDIR=$PWD WORKFLOW_TO_RUN="Canopy Cover with normal soil masking" ./plantit-workflow.sh
# cat /scif/apps/src/jx-args.json

# Initialize variables
IMAGE_FILE=
PLOTS_FILE=
ALGO_OPTIONS=""

echo "INPUT FOLDER ${INPUT}"
echo "WORKING FOLDER ${WORKDIR}"

# clone the repo
cd /scif/apps/src || exit
git init
git remote add origin https://github.com/Chris-Schnaufer/drone-makeflow.git
git pull origin main --allow-unrelated-histories

# update permissions for shell and python scripts
chmod a+x /scif/apps/src/*.sh
chmod a+x /scif/apps/src/*.py

# Find the files we need or are optional
IS_GEOJSON=false
while IFS= read -r -d '' ONE_FILE; do
  case "${ONE_FILE: -4}" in
    ".tif")
      IMAGE_FILE="${ONE_FILE}"
      ;;
    ".yml")
      ALGO_OPTIONS="${ALGO_OPTIONS} --metadata ${ONE_FILE}"
      ;;
  esac
  case "${ONE_FILE: -5}" in
    ".json")
      # Choose a .geojson file over a .json
      if [[ "${PLOTS_FILE}" == "" || $IS_GEOJSON == false ]]; then
        PLOTS_FILE="${ONE_FILE}"
      fi
      ;;
    ".tiff")
      IMAGE_FILE="${ONE_FILE}"
      ;;
    ".yaml")
      ALGO_OPTIONS="${ALGO_OPTIONS} --metadata ${ONE_FILE}"
      ;;
  esac
  case "${ONE_FILE: -8}" in
    ".geojson")
      PLOTS_FILE="${ONE_FILE}"
      IS_GEOJSON=true
      ;;
  esac
done < <(find "${INPUT}" -maxdepth 1 -type f -print0)

# Make sure we have mandatory files
if [[ "${IMAGE_FILE}" == "" ]]; then
  echo "Unable to find source image file (*.tif or *.tiff)"
  exit 10
fi
if [[ "${PLOTS_FILE}" == "" ]]; then
  echo "Unable to find plot geometry file (*.json or *.geojson)"
  exit 11
fi

echo "Processing with ${IMAGE_FILE} ${PLOTS_FILE}"
echo "  Options: ${ALGO_OPTIONS}"

# Write the argument JSON file for supported workflows (not all of them)
cat >"/scif/apps/src/jx-args.json" <<EOF
{
"SOILMASK_SOURCE_FILE": "${IMAGE_FILE}",
"SOILMASK_MASK_FILE": "orthomosaicmask.tif",
"SOILMASK_WORKING_FOLDER": "${WORKDIR}",
"SOILMASK_OPTIONS": "",
"SOILMASK_RATIO_SOURCE_FILE": "${IMAGE_FILE}",
"SOILMASK_RATIO_MASK_FILE": "orthomosaicmask.tif",
"SOILMASK_RATIO_WORKING_FOLDER": "${WORKDIR}",
"SOILMASK_RATIO_OPTIONS": "--ratio 1.0",
"PLOTCLIP_SOURCE_FILE": "${WORKDIR}/orthomosaicmask.tif",
"PLOTCLIP_PLOTGEOMETRY_FILE": "${PLOTS_FILE}",
"PLOTCLIP_WORKING_FOLDER": "${WORKDIR}",
"PLOTCLIP_OPTIONS": "",
"FILES2JSON_SEARCH_NAME": "orthomosaicmask.tif",
"FILES2JSON_SEARCH_FOLDER": "${WORKDIR}",
"FILES2JSON_JSON_FILE": "/scif/apps/src/canopy_cover_files.json",
"CANOPYCOVER_OPTIONS": "${OPTIONS}",
"GREENNESS_INDICES_OPTIONS": "${OPTIONS}",
"MERGECSV_SOURCE": "${WORKDIR}",
"MERGECSV_TARGET": "${WORKDIR}",
"MERGECSV_OPTIONS": "",
}
EOF

# Determine what workflow the caller wants to run, and run  that workflow
if [[ "${WORKFLOW_TO_RUN}" == "Canopy Cover with normal soil masking" ]]; then
  WORKFLOW=('soilmask' 'plotclip' 'find_files2json' 'canopycover' 'merge_csv')
elif [[ "${WORKFLOW_TO_RUN}" == "Canopy Cover with ratio soil masking" ]]; then
  WORKFLOW=('soilmask_ratio' 'plotclip' 'find_files2json' 'canopycover' 'merge_csv')
else
  echo "Unknown workflow specified: '${WORKFLOW_TO_RUN}'"
  exit 30
fi

echo "Running workflow steps: ${WORKFLOW[*]}"
for ((IDX = 0; IDX < ${#WORKFLOW[@]}; IDX++)); do
  echo "Running app $IDX '${WORKFLOW[$IDX]}'"
  scif run "${WORKFLOW[$IDX]}"
done

echo "Workflow completed"
