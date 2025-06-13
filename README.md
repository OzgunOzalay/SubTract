# SubTract: White Matter Tractography Pipeline

**SubTract** is a comprehensive white matter tractography pipeline designed for studying connectivity in limbic brain regions, with a particular focus on bed nucleus of the stria terminalis (BNST) circuitry. The pipeline has been **completely migrated from Bash to Python**, providing improved reliability, BIDS compliance, and modern software engineering practices.

## 🎉 Version 1.0.0 Alpha - Complete Pipeline Implementation

The complete SubTract pipeline is now available! All 11 processing steps have been successfully migrated from Bash to Python, offering a robust, BIDS-compliant solution for white matter tractography analysis.

## 🧠 Scientific Background

SubTract is specifically designed for an alyzing white matter connectivity in limbic circuits, particularly :

- **Bed Nucleus of the Stria Terminalis (BNST)**: A key component of the extended amygdala
- **Amygdala**: Central to fear and emotional processing  
- **Hippocampus**: Critical for memory formation
- **Hypothalamus**: Essential for neuroendocrine regulation
- **Ventromedial Prefrontal Cortex**: Important for emotion regulation

The pipeline performs probabilistic tractography between these regions and generates comprehensive connectivity fingerprints to characterize individual differences in white matter connectivity patterns.

## 🏗️ Complete Pipeline Architecture

### **✅ All Steps Implemented and Tested (Steps 001-011)**

1. **Data Organization** (001) - BIDS-compliant data structure setup
2. **DWI Denoising** (002) - MP-PCA denoising with MRtrix3
3. **Distortion Correction** (003) - FSL TopUp with dual phase encoding
4. **Motion/Eddy Correction** (004) - FSL Eddy with CUDA acceleration
5. **Registration** (005) - ANTs-based MNI→DWI template registration
6. **Microstructure Modeling** (006) - MDT NODDI & Ball-Stick fitting
7. **MRtrix3 Preprocessing** (007) - FOD estimation and 5TT generation
8. **Tractography** (008) - **✅ COMPLETE** - Probabilistic tracking with ACT
9. **SIFT2 Filtering** (009) - **✅ COMPLETE** - Track density optimization
10. **ROI Registration** (010) - **✅ COMPLETE** - fs2diff ROI transformation
11. **Connectome Generation** (011) - **✅ COMPLETE** - Connectivity matrix & fingerprints

### 🆕 **New in v1.0.0 Alpha**
- **Complete ROI Registration**: Automated transformation of 12 BNST network ROIs from fsaverage to subject DWI space
- **Connectivity Fingerprints**: Microstructure-weighted connectivity matrices for bilateral BNST analysis
- **Composite Microstructure**: Optimized combination of NODDI and Ball-Stick metrics
- **Full BIDS Compliance**: Standardized paths and naming throughout

## 🚀 Key Features

- **🔬 BIDS Compliance**: Native support for Brain Imaging Data Structure
- **🐍 Modern Python**: Type-safe implementation with Pydantic validation
- **🔧 Multi-Conda Integration**: Automatic tool isolation (subtract/ants/mdt environments)
- **⚡ GPU Acceleration**: CUDA support for FSL Eddy correction
- **📊 Rich CLI**: Beautiful progress tracking and reporting with status dashboard
- **🔄 Resume Capability**: Robust error handling with restart functionality
- **📈 Scalable**: Multi-subject parallel processing
- **🎯 Microstructure-Informed**: Integration of NODDI metrics with tractography
- **🧮 Complete Connectomics**: From preprocessing to connectivity fingerprints

## 💻 Installation

### Prerequisites

- **Python 3.8+**
- **Conda/Miniconda**
- **CUDA Toolkit** (optional, for GPU acceleration)

### Required Conda Environments

The pipeline uses multiple conda environments for tool isolation:

```bash
# Subtract environment with MRtrix3 and FSL
conda create -n subtract python=3.9
conda activate subtract  
conda install -c mrtrix3 mrtrix3=3.0.4
# Add FSL, FreeSurfer, and other tools

# ANTs environment for registration
conda create -n ants -c conda-forge ants

# MDT environment for microstructure modeling
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

### Complete Pipeline Execution

```bash
# Run full pipeline (all 11 steps)
subtract run /path/to/bids/dataset \
    --participant-label sub-001 sub-002

# Run specific steps only
subtract run /path/to/bids/dataset \
    --steps tractography,sift2,roi_registration,connectome \
    --participant-label sub-001

# Use configuration file for customization
subtract run-config example_config.yaml

# Check pipeline status
subtract status /path/to/bids/dataset --participant-label sub-001
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
  sift2_ndi_threshold: 0.1
  sift2_output_coeffs: true
  sift2_output_mu: true

# ROI configuration
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

## 🧪 Testing & Validation

### **Latest Test Results (January 2025)**

**Environment**: Linux 6.8.0-60-generic  
**Test Subject**: ALC2004 (BIDS format)  
**Pipeline Steps**: Complete pipeline (001-011)  
**Success Rate**: 100%

**Key Outputs Generated**:
- **Tractography**: `tracks_1M_BNST_L.tck`, `tracks_1M_BNST_R.tck`
- **SIFT2 Weights**: Track density optimization with NDI weighting
- **ROI Registration**: 12 bilateral ROIs transformed to subject space
- **Connectivity**: `L_BNST_fingerprint.csv`, `R_BNST_fingerprint.csv`
- **Microstructure**: `composite_microstructure.mif` with optimized formula

### Hardware Requirements

- **CPU**: Multi-core recommended (pipeline uses 24 threads by default)
- **RAM**: 16GB+ recommended for large datasets
- **GPU**: NVIDIA GPU with CUDA for accelerated Eddy correction
- **Storage**: ~15GB per subject for complete pipeline outputs

## 📁 Project Structure

```
SubTract/
├── src/subtract/           # Main Python package
│   ├── config/            # Configuration management
│   ├── core/              # Pipeline orchestration
│   ├── preprocessing/     # Steps 001-007
│   ├── tractography/      # Steps 008-009
│   ├── registration/      # Step 010
│   ├── connectome/        # Step 011
│   └── utils/             # Utility functions
├── ROIs/                  # Template ROI files
├── Templates/             # Brain templates
├── example_config.yaml    # Configuration template
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## 🔧 Development Status

### ✅ **Production Ready (v1.0.0 Alpha)**
- **Complete Pipeline**: All 11 steps implemented and tested
- **BIDS Support**: Full compliance with BIDS specification
- **Multi-Environment**: Seamless conda environment management
- **Error Handling**: Robust validation and recovery mechanisms
- **Rich CLI**: Progress tracking and status reporting
- **Connectivity Analysis**: Microstructure-informed connectomics

### 🎯 **Pipeline Capabilities**
- End-to-end processing from raw DWI to connectivity fingerprints
- Bilateral BNST network analysis with 12 ROI regions
- Microstructure-weighted track filtering using NODDI metrics
- Automated quality control and validation at each step
- Resume capability for interrupted processing

### 📈 **Performance Features**
- Optimized track count (1M per hemisphere) for efficiency
- GPU acceleration for motion correction
- Parallel subject processing capability
- Smart caching and intermediate file management

## 🎯 Output Structure

```
derivatives/subtract/sub-{subject}/dwi/
├── preprocessed/          # Steps 001-007 outputs
├── mrtrix3/              # Tractography and filtering
│   ├── tracks_1M_BNST_L.tck
│   ├── tracks_1M_BNST_R.tck  
│   ├── sift_1M_BNST_L.txt
│   └── ROIs/             # Registered ROI files
└── connectome/           # Step 011 outputs
    ├── composite_microstructure.mif
    ├── track_weights_1M_BNST_L.txt
    └── fingerprints/
        ├── L_BNST_fingerprint.csv
        └── R_BNST_fingerprint.csv
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📚 Documentation

- **Technical Details**: See `README_PYTHON.md` for comprehensive API documentation
- **Migration Status**: See `MIGRATION_STATUS.md` for completed migration details
- **Changelog**: See `CHANGELOG.md` for version history and updates

## 📧 Contact

For questions about the SubTract pipeline, please open an issue on GitHub or contact the development team.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **MRtrix3** team for excellent tractography tools
- **FSL** team for preprocessing utilities  
- **ANTs** team for registration methods
- **BIDS** community for data standardization
- **MDT** developers for microstructure modeling tools

