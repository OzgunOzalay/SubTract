"""
Eddy current correction processor for SubTract pipeline.

This module handles eddy current and motion correction using FSL Eddy,
corresponding to Step 004 in the original pipeline.
"""

import subprocess
import time
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class EddyCorrector(BaseProcessor):
    """
    Eddy current correction processor using FSL Eddy with CUDA acceleration.
    
    This processor corrects for eddy current distortions and subject motion
    in DWI data using FSL Eddy, building on outputs from TopUp.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the eddy corrector.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        super().__init__(config, logger)
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Process Eddy current correction for a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            # Get subject analysis directory
            if session_id:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
            else:
                analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
            
            dwi_dir = analysis_dir / "dwi"
            topup_dir = dwi_dir / "Topup"
            eddy_dir = dwi_dir / "Eddy"
            
            # Validate inputs
            if not topup_dir.exists():
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"TopUp directory not found: {topup_dir}. Run TopUp first."
                )
            
            # Check if output already exists and we're not forcing overwrite
            expected_output = eddy_dir / f"{subject_id}_eddy_unwarped.nii.gz"
            if expected_output.exists() and not self.config.processing.force_overwrite:
                self.logger.info(f"Eddy output already exists, skipping: {expected_output}")
                return ProcessingResult(
                    success=True,
                    outputs=[expected_output],
                    metrics={"skipped": True, "reason": "output_exists"},
                    execution_time=time.time() - start_time,
                    error_message=None
                )
            
            # Create Eddy directory
            eddy_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine phase encoding direction from TopUp outputs
            pe_direction = self._detect_phase_encoding_direction(topup_dir, subject_id)
            if not pe_direction:
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"Could not determine phase encoding direction from TopUp outputs"
                )
            
            outputs = []
            metrics = {}
            
            # Step 1: Setup Eddy directory with required files
            self.logger.info(f"Setting up Eddy directory with TopUp outputs for {pe_direction}")
            required_files = self._setup_eddy_directory(
                subject_id, dwi_dir, topup_dir, eddy_dir, pe_direction
            )
            outputs.extend(required_files)
            
            # Step 2: Extract B0 image
            self.logger.info("Extracting B0 image for brain mask")
            b0_image = self._extract_b0_image(subject_id, eddy_dir)
            outputs.append(b0_image)
            
            # Step 3: Create brain mask
            self.logger.info("Creating brain mask using BET")
            brain_mask = self._create_brain_mask(subject_id, eddy_dir, b0_image)
            outputs.append(brain_mask)
            
            # Step 4: Create index file
            self.logger.info("Creating index file for volume assignment")
            index_file = self._create_index_file(subject_id, eddy_dir)
            outputs.append(index_file)
            
            # Step 5: Run Eddy correction
            self.logger.info("Running FSL Eddy current correction with CUDA")
            eddy_outputs = self._run_eddy_correction(subject_id, eddy_dir, pe_direction)
            outputs.extend(eddy_outputs)
            
            metrics["files_processed"] = len(outputs)
            metrics["eddy_method"] = self.config.processing.eddy_method
            metrics["cuda_enabled"] = self.config.processing.eddy_cuda
            metrics["pe_direction"] = pe_direction
            
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
            error_msg = f"Eddy current correction failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _detect_phase_encoding_direction(self, topup_dir: Path, subject_id: str) -> Optional[str]:
        """
        Detect phase encoding direction from TopUp outputs.
        
        Args:
            topup_dir: TopUp directory path
            subject_id: Subject identifier
            
        Returns:
            Phase encoding direction string (e.g., "AP-PA", "LR-RL") or None if not found
        """
        # Look for TopUp field coefficient files with different phase encoding directions
        possible_directions = ["AP-PA", "LR-RL"]
        
        for direction in possible_directions:
            fieldcoef_file = topup_dir / f"{subject_id}_dir-{direction}_dwi_Topup_fieldcoef.nii.gz"
            if fieldcoef_file.exists():
                self.logger.info(f"Detected phase encoding direction: {direction}")
                return direction
        
        self.logger.error(f"Could not detect phase encoding direction from TopUp outputs")
        return None
    
    def _setup_eddy_directory(self, subject_id: str, dwi_dir: Path, 
                              topup_dir: Path, eddy_dir: Path, pe_direction: str) -> List[Path]:
        """
        Setup Eddy directory with required files from TopUp and DWI.
        
        Args:
            subject_id: Subject identifier
            dwi_dir: DWI directory path
            topup_dir: TopUp directory path
            eddy_dir: Eddy directory path
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            List of copied files
        """
        files_to_copy = [
            # From TopUp: corrected DWI data
            (topup_dir / f"{subject_id}_topup_dwi.nii.gz", 
             eddy_dir / f"{subject_id}_dwi.nii.gz"),
            
            # From TopUp: acquisition parameters
            (topup_dir / "acq_params.txt", 
             eddy_dir / "acq_params.txt"),
            
            # From TopUp: field coefficients
            (topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_fieldcoef.nii.gz",
             eddy_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_fieldcoef.nii.gz"),
            
            # From TopUp: movement parameters
            (topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_movpar.txt",
             eddy_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_movpar.txt"),
        ]
        
        # Copy bvals and bvecs from DWI directory (use first direction from pe_direction)
        first_direction = pe_direction.split('-')[0]  # AP from AP-PA, LR from LR-RL
        for suffix in ['.bval', '.bvec']:
            pattern = f"*{subject_id}*dir-{first_direction}*dwi{suffix}"
            files = list(dwi_dir.glob(pattern))
            if files:
                source_file = files[0]
                dest_file = eddy_dir / f"{subject_id}_dwi{suffix}"
                files_to_copy.append((source_file, dest_file))
            else:
                raise FileNotFoundError(f"Could not find {suffix} file for {subject_id} with direction {first_direction}")
        
        # Copy files
        copied_files = []
        for source, dest in files_to_copy:
            if not source.exists():
                raise FileNotFoundError(f"Required input file not found: {source}")
            
            shutil.copy2(source, dest)
            copied_files.append(dest)
            self.logger.debug(f"Copied: {source.name} -> {dest.name}")
        
        return copied_files
    
    def _extract_b0_image(self, subject_id: str, eddy_dir: Path) -> Path:
        """
        Extract B0 (first volume) from DWI data for brain masking.
        
        Args:
            subject_id: Subject identifier
            eddy_dir: Eddy directory path
            
        Returns:
            Path to extracted B0 image
        """
        dwi_file = eddy_dir / f"{subject_id}_dwi.nii.gz"
        b0_output = eddy_dir / f"{subject_id}_1stVol.nii.gz"
        
        cmd = [
            "fslroi",
            str(dwi_file.resolve()),
            str(b0_output.resolve()),
            "0", "1"
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not b0_output.exists():
                raise RuntimeError(f"B0 extraction failed: {b0_output}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"fslroi failed for B0 extraction: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        return b0_output
    
    def _create_brain_mask(self, subject_id: str, eddy_dir: Path, b0_image: Path) -> Path:
        """
        Create brain mask using FSL BET.
        
        Args:
            subject_id: Subject identifier
            eddy_dir: Eddy directory path
            b0_image: B0 image path
            
        Returns:
            Path to brain mask
        """
        brain_output = eddy_dir / f"{subject_id}_brain"
        mask_output = eddy_dir / f"{subject_id}_brain_mask.nii.gz"
        
        cmd = [
            "bet",
            str(b0_image.resolve()),
            str(brain_output.resolve()),
            "-m",  # Generate mask
            "-f", str(self.config.processing.bet_threshold)  # Threshold
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not mask_output.exists():
                raise RuntimeError(f"Brain mask creation failed: {mask_output}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"BET failed for brain mask creation: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        return mask_output
    
    def _create_index_file(self, subject_id: str, eddy_dir: Path) -> Path:
        """
        Create index file for Eddy (maps each volume to acquisition parameters).
        
        For single phase encoding, all volumes use index 1.
        For dual phase encoding after TopUp, all volumes use index 1.
        
        Args:
            subject_id: Subject identifier
            eddy_dir: Eddy directory path
            
        Returns:
            Path to index file
        """
        index_file = eddy_dir / "index.txt"
        
        # Get number of volumes from DWI data
        dwi_file = eddy_dir / f"{subject_id}_dwi.nii.gz"
        
        try:
            # Use fslinfo to get number of volumes
            cmd = ["fslinfo", str(dwi_file.resolve())]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Parse output to get number of volumes
            n_volumes = None
            for line in result.stdout.split('\n'):
                if 'dim4' in line:
                    n_volumes = int(line.split()[-1])
                    break
            
            if n_volumes is None:
                # Fallback: assume reasonable number of volumes
                n_volumes = 100
                self.logger.warning(f"Could not determine number of volumes, using {n_volumes}")
            
        except subprocess.CalledProcessError:
            # Fallback: assume reasonable number of volumes
            n_volumes = 100
            self.logger.warning(f"fslinfo failed, using fallback {n_volumes} volumes")
        
        # Create index file (all volumes use acquisition parameter index 1)
        with open(index_file, 'w') as f:
            for i in range(n_volumes):
                f.write("1\n")
        
        self.logger.debug(f"Created index file with {n_volumes} entries")
        return index_file
    
    def _run_eddy_correction(self, subject_id: str, eddy_dir: Path, pe_direction: str) -> List[Path]:
        """
        Run FSL Eddy current correction.
        
        Args:
            subject_id: Subject identifier
            eddy_dir: Eddy directory path
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            List of output files from Eddy
        """
        # Determine which eddy command to use
        if self.config.processing.eddy_cuda:
            eddy_cmd = self.config.processing.eddy_method
            # CUDA version doesn't use --nthr parameter
            use_nthr = False
        else:
            eddy_cmd = "eddy_openmp"
            use_nthr = True
        
        # Build eddy command
        cmd = [
            eddy_cmd,
            f"--imain={subject_id}_dwi",
            f"--mask={subject_id}_brain_mask.nii.gz",
            "--index=index.txt",
            "--acqp=acq_params.txt",
            f"--bvecs={subject_id}_dwi.bvec",
            f"--bvals={subject_id}_dwi.bval",
            f"--topup={subject_id}_dir-{pe_direction}_dwi_Topup",
            "--flm=quadratic",
            f"--out={subject_id}_eddy_unwarped",
            "--data_is_shelled"
        ]
        
        # Only add --nthr for non-CUDA versions
        if use_nthr:
            cmd.append(f"--nthr={self.config.processing.n_threads}")
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            
            # Run eddy from the eddy directory with binary output handling
            result = subprocess.run(
                cmd,
                cwd=eddy_dir,
                capture_output=True,
                check=True,
                bufsize=0  # Unbuffered output
            )
            
            # Handle output carefully - Eddy may produce binary output
            if result.stdout:
                try:
                    stdout_text = result.stdout.decode('utf-8', errors='ignore')
                    if stdout_text.strip():
                        self.logger.debug(f"Eddy stdout: {stdout_text}")
                except UnicodeDecodeError:
                    self.logger.debug("Eddy produced binary stdout (normal for FSL tools)")
            
            if result.stderr:
                try:
                    stderr_text = result.stderr.decode('utf-8', errors='ignore')
                    if stderr_text.strip():
                        self.logger.debug(f"Eddy stderr: {stderr_text}")
                except UnicodeDecodeError:
                    self.logger.debug("Eddy produced binary stderr (normal for FSL tools)")
            
            # Check for expected outputs
            expected_outputs = [
                eddy_dir / f"{subject_id}_eddy_unwarped.nii.gz",
                eddy_dir / f"{subject_id}_eddy_unwarped.eddy_rotated_bvecs",
                eddy_dir / f"{subject_id}_eddy_unwarped.eddy_movement_rms",
                eddy_dir / f"{subject_id}_eddy_unwarped.eddy_restricted_movement_rms",
                eddy_dir / f"{subject_id}_eddy_unwarped.eddy_parameters"
            ]
            
            # Check which outputs actually exist
            actual_outputs = []
            for output_file in expected_outputs:
                if output_file.exists():
                    actual_outputs.append(output_file)
                else:
                    self.logger.warning(f"Expected output not found: {output_file}")
            
            if not actual_outputs:
                raise RuntimeError("No Eddy outputs were created")
            
            # The main output must exist
            main_output = eddy_dir / f"{subject_id}_eddy_unwarped.nii.gz"
            if not main_output.exists():
                raise RuntimeError(f"Main Eddy output not created: {main_output}")
            
            return actual_outputs
            
        except subprocess.CalledProcessError as e:
            # Handle stderr carefully for error reporting
            error_stderr = ""
            if e.stderr:
                try:
                    error_stderr = e.stderr.decode('utf-8', errors='ignore')
                except UnicodeDecodeError:
                    error_stderr = "Binary error output (cannot decode)"
            
            error_msg = f"Eddy correction failed: {error_stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """
        Validate that required inputs exist for Eddy correction.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            True if inputs are valid
        """
        # Get subject analysis directory
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        dwi_dir = analysis_dir / "dwi"
        topup_dir = dwi_dir / "Topup"
        
        # Check that TopUp directory exists
        if not topup_dir.exists():
            self.logger.error(f"TopUp directory does not exist: {topup_dir}")
            return False
        
        # Detect phase encoding direction
        pe_direction = self._detect_phase_encoding_direction(topup_dir, subject_id)
        if not pe_direction:
            self.logger.error(f"Could not determine phase encoding direction from TopUp outputs")
            return False
        
        # Check for required TopUp outputs
        required_topup_files = [
            topup_dir / f"{subject_id}_topup_dwi.nii.gz",
            topup_dir / "acq_params.txt",
            topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_fieldcoef.nii.gz"
        ]
        
        for file_path in required_topup_files:
            if not file_path.exists():
                self.logger.error(f"Required TopUp file not found: {file_path}")
                return False
        
        # Check for bval/bvec files (use first direction from pe_direction)
        first_direction = pe_direction.split('-')[0]
        bval_files = list(dwi_dir.glob(f"*{subject_id}*dir-{first_direction}*dwi.bval"))
        bvec_files = list(dwi_dir.glob(f"*{subject_id}*dir-{first_direction}*dwi.bvec"))
        
        if not bval_files or not bvec_files:
            self.logger.error(f"bval/bvec files not found for {subject_id} with direction {first_direction}")
            return False
        
        # Check that FSL commands are available
        for cmd in ["fslroi", "bet", "fslinfo"]:
            try:
                subprocess.run([cmd, "--help"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.logger.error(f"FSL command not found: {cmd}")
                return False
        
        # Check that eddy command is available
        eddy_cmd = self.config.processing.eddy_method if self.config.processing.eddy_cuda else "eddy_openmp"
        try:
            subprocess.run([eddy_cmd, "--help"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error(f"Eddy command not found: {eddy_cmd}")
            return False
        
        return True
    
    def get_expected_outputs(self, subject_id: str, session_id: Optional[str] = None) -> List[Path]:
        """
        Get list of expected output paths.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            List of expected output paths
        """
        # Get subject analysis directory
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        eddy_dir = analysis_dir / "dwi" / "Eddy"
        
        return [
            eddy_dir / f"{subject_id}_eddy_unwarped.nii.gz"
        ]
    
    def should_skip(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """
        Check if processing should be skipped (outputs already exist).
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            True if processing should be skipped
        """
        if self.config.processing.force_overwrite:
            return False
        
        expected_outputs = self.get_expected_outputs(subject_id, session_id)
        
        if not expected_outputs:
            return False
        
        # Check if main output exists
        return expected_outputs[0].exists() 