#!/bin/bash
set -e

# Initialize conda
eval "$(/opt/miniconda/bin/conda shell.bash hook)"

# Check if we want to run an interactive shell
if [ "$1" = "bash" ] || [ "$1" = "sh" ]; then
    exec "$@"
fi

# Check if config file is provided
if [ $# -eq 0 ]; then
    echo "Usage: docker run <image> <config.yaml>"
    echo "Example: docker run subtract-pipeline /data/config.yaml"
    echo "For interactive shell: docker run -it <image> bash"
    exit 1
fi

CONFIG_FILE="$1"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found"
    exit 1
fi

echo "Running SubTract pipeline with configuration: $CONFIG_FILE"
echo "Available conda environments:"
/opt/miniconda/bin/conda env list
echo ""
echo "Tool availability:"
echo "  FSL: $(which fsl 2>/dev/null || echo "not found") - Version: $(cat $FSLDIR/etc/fslversion 2>/dev/null || echo "unknown")"
echo "  MRtrix3 (subtract env): /opt/miniconda/envs/subtract/bin/mrconvert, /opt/miniconda/envs/subtract/bin/mrdegibbs"
echo "  ANTs (ants env): /opt/miniconda/envs/ants/bin/antsRegistration"
echo "  MDT (mdt env): $(/opt/miniconda/bin/conda run -n mdt python -c 'import mdt; print(mdt.__version__)' 2>/dev/null || echo "not found")"
echo "  SubTract: $(/opt/miniconda/bin/conda run -n subtract which subtract 2>/dev/null || echo "not found")"
echo ""

# Run the pipeline using conda run to ensure proper environment activation
/opt/miniconda/bin/conda run -n subtract subtract run-config "$CONFIG_FILE" 