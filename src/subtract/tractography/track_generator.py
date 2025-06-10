"""
Track generation processor for SubTract pipeline.

This module implements Step 008: Tractography using MRtrix3 tckgen.
It handles ROI transformation from fsaverage space to diffusion space and
generates probabilistic white matter tracks using BNST seeds.
"""

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from subtract.core.base_processor import MRtrix3Processor, ProcessingResult


class TrackGenerator(MRtrix3Processor):
    """
    Track generation processor for probabilistic tractography.
    
    This processor implements Step 008 of the SubTract pipeline:
    1. Transform BNST ROIs from fsaverage space to diffusion space
    2. Convert ROIs to MIF format
    3. Generate probabilistic tracks using tckgen with ACT and backtracking
    """
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        """Initialize track generator."""
        super().__init__(config, logger)
        self.step_name = "tractography"
        self._check_dependencies()
    
    def _check_dependencies(self) -> None:
        """Check if required dependencies are available."""
        required_commands = [
            "mrtransform", "mrconvert", "tckgen"
        ]
        
        missing_commands = []
        for cmd in required_commands:
            try:
                subprocess.run([cmd, "--help"], capture_output=True, timeout=5)
            except (subprocess.TimeoutExpired, FileNotFoundError):
                missing_commands.append(cmd)
        
        if missing_commands:
            self.logger.warning(f"Missing commands: {missing_commands}")
            self.logger.warning("Tractography step may fail")
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Generate probabilistic tracks for a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            ProcessingResult object
        """
        import time
        start_time = time.time()
        
        try:
            # Get subject analysis directory
            if session_id:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
            else:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
            
            dwi_dir = analysis_dir / "dwi"
            mrtrix_dir = dwi_dir / "mrtrix3"
            
            # Validate inputs from previous steps
            if not self._validate_prerequisites(subject_id, mrtrix_dir):
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"Prerequisites not met for subject {subject_id}"
                )
            
            # Check if outputs already exist
            expected_outputs = self._get_expected_track_files(mrtrix_dir)
            if all(f.exists() for f in expected_outputs) and not self.config.processing.force_overwrite:
                self.logger.info(f"Track files already exist for {subject_id}, skipping")
                return ProcessingResult(
                    success=True,
                    outputs=expected_outputs,
                    metrics={"skipped": True, "reason": "outputs_exist"},
                    execution_time=time.time() - start_time,
                    error_message=None
                )
            
            outputs = []
            metrics = {}
            
            # Step 1: Transform BNST ROIs from fsaverage to diffusion space
            self.logger.info("Step 1: Transforming BNST ROIs from fsaverage to diffusion space")
            roi_files = self._transform_bnst_rois(subject_id, mrtrix_dir)
            outputs.extend(roi_files)
            
            # Step 2: Convert ROIs to MIF format
            self.logger.info("Step 2: Converting ROIs to MIF format")
            mif_roi_files = self._convert_rois_to_mif(subject_id, mrtrix_dir, roi_files)
            outputs.extend(mif_roi_files)
            
            # Step 3: Generate tracks for left and right BNST
            self.logger.info("Step 3: Generating probabilistic tracks")
            track_files = self._generate_tracks(subject_id, mrtrix_dir, mif_roi_files)
            outputs.extend(track_files)
            
            metrics["roi_files_transformed"] = len(roi_files)
            metrics["track_files_generated"] = len(track_files)
            metrics["total_tracks_per_roi"] = self.config.processing.n_tracks
            
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
            error_msg = f"Tractography failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _validate_prerequisites(self, subject_id: str, mrtrix_dir: Path) -> bool:
        """Validate that all prerequisite files exist."""
        required_files = [
            mrtrix_dir / "wmfod_norm.mif",  # From step 007
            mrtrix_dir / "5tt_coreg_fs_ants.mif",  # From step 007
            mrtrix_dir / "fs2diff_mrtrix.txt",  # From step 007 ANTs registration
        ]
        
        # Check for BNST ROI files in the project ROIs directory
        roi_dir = self.config.paths.base_path / "ROIs"
        bnst_roi_files = [
            roi_dir / "L_bnst_fsaverage.nii.gz",
            roi_dir / "R_bnst_fsaverage.nii.gz"
        ]
        
        missing_files = []
        for f in required_files + bnst_roi_files:
            if not f.exists():
                missing_files.append(str(f))
        
        if missing_files:
            self.logger.error(f"Missing prerequisite files for {subject_id}: {missing_files}")
            return False
        
        return True
    
    def _transform_bnst_rois(self, subject_id: str, mrtrix_dir: Path) -> List[Path]:
        """Transform BNST ROIs from fsaverage space to diffusion space."""
        roi_dir = self.config.paths.base_path / "ROIs"
        transformed_rois = []
        
        # ROI files to transform
        roi_files = [
            ("L_bnst_fsaverage.nii.gz", "L_bnst_DWI.nii.gz"),
            ("R_bnst_fsaverage.nii.gz", "R_bnst_DWI.nii.gz")
        ]
        
        for source_name, target_name in roi_files:
            source_file = roi_dir / source_name
            target_file = mrtrix_dir / target_name
            
            self.logger.info(f"Transforming {source_name} to diffusion space")
            
            # Use mrtransform to apply the fsaverage -> diffusion transformation
            cmd = [
                "mrtransform", str(source_file),
                "--template", str(mrtrix_dir / "mean_b0_brain.mif"),
                "-linear", str(mrtrix_dir / "fs2diff_mrtrix.txt"),
                "-interp", "nearest",  # Nearest neighbor for binary masks
                str(target_file),
                "-force"
            ]
            
            self.run_command(cmd, cwd=mrtrix_dir)
            transformed_rois.append(target_file)
        
        return transformed_rois
    
    def _convert_rois_to_mif(self, subject_id: str, mrtrix_dir: Path, roi_files: List[Path]) -> List[Path]:
        """Convert transformed ROI files to MIF format."""
        mif_files = []
        
        for roi_file in roi_files:
            mif_file = roi_file.with_suffix('.mif')
            
            self.logger.info(f"Converting {roi_file.name} to MIF format")
            
            cmd = [
                "mrconvert", str(roi_file), str(mif_file), "-force"
            ]
            
            self.run_command(cmd, cwd=mrtrix_dir)
            mif_files.append(mif_file)
        
        return mif_files
    
    def _generate_tracks(self, subject_id: str, mrtrix_dir: Path, roi_files: List[Path]) -> List[Path]:
        """Generate probabilistic tracks from BNST ROIs."""
        track_files = []
        
        # Map ROI files to track files
        roi_to_track = {
            "L_bnst_DWI.mif": "tracks_5M_BNST_L.tck",
            "R_bnst_DWI.mif": "tracks_5M_BNST_R.tck"
        }
        
        for roi_file in roi_files:
            roi_name = roi_file.name
            
            if roi_name not in roi_to_track:
                self.logger.warning(f"Unknown ROI file: {roi_name}, skipping")
                continue
            
            track_file = mrtrix_dir / roi_to_track[roi_name]
            hemisphere = "Left" if "L_bnst" in roi_name else "Right"
            
            self.logger.info(f"Generating tracks from BNST {hemisphere} for {subject_id}")
            
            # Build tckgen command
            cmd = [
                "tckgen",
                "-act", "5tt_coreg_fs_ants.mif",  # Anatomically constrained tractography
                "-backtrack",  # Allow backtracking
                "-seed_image", str(roi_file),  # Seed from BNST ROI
                "-nthreads", str(self.config.processing.n_threads),
                "-select", str(self.config.processing.n_tracks),  # Number of tracks to generate
                "-force",
                "wmfod_norm.mif",  # Input FOD
                str(track_file)  # Output track file
            ]
            
            self.run_command(cmd, cwd=mrtrix_dir)
            track_files.append(track_file)
        
        return track_files
    
    def _get_expected_track_files(self, mrtrix_dir: Path) -> List[Path]:
        """Get list of expected track files."""
        return [
            mrtrix_dir / "tracks_5M_BNST_L.tck",
            mrtrix_dir / "tracks_5M_BNST_R.tck"
        ]
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """Validate inputs before processing."""
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
        
        return self._validate_prerequisites(subject_id, mrtrix_dir)
    
    def get_expected_outputs(self, subject_id: str, session_id: Optional[str] = None) -> List[Path]:
        """Get list of expected output files."""
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
        
        # All expected outputs
        return [
            # Transformed ROIs
            mrtrix_dir / "L_bnst_DWI.nii.gz",
            mrtrix_dir / "R_bnst_DWI.nii.gz",
            # MIF ROIs
            mrtrix_dir / "L_bnst_DWI.mif",
            mrtrix_dir / "R_bnst_DWI.mif",
            # Track files
            mrtrix_dir / "tracks_5M_BNST_L.tck",
            mrtrix_dir / "tracks_5M_BNST_R.tck"
        ] 