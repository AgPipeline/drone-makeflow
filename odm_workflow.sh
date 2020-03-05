#!/bin/bash

set -e

ODM_CACHE_DIR=${CACHE_DIR}
ODM_DOCKER_IMAGE="agdrone/transformer-opendronemap:${DOCKER_VERSION}"
ODM_METADATA="${BASE_DIR}${EXPERIMENT_METADATA_FILENAME}"
ODM_SOURCE_IMAGES_DIR="${BASE_DIR}${DATA_FOLDER_NAME}"
ODM_WORKSPACE_DIR_NAME="workspace"
ODM_WORKSPACE="${BASE_DIR}${RELATIVE_WORKING_FOLDER}${ODM_WORKSPACE_DIR_NAME}/"
ODM_RESULT_FILENAME="result.json"
ODM_RUN_RESULTS="${ODM_WORKSPACE}${ODM_RESULT_FILENAME}"

CACHE_RESULTS_SCRIPT="${BASE_DIR}${RELATIVE_WORKING_FOLDER}cache_results.py"

DOCKER_MOUNT_POINT="/mnt/"
METADATA="${DOCKER_MOUNT_POINT}${EXPERIMENT_METADATA_FILENAME}"
WORKSPACE_DIR="${DOCKER_MOUNT_POINT}${RELATIVE_WORKING_FOLDER}${ODM_WORKSPACE_DIR_NAME}"
DOCKER_RUN_PARAMS="${DOCKER_MOUNT_POINT}${DATA_FOLDER_NAME}"

PATH_MAPS="${DOCKER_MOUNT_POINT}:${BASE_DIR}${RELATIVE_WORKING_FOLDER}"

echo "Cache: $ODM_CACHE_DIR"
echo "Docker image: $ODM_DOCKER_IMAGE"
echo "Metadata: $ODM_METADATA"
echo "Images dir: $ODM_SOURCE_IMAGES_DIR"
echo "Workspace name: $ODM_WORKSPACE_DIR_NAME"
echo "Local workspace dir: $ODM_WORKSPACE"
echo "Results: $ODM_RUN_RESULTS"
echo "Results script: $CACHE_RESULTS_SCRIPT"
echo "Docker mount: $DOCKER_MOUNT_POINT"
echo "Metadata: $METADATA"
echo "Docker workspace Dir: $WORKSPACE_DIR"
echo "Docker run params: $DOCKER_RUN_PARAMS"
echo "Path maps: $PATH_MAPS"
echo "Docker mount source: $IMAGE_MOUNT_SOURCE"

echo "Creating workspace folder '${ODM_WORKSPACE}'"
mkdir -p ${ODM_WORKSPACE} && chmod a+w ${ODM_WORKSPACE}

echo docker run --rm --name odm_transformer -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${ODM_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"
docker run --rm --name odm_transformer -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${ODM_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"

echo "Creating cache folder: '${ODM_CACHE_DIR}'"
mkdir -p ${ODM_CACHE_DIR}

echo "Copying results '${ODM_RUN_RESULTS}' to '${ODM_CACHE_DIR}'"
cp "${ODM_RUN_RESULTS}" "${ODM_CACHE_DIR}"

echo python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${ODM_METADATA}" "${ODM_RUN_RESULTS}" "${ODM_CACHE_DIR}"
python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${ODM_METADATA}" "${ODM_RUN_RESULTS}" "${ODM_CACHE_DIR}"
