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
            
            # Generate tracks for left and right hemispheres
            self.logger.info("Generating probabilistic tracks")
            track_files = self._generate_tracks(subject_id, mrtrix_dir)
            outputs.extend(track_files)
            
            metrics["track_files_generated"] = len(track_files)
            metrics["total_tracks"] = self.config.processing.n_tracks
            
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
            mrtrix_dir / "gmwmSeed_coreg_fs_ants.mif",  # GM-WM interface seed file
        ]
        
        missing_files = []
        for f in required_files:
            if not f.exists():
                missing_files.append(str(f))
        
        if missing_files:
            self.logger.error(f"Missing prerequisite files for {subject_id}: {missing_files}")
            return False
        
        return True
    
    def _generate_tracks(self, subject_id: str, mrtrix_dir: Path) -> List[Path]:
        """Generate probabilistic tracks using GM-WM interface seeding."""
        track_files = []
        
        # Convert n_tracks to a string with appropriate suffix (M for millions, K for thousands)
        n_tracks = self.config.processing.n_tracks
        if n_tracks >= 1000000:
            track_suffix = f"{n_tracks // 1000000}M"
        else:
            track_suffix = f"{n_tracks // 1000}K"
        
        # Track files for left and right hemispheres
        track_configs = [
            {"hemisphere": "Left", "suffix": "L"},
            {"hemisphere": "Right", "suffix": "R"}
        ]
        
        for config in track_configs:
            track_file = mrtrix_dir / f"tracks_{track_suffix}_BNST_{config['suffix']}.tck"
            
            self.logger.info(f"Generating tracks for {config['hemisphere']} hemisphere")
            
            # Build tckgen command with absolute paths
            act_file = mrtrix_dir / "5tt_coreg_fs_ants.mif"
            fod_file = mrtrix_dir / "wmfod_norm.mif"
            gmwm_seed_file = mrtrix_dir / "gmwmSeed_coreg_fs_ants.mif"
            
            cmd = [
                "tckgen",
                "-act", str(act_file.resolve()),  # Anatomically constrained tractography
                "-backtrack",  # Allow backtracking
                "-seed_gmwmi", str(gmwm_seed_file.resolve()),  # Seed from GM-WM interface
                "-nthreads", str(self.config.processing.n_threads),
                "-select", str(self.config.processing.n_tracks),  # Number of tracks from config
                "-cutoff", str(self.config.processing.track_cutoff),  # FOD amplitude cutoff
                "-force",
                str(fod_file.resolve()),  # Input FOD
                str(track_file.resolve())  # Output track file
            ]
            
            self.run_command(cmd, cwd=mrtrix_dir)
            track_files.append(track_file)
        
        return track_files
    
    def _get_expected_track_files(self, mrtrix_dir: Path) -> List[Path]:
        """Get list of expected track files."""
        # Convert n_tracks to a string with appropriate suffix (M for millions, K for thousands)
        n_tracks = self.config.processing.n_tracks
        if n_tracks >= 1000000:
            track_suffix = f"{n_tracks // 1000000}M"
        else:
            track_suffix = f"{n_tracks // 1000}K"
            
        return [
            mrtrix_dir / f"tracks_{track_suffix}_BNST_L.tck",
            mrtrix_dir / f"tracks_{track_suffix}_BNST_R.tck"
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
            # Track files
            mrtrix_dir / "tracks_1M_BNST_L.tck",
            mrtrix_dir / "tracks_1M_BNST_R.tck"
        ] 