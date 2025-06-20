"""
Track filtering processor for SubTract pipeline.

This module implements Step 009: SIFT2 track filtering using MRtrix3 tcksift2.
It creates NDI-weighted processing masks and applies SIFT2 filtering to 
improve the biological accuracy of white matter tractography.
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from subtract.core.base_processor import MRtrix3Processor, ProcessingResult


class TrackFilter(MRtrix3Processor):
    """
    Track filtering processor using SIFT2.
    
    This processor implements Step 009 of the SubTract pipeline:
    1. Create NDI-weighted processing mask from NODDI data
    2. Apply SIFT2 filtering to both left and right BNST tracks
    3. Generate SIFT2 weights, mu values, and coefficients
    """
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        """Initialize track filter."""
        super().__init__(config, logger)
        self.step_name = "sift2"
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        required_commands = [
            "mrcalc", "tcksift2"
        ]
        
        missing_commands = []
        for cmd in required_commands:
            try:
                subprocess.run([cmd, "--help"], capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_commands.append(cmd)
        
        if missing_commands:
            self.logger.warning(f"Missing commands: {missing_commands}")
            self.logger.warning("SIFT2 filtering step may fail")
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Apply SIFT2 filtering to tractography results.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            ProcessingResult with success status and output files
        """
        start_time = time.time()
        outputs = []
        metrics = {}
        
        try:
            # Use BIDS format for directory structure
            if session_id:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
                session_str = f" session {session_id}"
            else:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
                session_str = ""
            
            mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
            
            self.logger.info(f"Starting SIFT2 filtering for subject: {subject_id}{session_str}")
            self.logger.debug(f"Analysis directory constructed as: {analysis_dir}")
            self.logger.debug(f"Analysis directory exists: {analysis_dir.exists()}")
            
            # Validate prerequisites
            if not self._validate_prerequisites(subject_id, analysis_dir, mrtrix_dir):
                raise FileNotFoundError("Missing prerequisite files for SIFT2 filtering")
            
            # Step 1: Create NDI-weighted processing mask
            self.logger.info("Step 1: Creating NDI-weighted processing mask")
            mask_file = self._create_ndi_weighted_mask(subject_id, analysis_dir, mrtrix_dir)
            outputs.append(mask_file)
            
            # Step 2: Apply SIFT2 filtering to both hemispheres
            self.logger.info("Step 2: Applying SIFT2 filtering")
            sift2_files = self._run_sift2_filtering(subject_id, mrtrix_dir, mask_file)
            outputs.extend(sift2_files)
            
            metrics["ndi_mask_created"] = mask_file.exists()
            metrics["sift2_files_generated"] = len(sift2_files)
            metrics["hemispheres_processed"] = 2
            metrics["ndi_threshold_used"] = self.config.processing.sift2_ndi_threshold
            
            execution_time = time.time() - start_time
            
            return ProcessingResult(
                success=True,
                outputs=outputs,
                metrics=metrics,
                execution_time=execution_time,
                error_message=None
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"SIFT2 filtering failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _validate_prerequisites(self, subject_id: str, analysis_dir: Path, mrtrix_dir: Path) -> bool:
        """Validate that all prerequisite files exist."""
        # Files from previous steps
        required_files = [
            mrtrix_dir / "wmfod_norm.mif",           # From step 007 (MRtrix3 prep)
            mrtrix_dir / "5tt_coreg_fs_ants.mif",   # From step 007 (MRtrix3 prep)
            mrtrix_dir / "tracks_1M_BNST_L.tck",    # From step 008 (Tractography)
            mrtrix_dir / "tracks_1M_BNST_R.tck",    # From step 008 (Tractography)
        ]
        
        # NDI file from MDT processing (step 006) - BIDS format
        noddi_paths = [
            # Current actual structure: BIDS subject dir + legacy brain mask folder name  
            analysis_dir / "dwi" / "mdt" / "output" / f"sub-{subject_id}_brain_mask" / "NODDIDA" / "NDI.nii.gz",
            # Alternative simplified location
            analysis_dir / "dwi" / "mdt" / "NODDIDA" / "NDI.nii.gz",
        ]
        
        self.logger.debug(f"Analysis dir parameter: {analysis_dir}")
        self.logger.debug(f"Searching for NDI in paths: {[str(p) for p in noddi_paths]}")
        
        ndi_file = None
        for ndi_path in noddi_paths:
            self.logger.debug(f"Checking path: {ndi_path} (exists: {ndi_path.exists()})")
            if ndi_path.exists():
                ndi_file = ndi_path
                break
        
        if ndi_file is None:
            self.logger.error(f"NDI file not found in any expected location for {subject_id}")
            self.logger.error(f"Searched paths: {[str(p) for p in noddi_paths]}")
            return False
        
        # Check other required files
        missing_files = []
        for f in required_files:
            if not f.exists():
                missing_files.append(str(f))
        
        if missing_files:
            self.logger.error(f"Missing prerequisite files for {subject_id}: {missing_files}")
            return False
        
        return True
    
    def _create_ndi_weighted_mask(self, subject_id: str, analysis_dir: Path, mrtrix_dir: Path) -> Path:
        """Create NDI-weighted processing mask for SIFT2."""
        # Find NDI file from NODDI processing - BIDS format
        noddi_paths = [
            analysis_dir / "dwi" / "mdt" / "output" / f"sub-{subject_id}_brain_mask" / "NODDIDA" / "NDI.nii.gz",
            analysis_dir / "dwi" / "mdt" / "NODDIDA" / "NDI.nii.gz",
        ]
        
        ndi_file = None
        for ndi_path in noddi_paths:
            if ndi_path.exists():
                ndi_file = ndi_path
                break
        
        if ndi_file is None:
            raise FileNotFoundError(f"NDI file not found for {subject_id}")
        
        # Output mask file
        mask_file = mrtrix_dir / "ndi_5tt_mask.mif"
        
        # Get NDI threshold from configuration
        ndi_threshold = self.config.processing.sift2_ndi_threshold
        
        self.logger.info(f"Creating NDI-weighted mask with threshold {ndi_threshold}")
        
        # Create mask: NDI > threshold AND multiply by 5TT mask
        cmd = [
            "mrcalc", str(ndi_file.resolve()), str(ndi_threshold), "-gt",
            str((mrtrix_dir / "5tt_coreg_fs_ants.mif").resolve()), "-mult",
            str(mask_file.resolve()), "-force"
        ]
        
        self.run_command(cmd, cwd=mrtrix_dir)
        return mask_file
    
    def _run_sift2_filtering(self, subject_id: str, mrtrix_dir: Path, mask_file: Path) -> List[Path]:
        """Apply SIFT2 filtering to both hemispheres."""
        output_files = []
        
        # Track files and their corresponding output names
        track_configs = [
            {
                "input": "tracks_1M_BNST_L.tck",
                "hemisphere": "Left",
                "suffix": "L"
            },
            {
                "input": "tracks_1M_BNST_R.tck", 
                "hemisphere": "Right",
                "suffix": "R"
            }
        ]
        
        for config in track_configs:
            self.logger.info(f"Running SIFT2 for BNST {config['hemisphere']} hemisphere")
            
            # Input files
            track_file = mrtrix_dir / config["input"]
            fod_file = mrtrix_dir / "wmfod_norm.mif"
            
            # Output files
            sift_weights = mrtrix_dir / f"sift_1M_BNST_{config['suffix']}.txt"
            output_files.append(sift_weights)
            
            # Build tcksift2 command - NO TERM_RATIO PARAMETER
            cmd = [
                "tcksift2",
                "-proc_mask", str(mask_file.resolve()),
                "-nthreads", str(self.config.processing.n_threads),
                str(track_file.resolve()),
                str(fod_file.resolve()),
                str(sift_weights.resolve())
            ]
            
            # Add optional outputs based on configuration
            if self.config.processing.sift2_output_mu:
                mu_file = mrtrix_dir / f"sift_mu_1M_BNST_{config['suffix']}.txt"
                cmd.extend(["-out_mu", str(mu_file.resolve())])
                output_files.append(mu_file)
            
            if self.config.processing.sift2_output_coeffs:
                coeffs_file = mrtrix_dir / f"sift_coeffs_1M_BNST_{config['suffix']}.txt"
                cmd.extend(["-out_coeffs", str(coeffs_file.resolve())])
                output_files.append(coeffs_file)
            
            # Run SIFT2 without any termination ratio parameter
            self.run_command(cmd, cwd=mrtrix_dir)
        
        return output_files
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """Validate inputs before processing."""
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
        
        return self._validate_prerequisites(subject_id, analysis_dir, mrtrix_dir)
    
    def get_expected_outputs(self, subject_id: str, session_id: Optional[str] = None) -> List[Path]:
        """Get list of expected output files."""
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
        
        outputs = [
            # NDI-weighted processing mask
            mrtrix_dir / "ndi_5tt_mask.mif",
            # SIFT2 weights (always generated)
            mrtrix_dir / "sift_1M_BNST_L.txt",
            mrtrix_dir / "sift_1M_BNST_R.txt",
        ]
        
        # Optional outputs based on configuration
        if self.config.processing.sift2_output_mu:
            outputs.extend([
                mrtrix_dir / "sift_mu_1M_BNST_L.txt",
                mrtrix_dir / "sift_mu_1M_BNST_R.txt",
            ])
        
        if self.config.processing.sift2_output_coeffs:
            outputs.extend([
                mrtrix_dir / "sift_coeffs_1M_BNST_L.txt",
                mrtrix_dir / "sift_coeffs_1M_BNST_R.txt",
            ])
        
        return outputs 