# SubTract Pipeline: Bash to Python Migration Plan

## Overview
Migration of the SubTract white matter tractography pipeline from Bash to Python while preserving all functionality and improving the pipeline architecture.

## Phase 1: Infrastructure Setup (Weeks 1-2)

### 1.1 Project Structure
```
subtract_python/
├── src/
│   ├── subtract/
│   │   ├── __init__.py
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   ├── settings.py
│   │   │   └── paths.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── base_processor.py
│   │   │   ├── subject_manager.py
│   │   │   └── pipeline_runner.py
│   │   ├── preprocessing/
│   │   │   ├── __init__.py
│   │   │   ├── data_organizer.py
│   │   │   ├── denoiser.py
│   │   │   ├── distortion_corrector.py
│   │   │   └── motion_corrector.py
│   │   ├── registration/
│   │   │   ├── __init__.py
│   │   │   ├── template_registration.py
│   │   │   └── roi_transformer.py
│   │   ├── microstructure/
│   │   │   ├── __init__.py
│   │   │   ├── mdt_processor.py
│   │   │   └── noddi_fitter.py
│   │   ├── tractography/
│   │   │   ├── __init__.py
│   │   │   ├── mrtrix_preprocessor.py
│   │   │   ├── track_generator.py
│   │   │   ├── track_filter.py
│   │   │   └── connectome_builder.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── file_utils.py
│   │   │   ├── logging_utils.py
│   │   │   ├── validation.py
│   │   │   └── parallel_processing.py
│   │   └── visualization/
│   │       ├── __init__.py
│   │       ├── quality_control.py
│   │       └── connectivity_plots.py
├── tests/
├── docs/
├── data/
│   ├── templates/
│   ├── rois/
│   └── test_data/
├── configs/
├── scripts/
├── requirements.txt
├── setup.py
├── pyproject.toml
└── README.md
```

### 1.2 Core Dependencies
```python
# requirements.txt
nibabel>=5.0.0
numpy>=1.21.0
scipy>=1.7.0
pandas>=1.3.0
matplotlib>=3.5.0
seaborn>=0.11.0
scikit-image>=0.19.0
dipy>=1.7.0
nipype>=1.8.0
pydantic>=2.0.0
click>=8.0.0
rich>=12.0.0
loguru>=0.6.0
joblib>=1.1.0
tqdm>=4.64.0
pytest>=7.0.0
black>=22.0.0
flake8>=4.0.0
```

### 1.3 Configuration Management
- Use Pydantic for type-safe configuration
- YAML/TOML configuration files
- Environment-specific settings
- Validation of paths and parameters

## Phase 2: Core Infrastructure (Weeks 3-4)

### 2.1 Base Classes and Interfaces
```python
# Abstract base processor for all pipeline steps
class BaseProcessor(ABC):
    @abstractmethod
    def process(self, subject_id: str, **kwargs) -> ProcessingResult
    
    @abstractmethod
    def validate_inputs(self, **kwargs) -> bool
    
    @abstractmethod
    def get_outputs(self) -> List[Path]
```

### 2.2 Subject Management System
- Subject discovery and validation
- Data organization and tracking
- Progress monitoring
- Error handling and recovery

### 2.3 Pipeline Orchestration
- Step dependency management
- Parallel processing capabilities
- Resume functionality
- Comprehensive logging

## Phase 3: Preprocessing Modules (Weeks 5-7)

### 3.1 Data Organization (Step 001)
```python
class DataOrganizer(BaseProcessor):
    def organize_subject_data(self, subject_id: str) -> None:
        # Copy and organize DWI data
        # Create analysis directory structure
        # Validate data integrity
```

### 3.2 Denoising (Step 002)
```python
class DWIDenoiser(BaseProcessor):
    def denoise_dwi(self, dwi_file: Path, output_file: Path) -> None:
        # Wrapper for MRtrix3 dwidenoise
        # Input validation
        # Quality metrics
```

### 3.3 Distortion Correction (Step 003)
```python
class DistortionCorrector(BaseProcessor):
    def run_topup(self, ap_file: Path, pa_file: Path) -> TopupResult:
        # FSL TopUp implementation
        # Dual phase-encoding support
        # Field map generation
```

### 3.4 Motion Correction (Step 004)
```python
class MotionCorrector(BaseProcessor):
    def run_eddy(self, dwi_file: Path, mask: Path) -> EddyResult:
        # FSL Eddy implementation
        # CUDA support detection
        # QC report generation
```

## Phase 4: Registration and Microstructure (Weeks 8-10)

### 4.1 Template Registration (Step 005)
```python
class TemplateRegistration(BaseProcessor):
    def register_mni_to_dwi(self, dwi_brain: Path, template: Path) -> RegistrationResult:
        # ANTs registration
        # ROI transformation
        # Quality assessment
```

### 4.2 Microstructure Analysis (Step 006)
```python
class MicrostructureProcessor(BaseProcessor):
    def fit_noddi_model(self, dwi_file: Path, mask: Path) -> NODDIResult:
        # MDT NODDI fitting
        # Parameter maps generation
        # Quality control
```

## Phase 5: Tractography Pipeline (Weeks 11-14)

### 5.1 MRtrix3 Preprocessing (Step 007)
```python
class MRtrixPreprocessor(BaseProcessor):
    def prepare_for_tracking(self, dwi_file: Path) -> MRtrixPrepResult:
        # FOD estimation
        # 5TT segmentation
        # Coregistration
        # Seed boundary creation
```

### 5.2 Track Generation (Step 008)
```python
class TrackGenerator(BaseProcessor):
    def generate_tracks(self, seed_roi: Path, fod_file: Path) -> TrackingResult:
        # Probabilistic tracking
        # BNST-specific seeding
        # Quality metrics
```

### 5.3 Track Filtering (Step 009)
```python
class TrackFilter(BaseProcessor):
    def apply_sift2(self, tracks: Path, fod: Path, ndi_mask: Path) -> SIFT2Result:
        # Microstructure-informed filtering
        # Weight calculation
        # Track refinement
```

### 5.4 Connectome Construction (Steps 010-011)
```python
class ConnectomeBuilder(BaseProcessor):
    def build_connectivity_matrix(self, tracks: Path, parcellation: Path) -> ConnectivityResult:
        # Connectivity matrix generation
        # Fingerprint calculation
        # Network analysis
```

## Phase 6: Advanced Features and Improvements (Weeks 15-16)

### 6.1 Enhanced Quality Control
- Automated QC metrics
- Interactive visualization
- Outlier detection
- Report generation

### 6.2 Parallel Processing
- Multi-subject processing
- Step-level parallelization
- Resource management
- Progress tracking

### 6.3 Configuration and Flexibility
- Parameter optimization
- Method selection
- Custom ROI support
- Pipeline customization

## Phase 7: Testing and Validation (Weeks 17-18)

### 7.1 Unit Testing
- Individual module tests
- Mock data testing
- Edge case handling
- Performance benchmarks

### 7.2 Integration Testing
- End-to-end pipeline testing
- Comparison with original results
- Cross-platform validation
- Performance optimization

### 7.3 Documentation
- API documentation
- User guides
- Tutorial notebooks
- Best practices

## Key Improvements Over Original Pipeline

### 1. **Type Safety and Validation**
- Pydantic models for configuration
- Input/output validation
- Runtime type checking

### 2. **Error Handling and Recovery**
- Graceful error handling
- Checkpoint/resume functionality
- Detailed error reporting

### 3. **Modularity and Extensibility**
- Plugin architecture
- Easy method swapping
- Custom processing steps

### 4. **Performance Optimization**
- Intelligent caching
- Parallel processing
- Resource monitoring

### 5. **Quality Control**
- Automated QC metrics
- Interactive visualizations
- Comprehensive reporting

### 6. **Reproducibility**
- Version tracking
- Parameter logging
- Deterministic processing

### 7. **User Experience**
- CLI with rich output
- Progress bars
- Interactive configuration
- Web-based monitoring

## Migration Strategy

### Incremental Approach
1. Start with core infrastructure
2. Migrate one step at a time
3. Validate against original results
4. Add improvements incrementally

### Backward Compatibility
- Support for existing data structures
- Configuration migration tools
- Result comparison utilities

### Testing Strategy
- Unit tests for each component
- Integration tests for workflows
- Performance benchmarks
- Cross-validation with original pipeline

## Timeline Summary
- **Weeks 1-4**: Infrastructure and core systems
- **Weeks 5-10**: Preprocessing and registration modules
- **Weeks 11-14**: Tractography pipeline
- **Weeks 15-16**: Advanced features
- **Weeks 17-18**: Testing and validation

## Success Metrics
1. **Functional Parity**: All original functionality preserved
2. **Performance**: Equal or better processing speed
3. **Reliability**: Improved error handling and recovery
4. **Usability**: Enhanced user experience and documentation
5. **Maintainability**: Clean, modular, well-tested code 