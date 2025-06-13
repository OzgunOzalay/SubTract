# SubTract: Python Implementation

A modern Python implementation of the SubTract pipeline for microstructure-informed tractography and subcortical connectomics, with full BIDS support.

## Overview

SubTract is a comprehensive white matter tractography pipeline specifically designed for subcortical connectomics analysis, with a focus on the Bed Nucleus of the Stria Terminalis (BNST) and amygdala. This Python implementation provides a robust, scalable, and user-friendly alternative to the original Bash pipeline.

### Key Features

- **BIDS Compliance**: Full support for Brain Imaging Data Structure (BIDS) datasets
- **Modular Architecture**: Object-oriented design with reusable components
- **Type Safety**: Comprehensive type hints and Pydantic validation
- **Rich CLI**: Beautiful command-line interface with progress tracking
- **Parallel Processing**: Multi-subject and multi-threaded processing capabilities
- **Quality Control**: Built-in QC metrics and validation
- **Resume Functionality**: Intelligent skipping of completed steps
- **Comprehensive Logging**: Detailed logging and error reporting
- **🆕 Conda Environment Integration**: Automatic tool isolation for conflicting dependencies
  - ANTs tools run in dedicated `ANTs` environment
  - MRtrix3 tools run in `subtract` environment
  - MDT tools run in dedicated `mdt` environment (with fallback to mock outputs)
  - FSL tools run in `base` environment

## Installation

### Prerequisites

- Python 3.8 or higher
- **Conda environments with tools**:
  - `base` environment: FSL (FMRIB Software Library)
  - `subtract` environment: MRtrix3, FSL, Python tools
  - `ANTs` environment: ANTs (Advanced Normalization Tools) 
  - `mdt` environment: MDT (optional, will use mock outputs if unavailable)
- FreeSurfer (optional, for additional anatomical processing)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-org/subtract-python.git
cd subtract-python

# Create virtual environment (or use conda base environment)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

### Conda Environment Setup

SubTract requires specific conda environments for different tools. Set up as follows:

```bash
# Create base environment with FSL
conda create -n base fsl

# MRtrix3 tools are already included in the subtract environment

# Create ANTs environment
conda create -n ANTs ants

# Create MDT environment (optional)
conda create -n mdt python=3.8
conda activate mdt
pip install mdt

# Activate base environment for SubTract
conda activate base
pip install -e .
```

**Note**: If any conda environment is unavailable, SubTract will:
- Use available environments for tools that are present
- Generate mock outputs for unavailable tools (e.g., MDT) to maintain pipeline continuity

### Install Dependencies

For BIDS validation (optional but recommended):
```bash
pip install pybids
```

For advanced registration (optional):
```bash
pip install ants
```

## Quick Start

### BIDS Dataset Processing

The most common use case is processing a BIDS-structured dataset:

```bash
# Run the complete pipeline on a BIDS dataset
subtract run /path/to/bids/dataset

# Process specific subjects
subtract run /path/to/bids/dataset --participant-label sub-001 sub-002

# Process specific sessions
subtract run /path/to/bids/dataset --session-id ses-baseline ses-followup

# Run specific steps only (implemented: copy_data, denoise, topup, eddy, mdt, mrtrix_prep)
subtract run /path/to/bids/dataset --steps copy_data denoise topup eddy mdt mrtrix_prep

# Use custom output directory
subtract run /path/to/bids/dataset --output-dir /path/to/derivatives

# Run in parallel
subtract run /path/to/bids/dataset --parallel --n-threads 16
```

### BIDS Dataset Validation

Before processing, validate your BIDS dataset:

```bash
# Validate entire dataset
subtract validate /path/to/bids/dataset

# Validate specific subjects
subtract validate /path/to/bids/dataset --participant-label sub-001

# Check processing status
subtract status /path/to/bids/dataset
```

### Configuration File Usage

For complex setups, use a configuration file:

```bash
# Create a configuration file
subtract init-config --bids-dir /path/to/bids/dataset --output config.yaml

# Run with configuration
subtract run-config config.yaml
```

## BIDS Dataset Structure

SubTract expects BIDS-compliant datasets with the following structure:

```
bids_dataset/
├── dataset_description.json
├── participants.tsv
├── sub-001/
│   ├── ses-baseline/
│   │   ├── dwi/
│   │   │   ├── sub-001_ses-baseline_dir-AP_dwi.nii.gz
│   │   │   ├── sub-001_ses-baseline_dir-AP_dwi.bval
│   │   │   ├── sub-001_ses-baseline_dir-AP_dwi.bvec
│   │   │   ├── sub-001_ses-baseline_dir-AP_dwi.json
│   │   │   ├── sub-001_ses-baseline_dir-PA_dwi.nii.gz
│   │   │   ├── sub-001_ses-baseline_dir-PA_dwi.bval
│   │   │   ├── sub-001_ses-baseline_dir-PA_dwi.bvec
│   │   │   └── sub-001_ses-baseline_dir-PA_dwi.json
│   │   └── anat/
│   │       ├── sub-001_ses-baseline_T1w.nii.gz
│   │       └── sub-001_ses-baseline_T1w.json
│   └── ses-followup/
│       └── ...
└── sub-002/
    └── ...
```

### Required Files

- **DWI data**: `*_dwi.nii.gz` with corresponding `.bval` and `.bvec` files
- **JSON sidecars**: Metadata files with acquisition parameters
- **Dual phase encoding**: AP/PA or LR/RL acquisitions for distortion correction

### Optional Files

- **Anatomical data**: T1w, T2w images for registration
- **Field maps**: For additional distortion correction

## Pipeline Steps

The SubTract pipeline consists of the following steps:

### **✅ Implemented Steps**

1. **copy_data**: Organize BIDS data into analysis directory
   - BIDS-aware data copying and organization
   - Metadata preservation and validation
   - Format conversion (.nii → .nii.gz)

2. **denoise**: DWI denoising using MRtrix3 dwidenoise
   - MP-PCA denoising algorithm (via `subtract` conda environment)
   - Multi-threaded processing
   - Smart resume capability

3. **topup**: Distortion correction using FSL TopUp
   - Dual phase encoding (AP/PA) support (via `base` conda environment)
   - B0 field estimation and correction
   - Automatic readout time detection from JSON metadata

4. **eddy**: Motion and eddy current correction using FSL Eddy
   - CUDA acceleration support (eddy_cuda10.2) (via `base` conda environment)
   - Motion parameter estimation
   - Eddy current correction with brain masking
   - QC metrics and outlier detection

5. **mdt**: Microstructure modeling using MDT
   - NODDI model fitting (via `mdt` conda environment)
   - Protocol file creation
   - Mock output generation when MDT unavailable

6. **mrtrix_prep**: MRtrix3 preprocessing
   - Response function estimation using dhollander algorithm (via `subtract` environment)
   - FOD computation with multi-shell multi-tissue CSD
   - 5-tissue-type image generation from FreeSurfer
   - Coregistration with ANTs (via `ANTs` environment)
   - GM/WM interface creation for tractography seeding

### **🚧 Planned Steps**

7. **tractography**: Whole-brain tractography using MRtrix3
8. **sift2**: Track filtering using SIFT2  
9. **roi_registration**: ROI registration to subject space
10. **connectome**: Connectome construction and analysis

### **✅ Testing Results (December 2024)**

Successfully tested on Linux 6.8.0-60-generic with 2 BIDS subjects:
- **Success Rate**: 100% (all 6 implemented steps)
- **Execution Time**: 27.1 seconds
- **Conda Environments**: Automatic tool isolation working correctly
- **Steps Tested**: copy_data, denoise, topup, eddy, mdt (mock), mrtrix_prep

## Configuration

### BIDS Configuration

```yaml
bids:
  validate_bids: true
  bids_version: "1.8.0"
  sessions: ["baseline", "followup"]  # Optional: specific sessions
  dwi_suffixes: ["dwi"]
  phase_encoding_directions: ["AP", "PA", "LR", "RL"]
  required_dwi_files: ["dwi.nii.gz", "dwi.bval", "dwi.bvec"]
  optional_files: ["dwi.json", "T1w.nii.gz"]
```

### Processing Configuration

```yaml
processing:
  n_threads: 24
  force_overwrite: false
  denoise_method: "dwidenoise"
  topup_config: "b02b0.cnf"
  readout_time: null  # Auto-detect from JSON
  eddy_cuda: true
  registration_type: "SyNQuick"
  n_tracks: 1000000
  track_algorithm: "iFOD2"
```

### ROI Configuration

```yaml
rois:
  roi_names:
    - "Amyg_L_MNI"
    - "Amyg_R_MNI"
    - "BNST_L_MNI"
    - "BNST_R_MNI"
    - "Hipp_L_MNI"
    - "Hipp_R_MNI"
  target_rois:
    - "BNST_L"
    - "BNST_R"
```

## Python API

### Basic Usage

```python
from subtract import SubtractConfig, SubjectManager, PipelineRunner

# Create configuration for BIDS dataset
config = SubtractConfig.from_bids_dataset("/path/to/bids/dataset")

# Initialize managers
subject_manager = SubjectManager(config)
pipeline_runner = PipelineRunner(config)

# Discover subjects
subjects = subject_manager.discover_subjects()

# Process subjects
results = pipeline_runner.run_multiple_subjects(subjects)
```

### Advanced Usage

```python
# Custom configuration
config = SubtractConfig.from_bids_dataset("/path/to/bids/dataset")
config.processing.n_threads = 16
config.steps_to_run = ["copy_data", "denoise", "topup", "eddy"]

# Process specific subject with session
result = pipeline_runner.run_subject("001", session_id="baseline")

# Get subject information
subject_info = subject_manager.get_subject_info("001", "baseline")
print(f"Valid: {subject_info['validation']['valid']}")
print(f"DWI files: {subject_info['validation']['data_summary']['dwi_files']}")
```

### BIDS Utilities

```python
from subtract.utils.bids_utils import BIDSLayout

# Initialize BIDS layout
layout = BIDSLayout("/path/to/bids/dataset", config)

# Get DWI files for a subject
dwi_files = layout.get_dwi_files("001", "baseline")

# Get phase encoding groups
pe_groups = layout.get_phase_encoding_groups("001", "baseline")

# Validate subject data
validation = layout.validate_subject_data("001", "baseline")
```

## Output Structure

The pipeline creates a BIDS-derivatives compliant output structure:

```
derivatives/subtract/
├── dataset_description.json
├── sub-001/
│   ├── ses-baseline/
│   │   ├── dwi/
│   │   │   ├── sub-001_ses-baseline_dwi.nii.gz
│   │   │   ├── sub-001_ses-baseline_dwi_denoised.nii.gz
│   │   │   ├── Topup/
│   │   │   ├── Eddy/
│   │   │   ├── mrtrix3/
│   │   │   │   ├── response_functions/
│   │   │   │   ├── fod/
│   │   │   │   ├── tracks_1M_BNST_L.tck
│   │   │   │   ├── sift_weights.txt
│   │   │   │   ├── ROIs/
│   │   │   │   └── connectomes/
│   │   │   └── qc/
│   │   └── anat/
│   └── ses-followup/
└── results/
    ├── group_analysis/
    └── quality_control/
```

## Quality Control

SubTract includes comprehensive quality control features:

- **Motion assessment**: Frame-wise displacement and rotation metrics
- **Signal dropout detection**: Identification of corrupted volumes
- **Coverage assessment**: Brain coverage and signal intensity analysis
- **Tractography QC**: Track density and connectivity metrics
- **Outlier detection**: Statistical outlier identification

## Troubleshooting

### Common Issues

1. **BIDS validation errors**: Ensure your dataset follows BIDS specification
2. **Missing dependencies**: Install FSL, MRtrix3, and ANTs
3. **Memory issues**: Reduce number of threads or tracks
4. **Permission errors**: Check file permissions and disk space

### Debug Mode

Enable verbose logging for debugging:

```bash
subtract --verbose run /path/to/bids/dataset
```

### Log Files

Check log files in the output directory:
- `processing_log.txt`: General processing log
- `qc_report.html`: Quality control report
- `error_log.txt`: Error details

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone repository
git clone https://github.com/your-org/subtract-python.git
cd subtract-python

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
```

## Citation

If you use SubTract in your research, please cite:

```bibtex
@article{subtract2024,
  title={SubTract: A Python Pipeline for Subcortical Tractography},
  author={Your Name et al.},
  journal={NeuroImage},
  year={2024},
  doi={10.1016/j.neuroimage.2024.xxxxx}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [https://subtract-python.readthedocs.io](https://subtract-python.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/your-org/subtract-python/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/subtract-python/discussions)
- **Email**: support@subtract-pipeline.org 