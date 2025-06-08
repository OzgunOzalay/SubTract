# Changelog

All notable changes to the SubTract Python pipeline will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2024-06-08

### Added
- **Step 003: TopUp Distortion Correction** (`src/subtract/preprocessing/distortion_corrector.py`)
  - Complete FSL TopUp implementation for dual phase encoding correction
  - Automatic B0 extraction and merging from AP/PA data
  - Acquisition parameters file generation with metadata parsing
  - Automatic readout time detection from JSON sidecars
  - Field inhomogeneity estimation and correction
  - BIDS-compliant output structure

- **Step 004: Eddy Current Correction** (`src/subtract/preprocessing/eddy_corrector.py`)
  - FSL Eddy implementation with CUDA acceleration support
  - Automatic detection and use of `eddy_cuda10.2` with proper threading
  - Brain mask generation using FSL BET
  - Motion parameter estimation and correction
  - Eddy current distortion correction
  - Comprehensive QC metrics and outlier detection
  - Corrected b-vectors generation

### Fixed
- **Denoiser Skip Logic**: Fixed bug where skipped files (already existing) were incorrectly reported as failures
- **CUDA Threading**: Resolved eddy_cuda threading limitation (requires `--nthr=1`)
- **Path Handling**: Improved absolute path handling in subprocess calls for better reliability

### Enhanced
- **Pipeline Runner**: Updated to include TopUp and Eddy steps in processing workflow
- **Error Handling**: Improved error messages and validation for TopUp/Eddy dependencies
- **Progress Tracking**: Enhanced CLI progress reporting for new processing steps
- **Documentation**: Updated migration status and README to reflect current capabilities

### Performance
- **CUDA Acceleration**: Eddy correction now uses GPU acceleration, reducing processing time from hours to ~6-7 minutes per subject
- **Smart Resume**: All steps now properly support resume functionality for interrupted processing

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