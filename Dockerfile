# SubTract Pipeline Docker Image
# Optimized for HPC/Singularity deployment

# Use pre-built FSL image as base for much faster build
FROM brainlife/fsl:6.0.4

# Prevent interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Set working directory
WORKDIR /opt/subtract

# Install additional system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    unzip \
    build-essential \
    cmake \
    python3 \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda && \
    rm /tmp/miniconda.sh
ENV PATH="/opt/miniconda/bin:$PATH"

# Initialize conda
RUN conda init bash

# FSL is already installed in the base image, just ensure environment variables are set
ENV FSLDIR="/usr/local/fsl"
ENV FSLOUTPUTTYPE="NIFTI_GZ"
ENV FSLMULTIFILEQUIT="TRUE"

# Create the three separate conda environments as expected by the pipeline

# 1. Create 'subtract' environment with MRtrix3 and Python tools
RUN conda create -n subtract python=3.9 -y && \
    conda install -n subtract -c mrtrix3 mrtrix3 -y

# 2. Create 'ants' environment with ANTs tools
RUN conda create -n ants python=3.9 -y && \
    conda install -n ants -c conda-forge ants -y

# 3. Create 'mdt' environment with MDT tools  
RUN conda create -n mdt python=3.8 -y && \
    conda run -n mdt pip install mdt

# Set default environment to subtract but keep FSL in PATH  
ENV PATH="/opt/miniconda/envs/subtract/bin:/usr/local/fsl/bin:$PATH"
ENV FSLMULTIFILEQUIT="TRUE"
ENV FSLTCLSH="${FSLDIR}/bin/fsltclsh"
ENV FSLWISH="${FSLDIR}/bin/fslwish"

# Copy application files
COPY . /opt/subtract/

# Install Python dependencies and the SubTract package
RUN conda run -n subtract pip install --no-cache-dir -r requirements.txt && \
    conda run -n subtract pip install -e .

# Create a simple entrypoint script
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Initialize conda\n\
source /opt/miniconda/bin/activate\n\
\n\
# Check if config file is provided\n\
if [ $# -eq 0 ]; then\n\
    echo "Usage: docker run <image> <config.yaml>"\n\
    echo "Example: docker run subtract-pipeline /data/config.yaml"\n\
    exit 1\n\
fi\n\
\n\
CONFIG_FILE="$1"\n\
\n\
if [ ! -f "$CONFIG_FILE" ]; then\n\
    echo "Error: Configuration file $CONFIG_FILE not found"\n\
    exit 1\n\
fi\n\
\n\
echo "Running SubTract pipeline with configuration: $CONFIG_FILE"\n\
echo "Available conda environments:"\n\
conda env list\n\
echo ""\n\
echo "Tool availability:"\n\
echo "  FSL: $(which fsl 2>/dev/null || echo \"not found\") - Version: $(cat $FSLDIR/etc/fslversion 2>/dev/null || echo \"unknown\")"\n\
echo "  MRtrix3 (subtract env): $(conda run -n subtract which mrconvert 2>/dev/null || echo \"not found\")"\n\
echo "  ANTs (ants env): $(conda run -n ants which antsRegistration 2>/dev/null || echo \"not found\")"\n\
echo "  MDT (mdt env): $(conda run -n mdt python -c \"import mdt; print(mdt.__version__)\" 2>/dev/null || echo \"not found\")"\n\
echo "  SubTract: $(conda run -n subtract which subtract 2>/dev/null || echo \"not found\")"\n\
echo ""\n\
\n\
# Activate subtract environment and run the pipeline\n\
conda activate subtract\n\
subtract run-config "$CONFIG_FILE"\n\
' > /opt/subtract/entrypoint.sh && \
    chmod +x /opt/subtract/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/opt/subtract/entrypoint.sh"]

# Add labels for metadata
LABEL maintainer="SubTract Development Team"
LABEL description="SubTract: Microstructure-informed tractography pipeline"
LABEL version="1.0.0-alpha" 