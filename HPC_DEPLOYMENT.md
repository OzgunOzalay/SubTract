# SubTract Pipeline HPC Deployment Guide

This guide shows how to build and deploy the SubTract pipeline on HPC systems using Docker and Singularity.

## Building the Docker Image

### 1. Build the Docker Image

```bash
# Build the Docker image (this will take 30-60 minutes)
docker build -t subtract-pipeline:latest .

# Optional: Tag with version
docker tag subtract-pipeline:latest subtract-pipeline:1.0.0-alpha
```

### 2. Test the Docker Image Locally

```bash
# Create a test configuration
cp hpc_config_template.yaml my_config.yaml

# Edit the configuration to point to your local data
# Make sure paths in the config match your mounted volumes

# Test run with local data
docker run -it --rm \
  -v /path/to/your/bids/data:/data \
  subtract-pipeline:latest /data/my_config.yaml
```

## Converting to Singularity for HPC

### 1. Convert Docker Image to Singularity

```bash
# Method 1: Direct conversion from Docker Hub (if you pushed the image)
singularity build subtract-pipeline.sif docker://your-registry/subtract-pipeline:latest

# Method 2: Convert from local Docker image
singularity build subtract-pipeline.sif docker-daemon://subtract-pipeline:latest

# Method 3: Build directly from Dockerfile (if Singularity 3.0+)
singularity build subtract-pipeline.sif Dockerfile
```

### 2. Transfer to HPC System

```bash
# Copy the Singularity image to your HPC system
scp subtract-pipeline.sif username@hpc-cluster:/path/to/your/singularity/images/
```

## HPC Usage

### 1. Prepare Your Configuration

Create a configuration file on your HPC system:

```yaml
# Copy the template and modify for your data
cp hpc_config_template.yaml my_hpc_config.yaml
```

Edit the configuration to match your HPC setup:
- Adjust `n_threads` based on your node allocation
- Set `eddy_cuda: true` if you have GPU nodes available
- Modify paths to match your HPC storage structure

### 2. Prepare Your Data Structure

Your HPC data should be organized like this:

```
/your/hpc/data/
├── bids/                          # Your BIDS dataset
│   ├── dataset_description.json
│   ├── participants.tsv
│   └── sub-*/
└── derivatives/                   # Will be created by pipeline
    └── subtract/
        ├── results/
        └── sub-*/
```

### 3. SLURM Job Script Example

Create a SLURM job script (`subtract_job.slurm`):

```bash
#!/bin/bash
#SBATCH --job-name=subtract-pipeline
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64GB
#SBATCH --time=24:00:00
#SBATCH --partition=compute
#SBATCH --output=subtract_%j.out
#SBATCH --error=subtract_%j.err

# Load Singularity module
module load singularity

# Set up paths
DATA_DIR="/path/to/your/hpc/data"
CONFIG_FILE="$DATA_DIR/my_hpc_config.yaml"
SINGULARITY_IMAGE="/path/to/subtract-pipeline.sif"

# Run the pipeline
singularity run \
  --bind ${DATA_DIR}:/data \
  --cleanenv \
  ${SINGULARITY_IMAGE} \
  /data/my_hpc_config.yaml
```

### 4. Submit the Job

```bash
# Submit the job
sbatch subtract_job.slurm

# Monitor the job
squeue -u $USER
```

### 5. Advanced HPC Usage

#### A. Array Jobs for Multiple Subjects

For processing multiple subjects in parallel:

```bash
#!/bin/bash
#SBATCH --job-name=subtract-array
#SBATCH --array=1-10                # Adjust based on number of subjects
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32GB
#SBATCH --time=12:00:00

# Get subject list
SUBJECTS=($(ls /path/to/bids/sub-*/))
SUBJECT=${SUBJECTS[$SLURM_ARRAY_TASK_ID-1]}

# Create subject-specific config
CONFIG_FILE="/tmp/config_${SLURM_ARRAY_TASK_ID}.yaml"
sed "s/subject_filter: null/subject_filter: \"^${SUBJECT}$\"/" my_hpc_config.yaml > $CONFIG_FILE

# Run pipeline for this subject
singularity run \
  --bind /path/to/data:/data \
  --cleanenv \
  subtract-pipeline.sif \
  $CONFIG_FILE
```

#### B. GPU-Enabled Processing

For nodes with GPU support:

```bash
#!/bin/bash
#SBATCH --job-name=subtract-gpu
#SBATCH --gres=gpu:1
#SBATCH --partition=gpu

# Enable CUDA in config by setting eddy_cuda: true
# The pipeline will automatically use GPU acceleration when available
```

## Configuration Customization

### Key Parameters to Adjust for HPC:

1. **Processing Threads**: Match your node allocation
   ```yaml
   processing:
     n_threads: 16  # Match --cpus-per-task
   ```

2. **Memory-Intensive Steps**: Adjust for large datasets
   ```yaml
   processing:
     n_tracks: 1000000  # Reduce if memory limited
   ```

3. **GPU Acceleration**: Enable if available
   ```yaml
   processing:
     eddy_cuda: true
     eddy_method: "eddy_cuda10.2"
   ```

4. **Subject Selection**: Process specific subjects
   ```yaml
   subject_filter: "^(sub-001|sub-002)$"
   ```

5. **Step Selection**: Run only specific steps
   ```yaml
   steps_to_run:
     - "denoise"
     - "topup" 
     - "eddy"
     # Comment out steps you don't need
   ```

## Monitoring and Troubleshooting

### 1. Monitor Progress

```bash
# Check job status
squeue -u $USER

# View output logs
tail -f subtract_${JOBID}.out

# Check resource usage
sstat -j $JOBID
```

### 2. Common Issues

#### Memory Issues
- Reduce `n_tracks` parameter
- Request more memory in SLURM script
- Process subjects individually

#### Time Limits
- Full pipeline typically takes 8-24 hours per subject
- Consider running steps separately
- Use array jobs for multiple subjects

#### Storage Issues
- Ensure sufficient scratch space
- Consider using node-local storage for temporary files
- Clean up intermediate files if needed

### 3. Debugging

```bash
# Interactive session for debugging
srun --pty bash

# Test singularity image interactively
singularity shell --bind /data:/data subtract-pipeline.sif

# Check tool availability inside container
singularity exec subtract-pipeline.sif which mrconvert
singularity exec subtract-pipeline.sif which antsRegistration
```

## Output Structure

The pipeline will create outputs in your mounted data directory:

```
/your/hpc/data/derivatives/subtract/
├── results/
│   ├── connectivity_matrices/
│   ├── qc_reports/
│   └── summary_statistics/
└── sub-*/
    ├── dwi/
    │   ├── Eddy/
    │   ├── mrtrix3/
    │   └── mdt/
    └── logs/
```

## Performance Tips

1. **Use fast storage**: Store data on high-performance filesystems (not NFS)
2. **Optimize I/O**: Use node-local storage for temporary files
3. **Resource allocation**: Match CPU/memory requests to actual needs
4. **Parallel processing**: Use array jobs for multiple subjects
5. **Monitor usage**: Check actual resource utilization and adjust

## Support

For issues specific to:
- **HPC setup**: Contact your HPC support team
- **Singularity**: Check Singularity documentation
- **Pipeline errors**: Check the SubTract logs and documentation 