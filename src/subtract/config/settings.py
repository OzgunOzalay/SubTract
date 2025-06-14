"""
Configuration management for SubTract pipeline.
"""

from pathlib import Path
from typing import Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
import os


class PathConfig(BaseModel):
    """Path configuration for the pipeline."""
    
    base_path: Path = Field(description="Base directory for the project")
    data_dir: Path = Field(description="Directory containing raw BIDS data")
    analysis_dir: Path = Field(description="Directory for analysis outputs")
    result_dir: Path = Field(description="Directory for final results")
    script_dir: Path = Field(description="Directory containing scripts and templates")
    
    @validator('*', pre=True)
    def expand_paths(cls, v):
        if isinstance(v, (str, Path)):
            return Path(v).expanduser().resolve()
        return v


class BIDSConfig(BaseModel):
    """BIDS-specific configuration."""
    
    # BIDS compliance settings
    validate_bids: bool = Field(default=True, description="Validate BIDS structure")
    bids_version: str = Field(default="1.8.0", description="BIDS version to validate against")
    
    # Data selection
    sessions: Optional[List[str]] = Field(default=None, description="Specific sessions to process")
    tasks: Optional[List[str]] = Field(default=None, description="Specific tasks to process")
    runs: Optional[List[str]] = Field(default=None, description="Specific runs to process")
    
    # DWI-specific BIDS settings
    dwi_suffixes: List[str] = Field(
        default=["dwi"],
        description="DWI file suffixes to look for"
    )
    
    # Phase encoding directions for TopUp
    phase_encoding_directions: List[str] = Field(
        default=["AP", "PA", "LR", "RL"],
        description="Phase encoding directions to look for"
    )
    
    # Required BIDS files
    required_dwi_files: List[str] = Field(
        default=["dwi.nii.gz", "dwi.bval", "dwi.bvec"],
        description="Required DWI files for each subject"
    )
    
    # Optional files
    optional_files: List[str] = Field(
        default=["dwi.json", "T1w.nii.gz", "T2w.nii.gz"],
        description="Optional files that enhance processing"
    )


class ProcessingConfig(BaseModel):
    """Processing parameters configuration."""
    
    # General processing
    n_threads: int = Field(default=24, description="Number of threads for processing")
    force_overwrite: bool = Field(default=False, description="Force overwrite existing files")
    
    # Denoising parameters
    denoise_method: str = Field(default="dwidenoise", description="Denoising method")
    
    # TopUp parameters
    topup_config: str = Field(default="b02b0.cnf", description="TopUp configuration file")
    readout_time: Optional[float] = Field(default=None, description="Total readout time (auto-detect from JSON if None)")
    
    # Eddy parameters
    eddy_cuda: bool = Field(default=True, description="Use CUDA for Eddy if available")
    eddy_method: str = Field(default="eddy_cuda10.2", description="Eddy method to use")
    bet_threshold: float = Field(default=0.2, description="BET threshold for brain extraction")
    
    # Registration parameters
    registration_type: str = Field(default="SyNQuick", description="ANTs registration type")
    
    # Tractography parameters
    n_tracks: int = Field(default=1000000, description="Number of tracks to generate")
    track_algorithm: str = Field(default="iFOD2", description="Tracking algorithm")
    track_cutoff: float = Field(default=0.1, description="FOD amplitude cutoff for terminating tracks (default: 0.1)")
    
    # SIFT2 parameters
    sift2_term_ratio: float = Field(default=0.1, description="SIFT2 minimum cost function decrease (as fraction of initial value) for algorithm continuation")
    sift2_ndi_threshold: float = Field(default=0.1, description="NDI threshold for SIFT2 processing mask")
    sift2_output_coeffs: bool = Field(default=True, description="Generate SIFT2 coefficients files")
    sift2_output_mu: bool = Field(default=True, description="Generate mu (proportionality coefficient) files")
    sift2_fd_scale_gm: bool = Field(default=False, description="Scale fibre density by GM volume")


class ROIConfig(BaseModel):
    """ROI configuration."""
    
    roi_names: List[str] = Field(
        default=[
            "Amyg_L_MNI", "Amyg_R_MNI",
            "BNST_L_MNI", "BNST_R_MNI", 
            "Hipp_L_MNI", "Hipp_R_MNI",
            "Insl_L_MNI", "Insl_R_MNI",
            "vmPF_L_MNI", "vmPF_R_MNI",
            "Hypo_L_MNI", "Hypo_R_MNI"
        ],
        description="List of ROI names to process"
    )
    
    target_rois: List[str] = Field(
        default=["BNST_L", "BNST_R"],
        description="Target ROIs for tractography"
    )


class SubtractConfig(BaseModel):
    """Main configuration class for SubTract pipeline."""
    
    paths: PathConfig
    bids: BIDSConfig = Field(default_factory=BIDSConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    rois: ROIConfig = Field(default_factory=ROIConfig)
    
    # Pipeline steps to run
    steps_to_run: List[str] = Field(
        default=[
            "copy_data", "denoise", "topup", "eddy", 
            "mdt", "mrtrix_prep", 
            "tractography", "sift2", "roi_registration", 
            "connectome"
        ],
        description="Pipeline steps to execute"
    )
    
    # Subject filtering
    subject_filter: Optional[str] = Field(
        default=None, 
        description="Regex pattern to filter subjects"
    )
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "SubtractConfig":
        """Load configuration from file."""
        import yaml
        
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        return cls(**config_data)
    
    @classmethod
    def from_legacy_bash(cls, base_path: Union[str, Path]) -> "SubtractConfig":
        """Create configuration from legacy bash pipeline structure."""
        base_path = Path(base_path)
        
        paths = PathConfig(
            base_path=base_path,
            data_dir=base_path / "Data",
            analysis_dir=base_path / "Analysis", 
            result_dir=base_path / "Results",
            script_dir=base_path / "Scripts"
        )
        
        return cls(paths=paths)
    
    @classmethod
    def from_bids_dataset(cls, bids_root: Union[str, Path]) -> "SubtractConfig":
        """Create configuration from BIDS dataset."""
        bids_root = Path(bids_root)
        
        paths = PathConfig(
            base_path=bids_root.parent,
            data_dir=bids_root,
            analysis_dir=bids_root.parent / "derivatives" / "subtract",
            result_dir=bids_root.parent / "derivatives" / "subtract" / "results",
            script_dir=bids_root.parent / "code"
        )
        
        # Enable BIDS validation by default
        bids_config = BIDSConfig(validate_bids=True)
        
        return cls(paths=paths, bids=bids_config)
    
    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to file."""
        import yaml
        
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and handle Path objects
        config_dict = self.dict()
        
        def convert_paths(obj):
            if isinstance(obj, dict):
                return {k: convert_paths(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_paths(item) for item in obj]
            elif isinstance(obj, Path):
                return str(obj)
            return obj
        
        config_dict = convert_paths(config_dict)
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def validate_paths(self) -> bool:
        """Validate that required paths exist."""
        required_paths = [
            self.paths.base_path,
            self.paths.data_dir,
        ]
        
        for path in required_paths:
            if not path.exists():
                raise FileNotFoundError(f"Required path does not exist: {path}")
        
        # Create output directories if they don't exist
        output_dirs = [
            self.paths.analysis_dir,
            self.paths.result_dir,
        ]
        
        for path in output_dirs:
            path.mkdir(parents=True, exist_ok=True)
        
        return True
    
    def validate_bids_structure(self) -> bool:
        """Validate BIDS structure if enabled."""
        if not self.bids.validate_bids:
            return True
        
        try:
            import bids
            layout = bids.BIDSLayout(self.paths.data_dir, validate=True)
            return True
        except ImportError:
            # pybids not available, skip validation
            return True
        except Exception as e:
            raise ValueError(f"BIDS validation failed: {str(e)}") 