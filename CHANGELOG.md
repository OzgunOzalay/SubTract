# Changelog

All notable changes to this project will be documented in this file.

## [1.0.0-alpha] - 2025-01-27 - Complete Pipeline Migration

### 🎉 **MAJOR MILESTONE: Complete Bash-to-Python Migration**
**All 12 processing steps successfully migrated!** The SubTract pipeline is now fully functional in Python with comprehensive BIDS support, multi-conda environment integration, and end-to-end connectivity analysis.

### ✅ **New Steps Completed**
- **Step 002b: Gibbs Ringing Removal** (`src/subtract/preprocessing/gibbs_remover.py`) - **NEW**
  - MRtrix3 `mrdegibbs` integration for Gibbs artifact removal
  - Kellner et al. method using local subvoxel-shifts
  - Pipeline position: After DWI denoising, before distortion correction
  - File naming: Input: `*_denoised.nii.gz` → Output: `*_denoised_degibbs.nii.gz`
  - Multi-threaded processing with smart resume capability
  - Added to all configuration files and Docker integration

- **Step 010: ROI Registration** (`src/subtract/registration/roi_registration.py`)
  - Complete fs2diff ROI transformation implementation
  - Automated registration of 12 BNST network ROIs from fsaverage to subject DWI space
  - Multi-conda environment support (FreeSurfer→subtract, ANTs→ants, MRtrix3→subtract)
  - Bilateral processing: Creates left/right hemisphere parcellations with numbered regions (1-5)
  - ROI list: Amyg_L/R, BNST_L/R, Hipp_L/R, Insl_L/R, vmPF_L/R, Hypo_L/R
  - Output: 24 individual ROI files + 2 parcellation files per subject

- **Step 011: Connectome Generation** (`src/subtract/connectome/connectivity_matrix.py`)
  - **Part 1: Composite Microstructure & Track Sampling**
    - Composite formula: `NDI*0.35 + (1-ODI)*0.25 + w_stick*0.25 + (1-w_ball)*0.15`
    - Track sampling using `tcksample -stat_tck mean` for microstructure-weighted tracks
    - Flexible architecture ready for additional microstructure metrics
  - **Part 2: Connectivity Fingerprints**
    - Bilateral connectivity matrices for Left & Right BNST
    - Command structure: `tck2connectome` with `-vector -scale_invnodevol -scale_file -stat_edge mean`
    - Microstructure weighting using composite-derived track weights
    - Output: CSV connectivity fingerprints for comprehensive network analysis

### 🚀 **Pipeline Architecture Completed**
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

### 🎯 **Full BIDS Compliance**
- **Legacy Path Support Removed**: Complete standardization on BIDS format (`sub-{subject}`)
- **Consistent Naming**: All processors now use BIDS paths throughout
- **Updated Infrastructure**: `base_processor.py`, `data_organizer.py`, all step processors

### 🔧 **Technical Improvements**
- **Multi-Conda Environment Integration**: Complete tool isolation across all steps
  - FreeSurfer tools → `subtract` environment
  - ANTs tools → `ants` environment  
  - MRtrix3 tools → `subtract` environment
  - MDT tools → `mdt` environment (with fallback mocks)
- **Parameter Fixes**: Removed invalid `-term_ratio` parameter from SIFT2 (Step 009)
- **Enhanced Error Handling**: Robust validation and recovery mechanisms throughout
- **Import System**: Fixed relative/absolute import issues for reliable module loading

### 🧪 **Testing & Validation**
- **Complete Pipeline Test**: All 11 steps validated with real data (ALC2004)
- **End-to-End Processing**: From raw DWI to connectivity fingerprints
- **Environment Compatibility**: Multi-conda execution validated
- **Output Verification**: All expected files generated correctly

### 📚 **Documentation Updates**
- **README.md**: Complete v1.0.0 alpha documentation with full pipeline description
- **MIGRATION_STATUS.md**: Updated to reflect 100% migration completion
- **Pipeline Configuration**: Updated example configs for all 11 steps

### 🎯 **Production Ready Features**
- Complete preprocessing to connectivity analysis pipeline
- Multi-subject parallel processing capability
- Resume functionality for interrupted processing
- Beautiful CLI with comprehensive progress tracking
- Type-safe configuration with Pydantic validation
- BIDS-compliant output structure

### 🔄 **Breaking Changes**
- **Legacy Path Support**: Removed support for non-BIDS directory structures
- **Configuration**: Some parameter names updated for clarity

### 📋 **Migration Summary**
- **Phase 1** ✅: Core infrastructure + Steps 001-002
- **Phase 2** ✅: Steps 003-004 (TopUp + Eddy) 
- **Phase 3** ✅: Steps 007-009 (MRtrix3 + Tractography + SIFT2)
- **Phase 4** ✅: Steps 010-011 (ROI Registration + Connectomics)

**🎉 Version 1.0.0 Alpha: Complete pipeline migration accomplished!**

## [1.2.0] - 2024-06-09

### 🎉 Major Features
- **Enhanced Conda Environment Management**: Implemented robust environment switching with dedicated conda environments for different tool suites
- **Dependency Conflict Resolution**: Isolated problematic tools in separate environments to prevent library conflicts

### 🔧 Technical Improvements
- **Three-Environment Architecture**:
  - `subtract` environment: MRtrix3, FSL, main pipeline tools
  - `mdt` environment: MDT tools (isolated for dependency conflicts)
  - `ants` environment: ANTs registration tools (isolated for library conflicts)

### ✅ Bug Fixes
- Fixed MRtrix3 installation checks to work with subtract conda environment
- Resolved FreeSurfer color lookup table formatting inconsistencies
- Fixed ANTs registration library dependency conflicts (`libITKIOTransformMINC-5.3.so.1`)
- Implemented proper conda environment deactivate/activate sequence

### 🚀 Pipeline Improvements
- **100% Success Rate**: All major preprocessing steps now working reliably
- **Environment Isolation**: Tools run in appropriate environments automatically
- **Robust Error Handling**: Pipeline continues with graceful fallbacks when needed
- **Cross-Environment Compatibility**: Pipeline runs from any conda environment

### 📋 Completed Pipeline Steps
- ✅ Environment switching and tool isolation
- ✅ MRtrix3 preprocessing (all 8 phases)
- ✅ ANTs registration with proper output files
- ✅ FreeSurfer 5TT generation
- ✅ FOD estimation and processing  
- ✅ GM/WM interface creation

### 🔄 Breaking Changes
- None - backwards compatible

---

## [1.1.0] - Previous Release
- Implemented Steps 003-004 - Complete motion and distortion correction pipeline
- Added TopUp and Eddy current correction
- Enhanced BIDS compliance

## [1.0.0] - 2024-06-07

### Added
- **Core Infrastructure**
  - BIDS-compliant configuration system with Pydantic validation
  - Subject discovery and management with multi-session support
  - Pipeline orchestration with parallel processing capabilities
  - Base processor framework for standardized step implementation
  - Rich CLI interface with beautiful progress tracking

- **Step 001: Data Organization** (`src/subtract/preprocessing/data_organizer.py`)
  - BIDS-aware data copying and organization
  - Metadata preservation and validation
  - Format conversion (.nii → .nii.gz)
  - Legacy data structure support

- **Step 002: DWI Denoising** (`src/subtract/preprocessing/denoiser.py`)
  - MRtrix3 dwidenoise implementation
  - MP-PCA denoising algorithm
  - Multi-threaded processing
  - Smart output detection and resume capability

- **BIDS Utilities** (`src/subtract/utils/bids_utils.py`)
  - Complete BIDS dataset discovery and validation
  - Phase encoding direction detection
  - DWI and anatomical file finding
  - JSON metadata extraction

- **Command Line Interface** (`src/subtract/cli.py`)
  - `subtract run` - Process BIDS datasets
  - `subtract validate` - Validate BIDS data
  - `subtract status` - Show processing status
  - `subtract init-config` - Create configuration files
  - Rich progress reporting and error handling

### Technical
- Python 3.8+ support with comprehensive type hints
- Robust error handling and recovery mechanisms
- Comprehensive logging and debugging capabilities
- BIDS-derivatives compliant output structure
- Cross-platform compatibility (Linux, macOS, Windows)

---

## Legend

- **Added**: New features and functionality
- **Changed**: Modifications to existing features
- **Deprecated**: Features that will be removed in future versions
- **Removed**: Features that have been removed
- **Fixed**: Bug fixes and error corrections
- **Security**: Security-related improvements
- **Performance**: Performance improvements and optimizations
- **Enhanced**: Improvements to existing functionality
- **Technical**: Technical improvements and infrastructure changes

## [0.9.0] - 2025-01-27 - SIFT2 Track Filtering Complete

### ✅ Major Features Added
- **Step 009 SIFT2 Filtering**: Complete implementation of track filtering and optimization
  - MRtrix3 tcksift2 integration with configurable parameters
  - NDI-weighted processing mask creation from NODDI data
  - Track density optimization for improved biological accuracy
  - Configurable outputs: SIFT2 weights, mu values, coefficients
  - Multi-hemisphere support for left/right BNST tracks

### 🎛️ Configuration System Enhanced
- **5 New SIFT2 Parameters**: Fully configurable via YAML
  - `sift2_term_ratio`: Termination ratio (default: 0.1)
  - `sift2_ndi_threshold`: NDI threshold for mask creation (default: 0.1)
  - `sift2_output_coeffs`: Generate coefficients files (default: true)
  - `sift2_output_mu`: Generate mu values files (default: true)
  - `sift2_fd_scale_gm`: Advanced GM scaling option (default: false)

### 🧪 Testing & Integration
- **Full Pipeline Integration**: Step 009 seamlessly integrated into pipeline runner
- **Configuration Validation**: Type-safe parameter validation with Pydantic
- **Expected Output Generation**: Proper file tracking and validation
- **Environment Compatibility**: Uses 'subtract' conda environment for MRtrix3 tools (no separate mrtrix3 environment needed)

### 📊 Expected Outputs per Subject
```
analysis_dir/{subject}/dwi/mrtrix3/
├── ndi_5tt_mask.mif              # NDI-weighted processing mask
├── sift_1M_BNST_L.txt           # SIFT2 weights - Left
├── sift_1M_BNST_R.txt           # SIFT2 weights - Right
├── sift_mu_1M_BNST_L.txt        # Mu values - Left (optional)
├── sift_mu_1M_BNST_R.txt        # Mu values - Right (optional)
├── sift_coeffs_1M_BNST_L.txt    # Coefficients - Left (optional)
└── sift_coeffs_1M_BNST_R.txt    # Coefficients - Right (optional)
```

### 🎯 Current Status
- **Complete Pipeline**: Steps 001-009 (Preprocessing through SIFT2 Filtering)
- **Next Phase**: Steps 010-011 (ROI Registration, Connectomics)
- **Migration Progress**: 82% complete (9/11 major steps)

### 🔧 Breaking Changes
- None - backwards compatible with existing configurations

---

## [0.8.0] - 2025-01-XX - Tractography Implementation Complete

### ✅ Major Features Added
- **Step 008 Tractography**: Complete implementation of probabilistic tractography
  - BNST ROI transformation from fsaverage to diffusion space using ANTs
  - Anatomically constrained tractography (ACT) with MRtrix3 tckgen
  - Backtracking support for improved track quality
  - 1M tracks per hemisphere (optimized from 5M for faster processing)
  - Proper NIfTI to MIF conversion with mrconvert

### 🧪 Testing & Validation
- **Successful Test Run**: ALC2004 subject (January 2025)
  - Complete pipeline steps 001-008 executed successfully
  - Duration: ~33.5 minutes for full preprocessing + tractography
  - Output: `tracks_1M_BNST_L.tck` and `tracks_1M_BNST_R.tck`