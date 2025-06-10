# SubTract: White Matter Tractography Pipeline

**SubTract** is a comprehensive white matter tractography pipeline designed for studying connectivity in limbic brain regions, with a particular focus on bed nucleus of the stria terminalis (BNST) circuitry. The pipeline has been migrated from Bash to Python, providing improved reliability, BIDS compliance, and modern software engineering practices.

## 🧠 Scientific Background

SubTract is specifically designed for analyzing white matter connectivity in limbic circuits, particularly:

- **Bed Nucleus of the Stria Terminalis (BNST)**: A key component of the extended amygdala
- **Amygdala**: Central to fear and emotional processing
- **Hippocampus**: Critical for memory formation
- **Hypothalamus**: Essential for neuroendocrine regulation
- **Ventromedial Prefrontal Cortex**: Important for emotion regulation

The pipeline performs probabilistic tractography between these regions to characterize individual differences in white matter connectivity patterns.

## 🏗️ Pipeline Architecture

### Current Implementation Status: **Steps 001-009 Complete**

1. **Data Organization** (001) - BIDS-compliant data structure setup
2. **DWI Denoising** (002) - MP-PCA denoising with MRtrix3
3. **Distortion Correction** (003) - FSL TopUp with dual phase encoding
4. **Motion/Eddy Correction** (004) - FSL Eddy with CUDA acceleration
5. **Registration** (005) - ANTs-based template registration
6. **Microstructure Modeling** (006) - MDT NODDI fitting
7. **MRtrix3 Preprocessing** (007) - FOD estimation and 5TT generation
8. **Tractography** (008) - **✅ COMPLETE** - Probabilistic tracking with ACT
9. **SIFT2 Filtering** (009) - **✅ COMPLETE** - Track density optimization with configurable parameters

### Upcoming Steps:
10. **ROI Registration** (010) - Template ROI transformation
11. **Connectome Construction** (011) - Connectivity matrix generation

## 🚀 Key Features

- **🔬 BIDS Compliance**: Native support for Brain Imaging Data Structure
- **🐍 Modern Python**: Type-safe implementation with Pydantic validation
- **🔧 Conda Integration**: Automatic tool isolation across environments
- **⚡ GPU Acceleration**: CUDA support for FSL Eddy correction
- **📊 Rich CLI**: Beautiful progress tracking and reporting
- **🔄 Resume Capability**: Robust error handling with restart functionality
- **📈 Scalable**: Multi-subject parallel processing

## 💻 Installation

### Prerequisites

- **Python 3.8+**
- **Conda/Miniconda**
- **CUDA Toolkit** (optional, for GPU acceleration)

### Required Conda Environments

The pipeline uses multiple conda environments for tool isolation:

```bash
# Base environment with MRtrix3 and FSL
conda create -n subtract python=3.9
conda activate subtract  
conda install -c mrtrix3 mrtrix3=3.0.4
# Add other FSL tools as needed

# ANTs environment  
conda create -n ants -c conda-forge ants

# MDT environment (optional, mocks available)
conda create -n mdt python=3.8
# Install MDT tools if hardware supports
```

### Pipeline Installation

```bash
# Clone repository
git clone https://github.com/yourusername/SubTract.git
cd SubTract

# Install Python package
pip install -e .

# Verify installation
subtract --help
```

## 📊 Usage

### BIDS Dataset Processing

```bash
# Run complete preprocessing + tractography + SIFT2 pipeline
subtract run /path/to/bids/dataset \
    --steps copy_data,denoise,topup,eddy,mdt,mrtrix_prep,tractography,sift2 \
    --participant-label sub-001 sub-002

# Use configuration file
subtract run-config example_config.yaml

# Validate BIDS dataset
subtract validate /path/to/bids/dataset
```

### Configuration

The pipeline uses YAML configuration files. See `example_config.yaml` for all options:

```yaml
# Essential paths
paths:
  base_path: /path/to/project
  data_dir: /path/to/bids/dataset
  analysis_dir: /path/to/derivatives/subtract

# Processing parameters
processing:
  n_threads: 24
  n_tracks: 1000000  # 1M tracks per hemisphere
  track_algorithm: "iFOD2"
  eddy_cuda: true
  
  # SIFT2 filtering parameters
  sift2_term_ratio: 0.1
  sift2_ndi_threshold: 0.1
  sift2_output_coeffs: true
  sift2_output_mu: true

# ROI targets for tractography
rois:
  target_rois:
    - "BNST_L"
    - "BNST_R"
```

## 🧪 Testing & Validation

### Recent Test Results (January 2025)

**Environment**: Linux 6.8.0-60-generic  
**Test Subject**: ALC2004 (BIDS format)  
**Pipeline Steps**: 001-004 + 006-009  
**Duration**: ~33.5 minutes  
**Success Rate**: 100%

**Outputs Generated**:
- `tracks_1M_BNST_L.tck` - Left BNST tractography (1M tracks)
- `tracks_1M_BNST_R.tck` - Right BNST tractography (1M tracks)

### Hardware Requirements

- **CPU**: Multi-core recommended (pipeline uses 24 threads by default)
- **RAM**: 16GB+ recommended for large datasets
- **GPU**: NVIDIA GPU with CUDA for accelerated Eddy correction
- **Storage**: ~10GB per subject for intermediate files

## 📁 Project Structure

```
SubTract/
├── src/subtract/           # Main Python package
│   ├── config/            # Configuration management
│   ├── core/              # Pipeline orchestration
│   ├── preprocessing/     # Steps 001-007
│   ├── tractography/      # Steps 008-009
│   ├── registration/      # Step 010
│   ├── connectomics/      # Step 011
│   └── utils/             # Utility functions
├── ROIs/                  # Template ROI files
├── Templates/             # Brain templates
├── example_config.yaml    # Configuration template
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Development Status

### ✅ Completed (Production Ready)
- Core infrastructure and BIDS support
- Complete preprocessing pipeline (Steps 001-007)
- Tractography implementation (Step 008)
- SIFT2 track filtering (Step 009)
- Conda environment integration
- Rich CLI with progress tracking

### 🚧 In Development
- ROI registration (Step 010)  
- Connectome construction (Step 011)

### 📈 Performance Optimizations
- Reduced track count from 5M to 1M per hemisphere for faster processing
- GPU acceleration for motion correction
- Parallel subject processing
- Resume capability for interrupted runs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- **Technical Details**: See `README_PYTHON.md` for comprehensive API documentation
- **Migration Status**: See `MIGRATION_STATUS.md` for current progress
- **Migration Plan**: See `migration_plan.md` for development roadmap

## 📧 Contact

For questions about the SubTract pipeline, please open an issue on GitHub or contact the development team.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **MRtrix3** team for excellent tractography tools
- **FSL** team for preprocessing utilities  
- **ANTs** team for registration methods
- **BIDS** community for data standardization

