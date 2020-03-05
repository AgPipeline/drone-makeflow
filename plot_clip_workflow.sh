#!/bin/bash

set -e

PC_CACHE_DIR=${CACHE_DIR}
PC_DOCKER_IMAGE="agdrone/transformer-plotclip:${DOCKER_VERSION}"
PC_METADATA="${BASE_DIR}${EXPERIMENT_METADATA_FILENAME}"
PC_SOURCE_IMAGES_DIR="${BASE_DIR}${DATA_FOLDER_NAME}"
PC_WORKSPACE_DIR_NAME="workspace"
PC_WORKSPACE="${BASE_DIR}${RELATIVE_WORKING_FOLDER}${PC_WORKSPACE_DIR_NAME}/"
PC_RESULT_FILENAME="result.json"
PC_RUN_RESULTS="${PC_WORKSPACE}${PC_RESULT_FILENAME}"

CACHE_RESULTS_SCRIPT="${BASE_DIR}${RELATIVE_WORKING_FOLDER}cache_results.py"

DOCKER_MOUNT_POINT="/mnt/"
METADATA="${DOCKER_MOUNT_POINT}${EXPERIMENT_METADATA_FILENAME}"
WORKSPACE_DIR="${DOCKER_MOUNT_POINT}${RELATIVE_WORKING_FOLDER}${PC_WORKSPACE_DIR_NAME}"
DOCKER_RUN_PARAMS="${DOCKER_MOUNT_POINT}${DATA_FOLDER_NAME}/odm_orthophoto.tif"

PATH_MAPS="${DOCKER_MOUNT_POINT}:${BASE_DIR}${RELATIVE_WORKING_FOLDER}"

echo "Cache: $PC_CACHE_DIR"
echo "Docker image: $PC_DOCKER_IMAGE"
echo "Metadata: $PC_METADATA"
echo "Images dir: $PC_SOURCE_IMAGES_DIR"
echo "Workspace name: $PC_WORKSPACE_DIR_NAME"
echo "Local workspace dir: $PC_WORKSPACE"
echo "Results: $PC_RUN_RESULTS"
echo "Results script: $CACHE_RESULTS_SCRIPT"
echo "Docker mount: $DOCKER_MOUNT_POINT"
echo "Metadata: $METADATA"
echo "Docker workspace Dir: $WORKSPACE_DIR"
echo "Docker run params: $DOCKER_RUN_PARAMS"
echo "Path maps: $PATH_MAPS"
echo "Docker mount source: $IMAGE_MOUNT_SOURCE"

echo "Creating workspace folder '${PC_WORKSPACE}'"
mkdir -p ${PC_WORKSPACE} && chmod a+w ${PC_WORKSPACE}

echo docker run --rm --name sm_testing -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${PC_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"
docker run --rm --name sm_testing -v "${IMAGE_MOUNT_SOURCE}:${DOCKER_MOUNT_POINT}" ${PC_DOCKER_IMAGE} -d --metadata "${METADATA}" --working_space "${WORKSPACE_DIR}" "${DOCKER_RUN_PARAMS}"

echo "Creating cache folder: '${PC_CACHE_DIR}'"
mkdir -p ${PC_CACHE_DIR}

echo "Copying results '${PC_RUN_RESULTS}' to '${PC_CACHE_DIR}'"
cp "${PC_RUN_RESULTS}" "${PC_CACHE_DIR}"

echo python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${PC_METADATA}" "${PC_RUN_RESULTS}" "${PC_CACHE_DIR}"
python3 "${CACHE_RESULTS_SCRIPT}" --maps "${PATH_MAPS}" --extra_files "${PC_METADATA}" "${PC_RUN_RESULTS}" "${PC_CACHE_DIR}"
