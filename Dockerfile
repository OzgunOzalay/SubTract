# SubTract Pipeline Docker Image
# Optimized for HPC/Singularity deployment

# Use custom FSL 6.0.7 image as base
FROM ozgunozalay/fsl:6

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
    ocl-icd-opencl-dev \
    opencl-headers \
    clinfo \
    libarchive-dev \
    && rm -rf /var/lib/apt/lists/*

# Remove any conda/miniconda from the FSL base image to avoid conflicts
RUN rm -rf /opt/fsl-6.0.7.1/miniconda /opt/fsl-6.0.7.1/conda /usr/local/fsl/miniconda /usr/local/fsl/conda || true

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

# FSL is already installed in the base image, just ensure environment variables are set
ENV FSLDIR="/opt/fsl-6.0.7.1"
ENV FSLOUTPUTTYPE="NIFTI_GZ"
ENV FSLMULTIFILEQUIT="TRUE"

# FreeSurfer environment will be set dynamically in entrypoint.sh

# Create the three separate conda environments as expected by the pipeline

# 1. Create 'subtract' environment with MRtrix3 and Python tools
RUN /opt/miniconda/bin/conda create -n subtract -y && \
    /opt/miniconda/bin/conda install -n subtract -c mrtrix3 mrtrix3 -y

# 2. Create 'ants' environment with ANTs tools
RUN /opt/miniconda/bin/conda create -n ants -y && \
    /opt/miniconda/bin/conda install -n ants -c conda-forge ants -y

# 3. Create 'mdt' environment with MDT tools  
RUN /opt/miniconda/bin/conda create -n mdt python=3.10 -y && \
    /opt/miniconda/bin/conda install -n mdt -c conda-forge nibabel=4.0.2 numpy=1.23.5 pyopencl ocl-icd-system -y && \
    /opt/miniconda/bin/conda run -n mdt pip install tatsu mdt

# Set default environment to subtract but keep FSL in PATH  
ENV PATH="/opt/miniconda/envs/subtract/bin:/opt/fsl-6.0.7.1/bin:$PATH"
ENV FSLMULTIFILEQUIT="TRUE"
ENV FSLTCLSH="${FSLDIR}/bin/fsltclsh"
ENV FSLWISH="${FSLDIR}/bin/fslwish"

# Copy application files
COPY . /opt/subtract/

# Install Python dependencies and the SubTract package
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