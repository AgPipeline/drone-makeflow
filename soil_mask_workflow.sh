#!/bin/bash

set -e

SM_CACHE_DIR=${CACHE_DIR}
SM_DOCKER_IMAGE="agdrone/transformer-soilmask:${DOCKER_VERSION}"
SM_METADATA="${BASE_DIR}${EXPERIMENT_METADATA_FILENAME}"
SM_SOURCE_IMAGES_DIR="${BASE_DIR}${DATA_FOLDER_NAME}"
SM_WORKSPACE_DIR_NAME="workspace"
SM_WORKSPACE="${BASE_DIR}${RELATIVE_WORKING_FOLDER}${SM_WORKSPACE_DIR_NAME}/"
SM_RESULT_FILENAME="result.json"
SM_RUN_RESULTS="${SM_WORKSPACE}${SM_RESULT_FILENAME}"

CACHE_RESULTS_SCRIPT="${BASE_DIR}${RELATIVE_WORKING_FOLDER}cache_results.py"

DOCKER_MOUNT_POINT="/mnt/"
METADATA="${DOCKER_MOUNT_POINT}${EXPERIMENT_METADATA_FILENAME}"
WORKSPACE_DIR="${DOCKER_MOUNT_POINT}${RELATIVE_WORKING_FOLDER}${SM_WORKSPACE_DIR_NAME}"
DOCKER_RUN_PARAMS="${DOCKER_MOUNT_POINT}${DATA_FOLDER_NAME}/odm_orthophoto.tif"

PATH_MAPS="${DOCKER_MOUNT_POINT}:${BASE_DIR}${RELATIVE_WORKING_FOLDER}"

echo "Cache: $SM_CACHE_DIR"
echo "Docker image: $SM_DOCKER_IMAGE"
echo "Metadata: $SM_METADATA"
echo "Images dir: $SM_SOURCE_IMAGES_DIR"
echo "Workspace name: $SM_WORKSPACE_DIR_NAME"
echo "Local workspace dir: $SM_WORKSPACE"
echo "Results: $SM_RUN_RESULTS"
echo "Results script: $CACHE_RESULTS_SCRIPT"
echo "Docker mount: $DOCKER_MOUNT_POINT"
echo "Metadata: $METADATA"
echo "Docker workspace Dir: $WORKSPACE_DIR"
echo "Docker run params: $DOCKER_RUN_PARAMS"
echo "Path maps: $PATH_MAPS"
echo "Docker mount source: $IMAGE_MOUNT_SOURCE"

echo "Creating workspace folder '${SM_WORKSPACE}'"
mkdir -p ${SM_WORKSPACE} && chmod a+w ${SM_WORKSPACE}

echo docker run --rm --name sm_testing -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${SM_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"
docker run --rm --name sm_testing -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${SM_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"

echo "Creating cache folder: '${SM_CACHE_DIR}'"
mkdir -p ${SM_CACHE_DIR}

echo "Copying results '${SM_RUN_RESULTS}' to '${SM_CACHE_DIR}'"
cp "${SM_RUN_RESULTS}" "${SM_CACHE_DIR}"

echo python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${SM_METADATA}" "${SM_RUN_RESULTS}" "${SM_CACHE_DIR}"
python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${SM_METADATA}" "${SM_RUN_RESULTS}" "${SM_CACHE_DIR}"
