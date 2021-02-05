#!/bin/bash

WORKING_FOLDER=$(pwd)

# Get the Ortho image file
if [[ "${1}" == "" ]]; then
  echo "Orthogonal image to soil-mask is not specified"
  exit 1
fi
ORTHO_IMAGE="${1}"

# Get the mask file name
MASK_FILE="orthoimage_mask.tif"

# Get the ratio if specified
if [[ "${2}" != "" ]]; then
  RATIO_PARAM="${2}"
else
  RATIO_PARAM=""
fi

# Only ratio parameter supported at this time
if [[ "${RATIO_PARAM}" != "" ]]; then
  OPTIONS="${OPTIONS} --ratio ${RATIO_PARAM}"
else
  OPTIONS=""
fi

echo "Masking image file '${WORKING_FOLDER}/${ORTHO_IMAGE}' to file '${MASK_FILE}'"
echo "Ratio threshold value (not specified if using default value): ${RATIO_PARAM}"
echo "{" >"/scif/apps/src/jx-args.json"
{
  echo "\"SOILMASK_RATIO_SOURCE_FILE\": \"${WORKING_FOLDER}/${ORTHO_IMAGE}\","
  echo "\"SOILMASK_RATIO_MASK_FILE\": \"${MASK_FILE}\","
  echo "\"SOILMASK_RATIO_WORKING_FOLDER\": \"${WORKING_FOLDER}\","
  echo "\"SOILMASK_RATIO_OPTIONS\": \"${OPTIONS}\""
  echo "}"
} >>"/scif/apps/src/jx-args.json"

echo "JSON Args file:"
cat "/scif/apps/src/jx-args.json"
scif run soilmask_ratio
