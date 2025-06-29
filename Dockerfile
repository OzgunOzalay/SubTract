# SubTract Pipeline Docker Image
# Built upon Neurodocker base with FSL and MRtrix3 pre-installed

# Use the pre-built Neurodocker base image with FSL and MRtrix3
FROM ozgunozalay/subtract-base:latest

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
    software-properties-common \
    libarchive-dev \
    libhdf5-dev \
    libnetcdf-dev \
    libfftw3-dev \
    libeigen3-dev \
    libboost-all-dev \
    libgsl-dev \
    liblapack-dev \
    libblas-dev \
    libopenblas-dev \
    libatlas-base-dev \
    libopenmpi-dev \
    openmpi-bin \
    && rm -rf /var/lib/apt/lists/*

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
    bash /tmp/miniconda.sh -b -p /opt/miniconda && \
    rm /tmp/miniconda.sh
ENV PATH="/opt/miniconda/bin:$PATH"

# Unset any inherited conda environment variables
ENV CONDA_PREFIX=""
ENV CONDA_EXE=""
ENV _CONDA_ROOT=""
ENV _CONDA_EXE=""

# Initialize conda
RUN /opt/miniconda/bin/conda init bash

# Configure conda for more robust package installation
RUN /opt/miniconda/bin/conda config --set channel_priority flexible && \
    /opt/miniconda/bin/conda config --set auto_update_conda false && \
    /opt/miniconda/bin/conda clean --all --yes

# Create conda environments (without MRtrix3 to avoid conflicts)
RUN /opt/miniconda/bin/conda create -n subtract -y && \
    /opt/miniconda/bin/conda create -n ants -y && \
    /opt/miniconda/bin/conda install -n ants -c conda-forge ants -y --no-deps && \
    /opt/miniconda/bin/conda create -n mdt python=3.10 && \
    /opt/miniconda/bin/conda clean --all --yes

# Set default environment to subtract but prioritize system FSL and MRtrix3 in PATH  
ENV PATH="/opt/mrtrix3-3.0.4/bin:/opt/fsl-6.0.7.1/bin:/opt/miniconda/envs/subtract/bin:$PATH"
ENV LD_LIBRARY_PATH="/opt/mrtrix3-3.0.4/lib:$LD_LIBRARY_PATH"

# Copy application files and install Python dependencies
COPY . /opt/subtract/
RUN /opt/miniconda/bin/conda run -n subtract pip install --no-cache-dir -r requirements.txt && \
    /opt/miniconda/bin/conda run -n subtract pip install -e .

# Copy and set up entrypoint script
COPY entrypoint.sh /opt/subtract/entrypoint.sh
RUN chmod +x /opt/subtract/entrypoint.sh && \
    ls -la /opt/subtract/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/opt/subtract/entrypoint.sh"]

# Add labels for metadata
LABEL maintainer="SubTract Development Team"
LABEL description="SubTract: Microstructure-informed tractography pipeline"
LABEL version="1.0.0-alpha" 