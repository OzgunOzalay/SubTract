# SubTract v1.0.0-alpha Release Notes

## 🎉 Major Milestone: Complete Bash-to-Python Migration Accomplished!

**January 27, 2025** - We are excited to announce the release of SubTract v1.0.0-alpha, marking the **complete migration** of all 11 processing steps from Bash to Python. This represents a major achievement in modernizing the white matter tractography pipeline with comprehensive BIDS support, multi-conda environment integration, and end-to-end connectivity analysis capabilities.

## 🚀 What's New in v1.0.0-alpha

### ✅ **Complete Pipeline Implementation**
All 11 processing steps have been successfully migrated and tested:

1. **Data Organization** (001) - BIDS-compliant data structure setup
2. **DWI Denoising** (002) - MP-PCA denoising with MRtrix3
3. **Distortion Correction** (003) - FSL TopUp with dual phase encoding
4. **Motion/Eddy Correction** (004) - FSL Eddy with CUDA acceleration
5. **Registration** (005) - ANTs-based MNI→DWI template registration
6. **Microstructure Modeling** (006) - MDT NODDI & Ball-Stick fitting
7. **MRtrix3 Preprocessing** (007) - FOD estimation and 5TT generation
8. **Tractography** (008) - Probabilistic tracking with ACT
9. **SIFT2 Filtering** (009) - Track density optimization
10. **ROI Registration** (010) - **🆕 NEW** - fs2diff ROI transformation
11. **Connectome Generation** (011) - **🆕 NEW** - Connectivity fingerprints

### 🆕 **New Features Added**

#### **Step 010: ROI Registration**
- **Complete fs2diff Implementation**: Automated transformation of 12 BNST network ROIs from fsaverage to subject DWI space
- **Multi-Environment Support**: Seamless integration across FreeSurfer→subtract, ANTs→ants, MRtrix3→subtract environments (no separate mrtrix3 environment)
- **Bilateral Processing**: Creates left/right hemisphere parcellations with numbered regions (1-5)
- **Comprehensive ROI Coverage**: Amyg_L/R, BNST_L/R, Hipp_L/R, Insl_L/R, vmPF_L/R, Hypo_L/R
- **Structured Output**: 24 individual ROI files + 2 parcellation files per subject

#### **Step 011: Connectome Generation**
- **Part 1: Composite Microstructure & Track Sampling**
  - Optimized composite formula: `NDI*0.35 + (1-ODI)*0.25 + w_stick*0.25 + (1-w_ball)*0.15`
  - Track sampling using `tcksample -stat_tck mean` for microstructure-weighted tracks
  - Flexible architecture ready for additional microstructure metrics
- **Part 2: Connectivity Fingerprints**
  - Bilateral connectivity matrices for Left & Right BNST analysis
  - Advanced command structure: `tck2connectome` with `-vector -scale_invnodevol -scale_file -stat_edge mean`
  - Microstructure weighting using composite-derived track weights
  - CSV output format for comprehensive network analysis

### 🔧 **Technical Improvements**

#### **Full BIDS Compliance**
- **Legacy Path Support Removed**: Complete standardization on BIDS format (`sub-{subject}`)
- **Consistent Naming**: All processors now use BIDS paths throughout the entire pipeline
- **Infrastructure Updates**: Updated `base_processor.py`, `data_organizer.py`, and all step processors

#### **Enhanced Multi-Conda Environment Integration**
- **Complete Tool Isolation**: Tools run in appropriate environments automatically
  - FreeSurfer tools → `subtract` environment
  - ANTs tools → `ants` environment  
  - MRtrix3 tools → `subtract` environment (no separate mrtrix3 environment)
  - MDT tools → `mdt` environment (with fallback mocks)
- **Parameter Fixes**: Removed invalid `-term_ratio` parameter from SIFT2 (Step 009)
- **Import System**: Fixed relative/absolute import issues for reliable module loading

#### **Production-Ready Architecture**
```
derivatives/subtract/sub-{subject}/dwi/
├── preprocessed/          # Steps 001-007 outputs
├── mrtrix3/              # Tractography and filtering  
│   ├── tracks_1M_BNST_L.tck
│   ├── tracks_1M_BNST_R.tck
│   ├── sift_1M_BNST_L.txt
│   └── ROIs/             # Step 010: 24 registered ROI files + 2 parcellations
└── connectome/           # Step 011: Connectivity analysis
    ├── composite_microstructure.mif
    ├── track_weights_1M_BNST_L.txt  
    ├── track_weights_1M_BNST_R.txt
    └── fingerprints/
        ├── L_BNST_fingerprint.csv
        └── R_BNST_fingerprint.csv
```

## 🧪 **Testing & Validation**
- **Complete Pipeline Test**: All 11 steps validated with real data (subject ALC2004)
- **End-to-End Processing**: Successfully demonstrated from raw DWI to connectivity fingerprints
- **Environment Compatibility**: Multi-conda execution validated across all processing steps
- **Output Verification**: All expected files generated correctly with proper BIDS compliance

## 🎯 **Production-Ready Features**
- ✅ **Complete preprocessing to connectivity analysis pipeline**
- ✅ **Multi-subject parallel processing capability**
- ✅ **Resume functionality for interrupted processing**
- ✅ **Beautiful CLI with comprehensive progress tracking**
- ✅ **Type-safe configuration with Pydantic validation**
- ✅ **BIDS-compliant output structure**
- ✅ **Robust error handling and recovery mechanisms**

## 📚 **Documentation Updates**
- **README.md**: Complete v1.0.0 alpha documentation with full pipeline description
- **MIGRATION_STATUS.md**: Updated to reflect 100% migration completion
- **CHANGELOG.md**: Comprehensive changelog with all improvements and new features
- **Pipeline Configuration**: Updated example configs for all 11 steps

## 🔄 **Breaking Changes**
- **Legacy Path Support**: Removed support for non-BIDS directory structures
- **Parameter Updates**: Some SIFT2 parameters updated for MRtrix3 compatibility
- **Configuration**: Minor parameter name updates for improved clarity

## 🎯 **Migration Summary**
- **Phase 1** ✅: Core infrastructure + Steps 001-002
- **Phase 2** ✅: Steps 003-004 (TopUp + Eddy) 
- **Phase 3** ✅: Steps 007-009 (MRtrix3 + Tractography + SIFT2)
- **Phase 4** ✅: Steps 010-011 (ROI Registration + Connectomics)

## 💻 **Installation**

```bash
# Clone the repository
git clone https://github.com/your-org/SubTract.git
cd SubTract

# Install the package
pip install -e .

# Verify installation
subtract --help
```

## 🚀 **Quick Start**

```bash
# Run complete pipeline (all 11 steps)
subtract run /path/to/bids/dataset --participant-label sub-001

# Run specific steps only  
subtract run /path/to/bids/dataset --steps roi_registration,connectome

# Use configuration file
subtract run-config example_config.yaml

# Check processing status
subtract status /path/to/bids/dataset --participant-label sub-001
```

## 🙏 **Acknowledgments**
- **MRtrix3** team for excellent tractography tools
- **FSL** team for preprocessing utilities  
- **ANTs** team for registration methods
- **BIDS** community for data standardization
- **MDT** developers for microstructure modeling tools

## 📧 **Support**
For questions, bug reports, or feature requests, please open an issue on GitHub.

---

**🎉 SubTract v1.0.0-alpha represents a complete transformation of the pipeline from Bash to modern Python, providing researchers with a robust, scalable, and maintainable solution for white matter tractography analysis.** 