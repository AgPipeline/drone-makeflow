#!/bin/bash

# See what the caller wants
case $1 in
  "workflow" )
    echo "Running the workflow."
    ./run_workflow.sh
    ;;
  "clean" )
    echo "Cleaning up previous workflow (deletes all artifacts)."
    ./run_workflow.sh -c
    ;;
  * )
    echo "Supported docker parameters:"
    echo "  \"workflow\": runs the workflow."
    echo "  \"clean\": cleans up after a workflow run by deleting all artifacts."
    echo "  -h: display help"
    ./run_workflow.sh -h
    exit 0
    ;;
esac;