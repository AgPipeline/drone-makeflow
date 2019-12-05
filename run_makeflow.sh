#!/bin/bash

$HOME/cctools/bin/makeflow --jx odm_workflow.jx --jx-args env.json $@
$HOME/cctools/bin/makeflow --jx soil_mask_workflow.jx --jx-args env.json $@
$HOME/cctools/bin/makeflow --jx plot_clip_workflow.jx --jx-args env.json --jx-define "MF_BETYDB_URL"="`echo "\"\\\"\"${BETYDB_URL}\\\"\"\""`" --jx-define "MF_BETYDB_KEY"="`echo "\"\\\"\"${BETYDB_KEY}\\\"\"\""`" $@

