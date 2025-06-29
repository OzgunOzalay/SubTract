#!/bin/bash
set -e

# Initialize conda for both Docker and Singularity environments
if [ -f "/opt/miniconda/etc/profile.d/conda.sh" ]; then
    # Source conda profile (works for Singularity)
    source /opt/miniconda/etc/profile.d/conda.sh
elif [ -f "/opt/miniconda/bin/conda" ]; then
    # Use conda hook (works for Docker)
    eval "$(/opt/miniconda/bin/conda shell.bash hook)"
else
    echo "Error: Conda not found in expected locations"
    exit 1
fi

# Ensure conda is properly initialized
if ! command -v conda &> /dev/null; then
    echo "Error: Conda not properly initialized"
    exit 1
fi

# Check if we want to run an interactive shell
if [ "$1" = "bash" ] || [ "$1" = "sh" ]; then
    exec "$@"
fi

# Check if arguments are provided
if [ $# -eq 0 ]; then
    echo "Usage: docker run <image> <command> [args...]"
    echo "Examples:"
    echo "  docker run subtract-pipeline run-config /data/config.yaml"
    echo "  docker run subtract-pipeline run /data/bids --steps tractography"
    echo "  docker run -it <image> bash"
    echo ""
    echo "Available conda environments:"
    conda env list
    exit 1
fi

COMMAND="$1"
shift

echo "Running SubTract command: $COMMAND"
echo "Available conda environments:"
conda env list
echo ""
echo "Tool availability:"
echo "  FSL: $(which fsl 2>/dev/null || echo "not found") - Version: $(cat $FSLDIR/etc/fslversion 2>/dev/null || echo "unknown")"
echo "  MRtrix3 (system): $(which dwidenoise 2>/dev/null || echo "not found")"
echo "  ANTs (ants env): $(conda run -n ants which antsRegistration 2>/dev/null || echo "not found")"
echo "  SubTract: $(conda run -n subtract which subtract 2>/dev/null || echo "not found")"
echo ""

# Determine which environment to use based on command
# Most SubTract commands run in the subtract environment
ENVIRONMENT="subtract"

# Run the pipeline using conda run to ensure proper environment activation
# But ensure system MRtrix3 is available in the environment
echo "Using conda environment: $ENVIRONMENT"
export PATH="/opt/mrtrix3-3.0.4/bin:/opt/fsl-6.0.7.1/bin:$PATH"
export LD_LIBRARY_PATH="/opt/mrtrix3-3.0.4/lib:$LD_LIBRARY_PATH"
conda run -n $ENVIRONMENT subtract "$COMMAND" "$@" 