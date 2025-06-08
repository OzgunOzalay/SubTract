"""
TopUp distortion correction processor for SubTract pipeline.

This module handles distortion correction using FSL TopUp,
corresponding to Step 003 in the original pipeline.
"""

import subprocess
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class DistortionCorrector(BaseProcessor):
    """
    TopUp distortion correction processor using FSL TopUp.
    
    This processor corrects distortions caused by magnetic field inhomogeneities
    using dual phase encoding (AP/PA) DWI data and FSL TopUp.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the distortion corrector.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        super().__init__(config, logger)
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Process TopUp distortion correction for a subject.
        
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
            
            if not dwi_dir.exists():
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"DWI directory not found: {dwi_dir}"
                )
            
            # Create TopUp directory
            topup_dir.mkdir(parents=True, exist_ok=True)
            
            # Find dual phase encoding DWI files
            pe_files = self._find_phase_encoding_files(dwi_dir, subject_id)
            
            if not pe_files['ap'] or not pe_files['pa']:
                self.logger.warning(f"Subject {subject_id} does not have dual phase encoding data, skipping TopUp")
                return ProcessingResult(
                    success=True,
                    outputs=[],
                    metrics={"skipped": True, "reason": "no_dual_pe"},
                    execution_time=time.time() - start_time,
                    error_message=None
                )
            
            # Check if output already exists and we're not forcing overwrite
            expected_output = topup_dir / f"{subject_id}_topup_dwi.nii.gz"
            if expected_output.exists() and not self.config.processing.force_overwrite:
                self.logger.info(f"TopUp output already exists, skipping: {expected_output}")
                return ProcessingResult(
                    success=True,
                    outputs=[expected_output],
                    metrics={"skipped": True, "reason": "output_exists"},
                    execution_time=time.time() - start_time,
                    error_message=None
                )
            
            outputs = []
            metrics = {}
            
            # Step 1: Extract B0 images
            self.logger.info("Extracting B0 images from AP and PA data")
            b0_ap, b0_pa = self._extract_b0_images(pe_files, topup_dir, subject_id)
            outputs.extend([b0_ap, b0_pa])
            
            # Step 2: Merge B0 images
            self.logger.info("Merging AP and PA B0 images")
            merged_b0 = self._merge_b0_images(b0_ap, b0_pa, topup_dir, subject_id)
            outputs.append(merged_b0)
            
            # Step 3: Create acquisition parameters file
            self.logger.info("Creating acquisition parameters file")
            acq_params_file = self._create_acquisition_params(pe_files, topup_dir)
            outputs.append(acq_params_file)
            
            # Step 4: Run TopUp
            self.logger.info("Running FSL TopUp to estimate field inhomogeneity")
            topup_output = self._run_topup(merged_b0, acq_params_file, topup_dir, subject_id)
            outputs.extend(topup_output)
            
            # Step 5: Apply TopUp correction
            self.logger.info("Applying TopUp correction to DWI data")
            corrected_dwi = self._apply_topup(
                pe_files['ap'], acq_params_file, topup_output[0], topup_dir, subject_id
            )
            outputs.append(corrected_dwi)
            
            metrics["files_processed"] = len(outputs)
            metrics["ap_file"] = pe_files['ap'].name
            metrics["pa_file"] = pe_files['pa'].name
            
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
            error_msg = f"TopUp distortion correction failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _find_phase_encoding_files(self, dwi_dir: Path, subject_id: str) -> Dict[str, Optional[Path]]:
        """
        Find AP and PA phase encoding DWI files.
        
        Args:
            dwi_dir: DWI directory path
            subject_id: Subject identifier
            
        Returns:
            Dictionary with 'ap' and 'pa' file paths
        """
        pe_files = {'ap': None, 'pa': None}
        
        # Look for denoised files first, then original files
        for suffix in ['_denoised.nii.gz', '.nii.gz', '.nii']:
            for direction in ['AP', 'PA']:
                pattern = f"*{subject_id}*dir-{direction}*dwi{suffix}"
                files = list(dwi_dir.glob(pattern))
                
                if files:
                    pe_files[direction.lower()] = files[0]
                    self.logger.debug(f"Found {direction} file: {files[0]}")
        
        return pe_files
    
    def _extract_b0_images(self, pe_files: Dict[str, Path], topup_dir: Path, subject_id: str) -> Tuple[Path, Path]:
        """
        Extract B0 (first volume) from AP and PA DWI data.
        
        Args:
            pe_files: Dictionary with AP and PA file paths
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            
        Returns:
            Tuple of (B0_AP_path, B0_PA_path)
        """
        b0_ap = topup_dir / f"{subject_id}_dir-AP_dwi.nii.gz"
        b0_pa = topup_dir / f"{subject_id}_dir-PA_dwi.nii.gz"
        
        # Extract first volume (B0) from AP data
        cmd_ap = [
            "fslroi",
            str(pe_files['ap'].resolve()),
            str(b0_ap.resolve()),
            "0", "1"
        ]
        
        # Extract first volume (B0) from PA data
        cmd_pa = [
            "fslroi",
            str(pe_files['pa'].resolve()),
            str(b0_pa.resolve()),
            "0", "1"
        ]
        
        # Run commands
        for cmd, output_file in [(cmd_ap, b0_ap), (cmd_pa, b0_pa)]:
            try:
                self.logger.debug(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                if not output_file.exists():
                    raise RuntimeError(f"Output file was not created: {output_file}")
                    
            except subprocess.CalledProcessError as e:
                error_msg = f"fslroi failed: {e.stderr}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        return b0_ap, b0_pa
    
    def _merge_b0_images(self, b0_ap: Path, b0_pa: Path, topup_dir: Path, subject_id: str) -> Path:
        """
        Merge AP and PA B0 images for TopUp processing.
        
        Args:
            b0_ap: AP B0 image path
            b0_pa: PA B0 image path
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            
        Returns:
            Path to merged B0 image
        """
        merged_b0 = topup_dir / f"{subject_id}_dir-AP-PA_dwi.nii.gz"
        
        cmd = [
            "fslmerge",
            "-t",
            str(merged_b0.resolve()),
            str(b0_ap.resolve()),
            str(b0_pa.resolve())
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not merged_b0.exists():
                raise RuntimeError(f"Merged B0 file was not created: {merged_b0}")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"fslmerge failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        return merged_b0
    
    def _create_acquisition_params(self, pe_files: Dict[str, Path], topup_dir: Path) -> Path:
        """
        Create acquisition parameters file for TopUp.
        
        Args:
            pe_files: Dictionary with AP and PA file paths
            topup_dir: TopUp working directory
            
        Returns:
            Path to acquisition parameters file
        """
        acq_params_file = topup_dir / "acq_params.txt"
        
        # Try to get readout time from JSON metadata
        readout_time = self._get_readout_time(pe_files)
        
        # Create acquisition parameters
        # Format: PhaseEncodingDirection + ReadoutTime
        # AP (0 1 0) and PA (0 -1 0) with readout time
        acq_params = [
            f"0 1 0 {readout_time}",   # AP
            f"0 -1 0 {readout_time}"   # PA
        ]
        
        with open(acq_params_file, 'w') as f:
            for line in acq_params:
                f.write(line + '\n')
        
        self.logger.debug(f"Created acquisition parameters file: {acq_params_file}")
        return acq_params_file
    
    def _get_readout_time(self, pe_files: Dict[str, Path]) -> float:
        """
        Extract readout time from JSON metadata.
        
        Args:
            pe_files: Dictionary with AP and PA file paths
            
        Returns:
            Readout time in seconds
        """
        default_readout_time = 0.0959097  # Default from original script
        
        # Try to get from AP file JSON
        for direction in ['ap', 'pa']:
            if pe_files[direction]:
                json_file = pe_files[direction].parent / f"{pe_files[direction].stem.replace('.nii', '')}.json"
                if json_file.exists():
                    try:
                        with open(json_file, 'r') as f:
                            metadata = json.load(f)
                        
                        # Calculate readout time from metadata
                        if 'TotalReadoutTime' in metadata:
                            return metadata['TotalReadoutTime']
                        elif 'EffectiveEchoSpacing' in metadata and 'ReconMatrixPE' in metadata:
                            # Calculate: (ReconMatrixPE - 1) * EffectiveEchoSpacing
                            readout_time = (metadata['ReconMatrixPE'] - 1) * metadata['EffectiveEchoSpacing']
                            return readout_time
                            
                    except (json.JSONDecodeError, KeyError) as e:
                        self.logger.warning(f"Could not read readout time from {json_file}: {e}")
        
        self.logger.warning(f"Using default readout time: {default_readout_time}")
        return default_readout_time
    
    def _run_topup(self, merged_b0: Path, acq_params: Path, topup_dir: Path, subject_id: str) -> List[Path]:
        """
        Run FSL TopUp to estimate field inhomogeneity.
        
        Args:
            merged_b0: Merged B0 image path
            acq_params: Acquisition parameters file path
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            
        Returns:
            List of TopUp output files
        """
        topup_output_base = topup_dir / f"{subject_id}_dir-AP-PA_dwi_Topup"
        
        cmd = [
            "topup",
            f"--imain={merged_b0.resolve()}",
            f"--datain={acq_params.resolve()}",
            f"--config={self.config.processing.topup_config}",
            f"--out={topup_output_base.resolve()}",
            f"--nthr={self.config.processing.n_threads}"
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # TopUp creates several output files
            expected_outputs = [
                topup_dir / f"{subject_id}_dir-AP-PA_dwi_Topup_fieldcoef.nii.gz",
                topup_dir / f"{subject_id}_dir-AP-PA_dwi_Topup_movpar.txt"
            ]
            
            # Check if main output exists (fieldcoef file is the key one)
            if not expected_outputs[0].exists():
                raise RuntimeError(f"TopUp output not created: {expected_outputs[0]}")
            
            return [topup_output_base]  # Return base name for applytopup
            
        except subprocess.CalledProcessError as e:
            error_msg = f"TopUp failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _apply_topup(self, ap_dwi: Path, acq_params: Path, topup_output: Path, 
                     topup_dir: Path, subject_id: str) -> Path:
        """
        Apply TopUp correction to DWI data.
        
        Args:
            ap_dwi: AP DWI file path
            acq_params: Acquisition parameters file path
            topup_output: TopUp output base path
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            
        Returns:
            Path to corrected DWI file
        """
        corrected_dwi = topup_dir / f"{subject_id}_topup_dwi.nii.gz"
        
        cmd = [
            "applytopup",
            f"--imain={ap_dwi.resolve()}",
            "--inindex=1",
            f"--datain={acq_params.resolve()}",
            f"--topup={topup_output.resolve()}",
            "--method=jac",
            f"--out={corrected_dwi.resolve()}"
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not corrected_dwi.exists():
                raise RuntimeError(f"Corrected DWI file was not created: {corrected_dwi}")
            
            return corrected_dwi
            
        except subprocess.CalledProcessError as e:
            error_msg = f"applytopup failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """
        Validate that required inputs exist for TopUp correction.
        
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
        
        if not dwi_dir.exists():
            self.logger.error(f"DWI directory does not exist: {dwi_dir}")
            return False
        
        # Check for dual phase encoding files
        pe_files = self._find_phase_encoding_files(dwi_dir, subject_id)
        if not pe_files['ap'] or not pe_files['pa']:
            self.logger.warning(f"Subject {subject_id} does not have dual phase encoding data")
            return True  # This is valid, but TopUp will be skipped
        
        # Check that FSL is available
        for cmd in ["fslroi", "fslmerge", "topup", "applytopup"]:
            try:
                subprocess.run([cmd, "--help"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.logger.error(f"FSL command not found: {cmd}. Please ensure FSL is installed and in PATH.")
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
        
        topup_dir = analysis_dir / "dwi" / "Topup"
        
        return [
            topup_dir / f"{subject_id}_topup_dwi.nii.gz"
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