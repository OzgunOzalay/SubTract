"""
Connectivity matrix and fingerprint generation processor.

This processor implements Step 011 of the SubTract pipeline:
1. Creates composite microstructure images from multiple diffusion metrics
2. Samples microstructure along tractography streamlines  
3. Generates connectivity fingerprints using track weights
"""

import logging
import time
from pathlib import Path
from typing import List, Optional, Dict, Any

from subtract.core.base_processor import MRtrix3Processor, ProcessingResult


class ConnectivityMatrix(MRtrix3Processor):
    """
    Processor for creating connectivity matrices and fingerprints.
    
    Combines microstructural metrics (NODDI, Ball&Stick) with tractography
    to create weighted connectivity fingerprints for BNST network analysis.
    """
    
    def __init__(self, config, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self.step_name = "connectome"
        self.step_description = "Connectivity matrix and fingerprint generation"
    
    def _check_dependencies(self) -> None:
        """Check that MRtrix3 tools are available."""
        required_tools = ["mrcalc", "tcksample", "tck2connectome"]
        for tool in required_tools:
            self.check_command_availability(tool)
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Generate connectivity matrices and fingerprints for a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Optional session identifier
            
        Returns:
            ProcessingResult with success status and outputs
        """
        start_time = time.time()
        
        try:
            # Use BIDS format for directory structure
            if session_id:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
                session_str = f" session {session_id}"
            else:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
                session_str = ""
            
            connectome_dir = analysis_dir / "dwi" / "connectome"
            mrtrix_dir = analysis_dir / "dwi" / "mrtrix3"
            
            self.logger.info(f"Starting connectome generation for subject: {subject_id}{session_str}")
            
            # Create output directory
            connectome_dir.mkdir(parents=True, exist_ok=True)
            (connectome_dir / "fingerprints").mkdir(exist_ok=True)
            
            # Validate prerequisites
            if not self._validate_prerequisites(subject_id, analysis_dir, mrtrix_dir):
                raise FileNotFoundError("Missing prerequisite files for connectome generation")
            
            outputs = []
            metrics = {}
            
            # Part 1: Create composite microstructure and sample tracks
            self.logger.info("Part 1: Creating composite microstructure and sampling tracks")
            composite_file, track_weights = self._create_composite_and_sample(
                subject_id, analysis_dir, connectome_dir, mrtrix_dir
            )
            outputs.append(composite_file)
            outputs.extend(track_weights)
            
            # Part 2: Generate connectivity fingerprints
            self.logger.info("Part 2: Generating connectivity fingerprints")
            fingerprint_files = self._generate_connectivity_fingerprints(
                subject_id, connectome_dir, mrtrix_dir, track_weights
            )
            outputs.extend(fingerprint_files)
            
            # Collect metrics
            metrics["composite_microstructure_created"] = composite_file.exists()
            metrics["hemispheres_processed"] = 2
            metrics["track_weights_generated"] = len(track_weights)
            metrics["fingerprints_generated"] = len(fingerprint_files)
            metrics["microstructure_formula"] = self._get_composite_formula_description()
            
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
            error_msg = f"Connectome generation failed for subject {subject_id}: {str(e)}"
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
        # Microstructure files from MDT processing (Step 006) - BIDS format
        mdt_dir = analysis_dir / "dwi" / "mdt" / "output" / f"{subject_id}_brain_mask"
        
        required_microstructure_files = [
            mdt_dir / "NODDIDA" / "NDI.nii.gz",
            mdt_dir / "NODDIDA" / "ODI.nii.gz", 
            mdt_dir / "BallStick_r1" / "w_stick0.w.nii.gz",
            mdt_dir / "BallStick_r1" / "w_ball.w.nii.gz",
        ]
        
        # Tractography files from Step 008
        required_tractography_files = [
            mrtrix_dir / "tracks_1M_BNST_L.tck",
            mrtrix_dir / "tracks_1M_BNST_R.tck",
        ]
        
        # ROI parcellation files from Step 010
        required_roi_files = [
            mrtrix_dir / "ROIs" / "left_bnst_network_parcellation.mif",
            mrtrix_dir / "ROIs" / "right_bnst_network_parcellation.mif",
        ]
        
        all_required_files = (
            required_microstructure_files + 
            required_tractography_files + 
            required_roi_files
        )
        
        missing_files = []
        for f in all_required_files:
            if not f.exists():
                missing_files.append(str(f))
        
        if missing_files:
            self.logger.error(f"Missing prerequisite files for {subject_id}: {missing_files}")
            return False
        
        return True
    
    def _create_composite_and_sample(
        self, 
        subject_id: str, 
        analysis_dir: Path, 
        connectome_dir: Path, 
        mrtrix_dir: Path
    ) -> tuple[Path, List[Path]]:
        """
        Create composite microstructure image and sample along tracks.
        
        Returns:
            Tuple of (composite_file, track_weights_files)
        """
        # Get microstructure input paths - BIDS format
        mdt_dir = analysis_dir / "dwi" / "mdt" / "output" / f"{subject_id}_brain_mask"
        
        ndi_file = mdt_dir / "NODDIDA" / "NDI.nii.gz"
        odi_file = mdt_dir / "NODDIDA" / "ODI.nii.gz"
        stick_file = mdt_dir / "BallStick_r1" / "w_stick0.w.nii.gz"
        ball_file = mdt_dir / "BallStick_r1" / "w_ball.w.nii.gz"
        
        # Output composite file
        composite_file = connectome_dir / "composite_microstructure.mif"
        
        self.logger.info("Creating composite microstructure image")
        
        # Create composite microstructure using tested formula
        # Formula: NDI*0.35 + (1-ODI)*0.25 + w_stick0*0.25 + (1-w_ball)*0.15
        cmd = [
            "mrcalc",
            str(ndi_file.resolve()), "0.35", "-mult",
            str(odi_file.resolve()), "-neg", "1", "-add", "0.25", "-mult", "-add",
            str(stick_file.resolve()), "0.25", "-mult", "-add", 
            str(ball_file.resolve()), "-neg", "1", "-add", "0.15", "-mult", "-add",
            str(composite_file.resolve()),
            "-force"
        ]
        
        self.run_command(cmd, cwd=connectome_dir)
        
        # Sample microstructure along tracks for both hemispheres
        track_weights = []
        hemispheres = [
            {"suffix": "L", "name": "Left"},
            {"suffix": "R", "name": "Right"}
        ]
        
        for hemi in hemispheres:
            self.logger.info(f"Sampling microstructure for {hemi['name']} hemisphere")
            
            track_file = mrtrix_dir / f"tracks_1M_BNST_{hemi['suffix']}.tck"
            weights_file = connectome_dir / f"track_weights_1M_BNST_{hemi['suffix']}.txt"
            
            cmd = [
                "tcksample",
                str(track_file.resolve()),
                str(composite_file.resolve()),
                str(weights_file.resolve()),
                "-stat_tck", "mean"
            ]
            
            self.run_command(cmd, cwd=connectome_dir)
            track_weights.append(weights_file)
        
        return composite_file, track_weights
    
    def _generate_connectivity_fingerprints(
        self, 
        subject_id: str,
        connectome_dir: Path, 
        mrtrix_dir: Path, 
        track_weights: List[Path]
    ) -> List[Path]:
        """
        Generate connectivity fingerprints for both hemispheres.
        
        Args:
            subject_id: Subject identifier
            connectome_dir: Connectome output directory
            mrtrix_dir: MRtrix3 directory with tracks and ROIs
            track_weights: List of track weight files [L, R]
            
        Returns:
            List of generated fingerprint files
        """
        fingerprint_files = []
        
        # Configuration for both hemispheres
        hemisphere_configs = [
            {
                "suffix": "L",
                "name": "Left",
                "track_file": mrtrix_dir / "tracks_1M_BNST_L.tck",
                "roi_file": mrtrix_dir / "ROIs" / "left_bnst_network_parcellation.mif",
                "weights_file": track_weights[0],  # L weights
                "output_file": connectome_dir / "fingerprints" / "L_BNST_fingerprint.csv"
            },
            {
                "suffix": "R", 
                "name": "Right",
                "track_file": mrtrix_dir / "tracks_1M_BNST_R.tck",
                "roi_file": mrtrix_dir / "ROIs" / "right_bnst_network_parcellation.mif", 
                "weights_file": track_weights[1],  # R weights
                "output_file": connectome_dir / "fingerprints" / "R_BNST_fingerprint.csv"
            }
        ]
        
        for config in hemisphere_configs:
            self.logger.info(f"Generating connectivity fingerprint for {config['name']} BNST")
            
            # Use exact command structure from tested script
            cmd = [
                "tck2connectome",
                str(config["track_file"].resolve()),
                str(config["roi_file"].resolve()),
                str(config["output_file"].resolve()),
                "-scale_invnodevol",
                "-scale_file", str(config["weights_file"].resolve()),
                "-stat_edge", "mean",
                "-vector",
                "-force"
            ]
            
            self.run_command(cmd, cwd=connectome_dir)
            fingerprint_files.append(config["output_file"])
        
        return fingerprint_files
    
    def _get_composite_formula_description(self) -> str:
        """Get description of the composite microstructure formula."""
        return "NDI*0.35 + (1-ODI)*0.25 + w_stick*0.25 + (1-w_ball)*0.15"
    
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
        
        connectome_dir = analysis_dir / "dwi" / "connectome"
        
        return [
            # Composite microstructure
            connectome_dir / "composite_microstructure.mif",
            # Track weights  
            connectome_dir / "track_weights_1M_BNST_L.txt",
            connectome_dir / "track_weights_1M_BNST_R.txt",
            # Connectivity fingerprints
            connectome_dir / "fingerprints" / "L_BNST_fingerprint.csv",
            connectome_dir / "fingerprints" / "R_BNST_fingerprint.csv",
        ] 