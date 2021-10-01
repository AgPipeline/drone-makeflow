#!/bin/bash

# Initialize variables
IMAGE_FILE=
PLOTS_FILE=
ALGO_OPTIONS=""

echo "INPUT FOLDER ${INPUT}"
echo "WORKING FOLDER ${WORKDIR}"

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
if [[ "{$IMAGE_FILE}" == "" ]]; then
  echo "Unable to find source image file (*.tif or *.tiff)"
  exit 10
fi
if [[ "${PLOTS_FILE}" == "" ]]; then
  echo "Unable to find plot geometry file (*.json or *.geojson)"
  exit 11
fi

# Write the argument JSON file for supported workflows (not all of them)
echo "{" >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_SOURCE_FILE\": \"/${INPUT}/${IMAGE_FILE}\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_MASK_FILE\": \"orthomosaicmask.tif\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_WORKING_FOLDER\": \"/${WORKDIR}\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_OPTIONS\": \"\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_RATIO_SOURCE_FILE\": \"/${INPUT}/${IMAGE_FILE}\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_RATIO_MASK_FILE\": \"orthomosaicmask.tif\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_RATIO_WORKING_FOLDER\": \"/${WORKDIR}\"," >"/scif/apps/src/jx-args.json"
echo "\"SOILMASK_RATIO_OPTIONS\": \"--ratio 1.0\"," >"/scif/apps/src/jx-args.json"
echo "\"PLOTCLIP_SOURCE_FILE\": \"/${WORKDIR}/orthomosaicmask.tif\"," >"/scif/apps/src/jx-args.json"
echo "\"PLOTCLIP_PLOTGEOMETRY_FILE\": \"/${WORKDIR}/plots.geojson\"," >"/scif/apps/src/jx-args.json"
echo "\"PLOTCLIP_WORKING_FOLDER\": \"/${WORKDIR}\"," >"/scif/apps/src/jx-args.json"
echo "\"PLOTCLIP_OPTIONS\": \"\"," >"/scif/apps/src/jx-args.json"
echo "\"FILES2JSON_SEARCH_NAME\": \"orthomosaicmask.tif\"," >"/scif/apps/src/jx-args.json"
echo "\"FILES2JSON_SEARCH_FOLDER\": \"/${WORKDIR}\"," >"/scif/apps/src/jx-args.json"
echo "\"FILES2JSON_JSON_FILE\": \"/${WORKDIR}/canopy_cover_files.json\"," >"/scif/apps/src/jx-args.json"
echo "\"CANOPYCOVER_OPTIONS\": \"${OPTIONS}\"," >"/scif/apps/src/jx-args.json"
echo "\"GREENNESS_INDICES_OPTIONS\": \"${OPTIONS}\"," >"/scif/apps/src/jx-args.json"
echo "\"MERGECSV_SOURCE\": \"/${INPUT}\"," >"/scif/apps/src/jx-args.json"
echo "\"MERGECSV_TARGET\": \"/${WORKDIR}\"," >"/scif/apps/src/jx-args.json"
echo "\"MERGECSV_OPTIONS\": \"\"," >"/scif/apps/src/jx-args.json"
echo "}" >"/scif/apps/src/jx-args.json"

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
for (( IDX=0; IDX < ${#WORKFLOW[@]}; IDX++ )); do
  echo "Running app $IDX '${WORKFLOW[$IDX]}'"
done
