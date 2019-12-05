#!/bin/bash

$HOME/cctools/bin/makeflow --jx odm_workflow.jx --jx-args env.json $@
$HOME/cctools/bin/makeflow --jx soil_mask_workflow.jx --jx-args env.json $@

