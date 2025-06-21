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
import os

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class DistortionCorrector(BaseProcessor):
    """
    TopUp distortion correction processor using FSL TopUp.
    
    This processor corrects distortions caused by magnetic field inhomogeneities
    using dual phase encoding (AP/PA or LR/RL) DWI data and FSL TopUp.
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
            pe_files, pe_direction = self._find_phase_encoding_files(dwi_dir, subject_id)
            
            if not pe_files['first'] or not pe_files['second']:
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
            self.logger.info(f"Extracting B0 images from {pe_direction} data")
            b0_first, b0_second = self._extract_b0_images(pe_files, topup_dir, subject_id, pe_direction)
            outputs.extend([b0_first, b0_second])
            
            # Step 2: Merge B0 images
            self.logger.info(f"Merging {pe_direction} B0 images")
            merged_b0 = self._merge_b0_images(b0_first, b0_second, topup_dir, subject_id, pe_direction)
            outputs.append(merged_b0)
            
            # Step 3: Create acquisition parameters file
            self.logger.info("Creating acquisition parameters file")
            acq_params_file = self._create_acquisition_params(pe_files, topup_dir, pe_direction)
            outputs.append(acq_params_file)
            
            # Step 4: Run TopUp
            self.logger.info("Running FSL TopUp to estimate field inhomogeneity")
            topup_output = self._run_topup(merged_b0, acq_params_file, topup_dir, subject_id, pe_direction)
            outputs.extend(topup_output)
            
            # Step 5: Apply TopUp correction
            self.logger.info("Applying TopUp correction to DWI data")
            corrected_dwi = self._apply_topup(
                pe_files['first'], acq_params_file, topup_output[0], topup_dir, subject_id
            )
            outputs.append(corrected_dwi)
            
            metrics["files_processed"] = len(outputs)
            metrics["first_file"] = pe_files['first'].name
            metrics["second_file"] = pe_files['second'].name
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
            error_msg = f"TopUp distortion correction failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _find_phase_encoding_files(self, dwi_dir: Path, subject_id: str) -> Tuple[Dict[str, Optional[Path]], str]:
        """
        Find dual phase encoding DWI files (AP/PA or LR/RL).
        
        Args:
            dwi_dir: DWI directory path
            subject_id: Subject identifier
            
        Returns:
            Tuple of (file dictionary, phase encoding direction string)
        """
        # Define phase encoding direction pairs
        pe_pairs = {
            'AP-PA': ['AP', 'PA'],
            'LR-RL': ['LR', 'RL']
        }
        
        # Look for denoised files first, then original files
        for suffix in ['_denoised.nii.gz', '.nii.gz', '.nii']:
            for pe_direction, directions in pe_pairs.items():
                pe_files = {'first': None, 'second': None}
                found_count = 0
                
                for direction in directions:
                    pattern = f"*{subject_id}*dir-{direction}*dwi{suffix}"
                    files = list(dwi_dir.glob(pattern))
                    
                    if files:
                        if found_count == 0:
                            pe_files['first'] = files[0]
                        else:
                            pe_files['second'] = files[0]
                        found_count += 1
                        self.logger.debug(f"Found {direction} file: {files[0]}")
                
                # If we found both files for this direction pair, return them
                if pe_files['first'] and pe_files['second']:
                    self.logger.info(f"Found {pe_direction} phase encoding pair")
                    return pe_files, pe_direction
        
        # If no complete pair found, return empty dict and empty string
        return {'first': None, 'second': None}, ""
    
    def _extract_b0_images(self, pe_files: Dict[str, Path], topup_dir: Path, subject_id: str, pe_direction: str) -> Tuple[Path, Path]:
        """
        Extract B0 (first volume) from dual phase encoding DWI data.
        
        Args:
            pe_files: Dictionary with first and second file paths
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            Tuple of (B0_first_path, B0_second_path)
        """
        # Extract direction names from pe_direction
        directions = pe_direction.split('-')
        b0_first = topup_dir / f"{subject_id}_dir-{directions[0]}_dwi.nii.gz"
        b0_second = topup_dir / f"{subject_id}_dir-{directions[1]}_dwi.nii.gz"
        
        # Extract first volume (B0) from first data
        cmd_first = [
            "fslroi",
            str(pe_files['first'].resolve()),
            str(b0_first.resolve()),
            "0", "1"
        ]
        
        # Extract first volume (B0) from second data
        cmd_second = [
            "fslroi",
            str(pe_files['second'].resolve()),
            str(b0_second.resolve()),
            "0", "1"
        ]
        
        # Run commands
        for cmd, output_file in [(cmd_first, b0_first), (cmd_second, b0_second)]:
            try:
                self.logger.debug(f"Running: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                
                if not output_file.exists():
                    raise RuntimeError(f"Output file was not created: {output_file}")
                    
            except subprocess.CalledProcessError as e:
                error_msg = f"fslroi failed: {e.stderr}"
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
        
        return b0_first, b0_second
    
    def _merge_b0_images(self, b0_first: Path, b0_second: Path, topup_dir: Path, subject_id: str, pe_direction: str) -> Path:
        """
        Merge dual phase encoding B0 images for TopUp processing.
        
        Args:
            b0_first: First direction B0 image path
            b0_second: Second direction B0 image path
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            Path to merged B0 image
        """
        merged_b0 = topup_dir / f"{subject_id}_dir-{pe_direction}_dwi.nii.gz"
        
        cmd = [
            "fslmerge",
            "-t",
            str(merged_b0.resolve()),
            str(b0_first.resolve()),
            str(b0_second.resolve())
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
    
    def _create_acquisition_params(self, pe_files: Dict[str, Path], topup_dir: Path, pe_direction: str) -> Path:
        """
        Create acquisition parameters file for TopUp.
        
        Args:
            pe_files: Dictionary with first and second file paths
            topup_dir: TopUp working directory
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            Path to acquisition parameters file
        """
        acq_params_file = topup_dir / "acq_params.txt"
        
        # Try to get readout time from JSON metadata
        readout_time = self._get_readout_time(pe_files)
        
        # Create acquisition parameters based on phase encoding direction
        # Format: PhaseEncodingDirection + ReadoutTime
        if pe_direction == "AP-PA":
            # AP (0 1 0) and PA (0 -1 0) with readout time
            acq_params = [
                f"0 1 0 {readout_time}",   # AP
                f"0 -1 0 {readout_time}"   # PA
            ]
        elif pe_direction == "LR-RL":
            # LR (1 0 0) and RL (-1 0 0) with readout time
            acq_params = [
                f"1 0 0 {readout_time}",   # LR
                f"-1 0 0 {readout_time}"   # RL
            ]
        else:
            raise ValueError(f"Unsupported phase encoding direction: {pe_direction}")
        
        with open(acq_params_file, 'w') as f:
            for line in acq_params:
                f.write(line + '\n')
        
        self.logger.debug(f"Created acquisition parameters file for {pe_direction}: {acq_params_file}")
        return acq_params_file
    
    def _get_readout_time(self, pe_files: Dict[str, Path]) -> float:
        """
        Extract readout time from JSON metadata.
        
        Args:
            pe_files: Dictionary with first and second file paths
            
        Returns:
            Readout time in seconds
        """
        default_readout_time = 0.0959097  # Default from original script
        
        # Try to get from first file JSON
        for key in ['first', 'second']:
            if pe_files[key]:
                json_file = pe_files[key].parent / f"{pe_files[key].stem.replace('.nii', '')}.json"
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
    
    def _run_topup(self, merged_b0: Path, acq_params: Path, topup_dir: Path, subject_id: str, pe_direction: str) -> List[Path]:
        """
        Run FSL TopUp to estimate field inhomogeneity.
        
        Args:
            merged_b0: Merged B0 image path
            acq_params: Acquisition parameters file path
            topup_dir: TopUp working directory
            subject_id: Subject identifier
            pe_direction: Phase encoding direction string (e.g., "AP-PA", "LR-RL")
            
        Returns:
            List of TopUp output files
        """
        topup_output_base = topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup"
        
        # Find the FSL config file
        fsl_config_path = self._find_fsl_config_file()
        
        cmd = [
            "topup",
            f"--imain={merged_b0.resolve()}",
            f"--datain={acq_params.resolve()}",
            f"--config={fsl_config_path}",
            f"--out={topup_output_base.resolve()}",
            f"--nthr={self.config.processing.n_threads}"
        ]
        
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # TopUp creates several output files
            expected_outputs = [
                topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_fieldcoef.nii.gz",
                topup_dir / f"{subject_id}_dir-{pe_direction}_dwi_Topup_movpar.txt"
            ]
            
            # Check if main output exists (fieldcoef file is the key one)
            if not expected_outputs[0].exists():
                raise RuntimeError(f"TopUp output not created: {expected_outputs[0]}")
            
            return [topup_output_base]  # Return base name for applytopup
            
        except subprocess.CalledProcessError as e:
            error_msg = f"TopUp failed: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _find_fsl_config_file(self) -> str:
        """
        Find the FSL b02b0.cnf configuration file.
        
        Returns:
            Full path to the b02b0.cnf file
        """
        config_filename = self.config.processing.topup_config
        
        # Check if it's already a full path
        if Path(config_filename).is_absolute():
            return config_filename
        
        # Look for the file in common FSL locations
        possible_paths = [
            Path("/opt/fsl-6.0.7.1/pkgs/fsl-topup-2203.2-h2bc3f7f_1/etc/flirtsch/b02b0.cnf"),
            Path("/usr/local/fsl/etc/flirtsch/b02b0.cnf"),
            Path("/opt/fsl/etc/flirtsch/b02b0.cnf"),
            Path("/usr/share/fsl/etc/flirtsch/b02b0.cnf"),
        ]
        
        # Also check if FSLDIR environment variable is set
        fsl_dir = os.environ.get('FSLDIR')
        if fsl_dir:
            possible_paths.insert(0, Path(fsl_dir) / "etc" / "flirtsch" / config_filename)
        
        for path in possible_paths:
            if path.exists():
                self.logger.debug(f"Found FSL config file: {path}")
                return str(path)
        
        # If not found, return the original filename and let TopUp handle the error
        self.logger.warning(f"FSL config file not found in common locations, using: {config_filename}")
        return config_filename
    
    def _apply_topup(self, first_dwi: Path, acq_params: Path, topup_output: Path, 
                     topup_dir: Path, subject_id: str) -> Path:
        """
        Apply TopUp correction to DWI data.
        
        Args:
            first_dwi: First direction DWI file path (AP or LR)
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
            f"--imain={first_dwi.resolve()}",
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
        pe_files, _ = self._find_phase_encoding_files(dwi_dir, subject_id)
        if not pe_files['first'] or not pe_files['second']:
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