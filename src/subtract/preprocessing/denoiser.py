"""
DWI denoising processor for SubTract pipeline.

This module handles DWI denoising using MRtrix3 dwidenoise,
corresponding to Step 002 in the original pipeline.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class DWIDenoiser(BaseProcessor):
    """
    DWI denoising processor using MRtrix3 dwidenoise.
    
    This processor applies denoising to DWI data using the MRtrix3 dwidenoise
    command, which implements the method described in Veraart et al. (2016).
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the DWI denoiser.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        super().__init__(config, logger)
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Process DWI denoising for a subject.
        
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
                analysis_dir = self.config.paths.analysis_dir / subject_id
            
            dwi_dir = analysis_dir / "dwi"
            
            if not dwi_dir.exists():
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"DWI directory not found: {dwi_dir}"
                )
            
            # Find DWI files to denoise
            dwi_files = self._find_dwi_files(dwi_dir)
            
            if not dwi_files:
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"No DWI files found in {dwi_dir}"
                )
            
            outputs = []
            metrics = {"files_processed": 0, "files_skipped": 0}
            
            # Process each DWI file
            for dwi_file in dwi_files:
                try:
                    result = self._denoise_file(dwi_file)
                    if result:
                        outputs.append(result)
                        metrics["files_processed"] += 1
                        self.logger.info(f"Denoised: {dwi_file.name}")
                    else:
                        metrics["files_skipped"] += 1
                        self.logger.info(f"Skipped (already exists): {dwi_file.name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to denoise {dwi_file}: {e}")
                    # Continue with other files
            
            execution_time = time.time() - start_time
            success = metrics["files_processed"] > 0
            
            return ProcessingResult(
                success=success,
                outputs=outputs,
                metrics=metrics,
                execution_time=execution_time,
                error_message=None if success else "No files were successfully denoised"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"DWI denoising failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _find_dwi_files(self, dwi_dir: Path) -> List[Path]:
        """
        Find DWI files to denoise.
        
        Args:
            dwi_dir: DWI directory path
            
        Returns:
            List of DWI file paths
        """
        dwi_files = []
        
        # Look for .nii and .nii.gz files containing "dwi"
        for pattern in ["*.nii", "*.nii.gz"]:
            files = list(dwi_dir.glob(pattern))
            dwi_files.extend([f for f in files if "dwi" in f.name.lower() and "denoised" not in f.name.lower()])
        
        return sorted(dwi_files)
    
    def _denoise_file(self, input_file: Path) -> Optional[Path]:
        """
        Denoise a single DWI file using MRtrix3 dwidenoise.
        
        Args:
            input_file: Input DWI file path
            
        Returns:
            Output file path if successful, None if skipped
        """
        # Determine output filename
        if input_file.suffix == ".nii":
            output_file = input_file.parent / f"{input_file.stem}_denoised.nii.gz"
        else:  # .nii.gz
            stem = input_file.name.replace(".nii.gz", "")
            output_file = input_file.parent / f"{stem}_denoised.nii.gz"
        
        # Check if output already exists and we're not forcing overwrite
        if output_file.exists() and not self.config.processing.force_overwrite:
            self.logger.debug(f"Output exists, skipping: {output_file}")
            return None
        
        # Build dwidenoise command
        cmd = [
            "dwidenoise",
            str(input_file),
            str(output_file),
            "-force",
            "-nthreads", str(self.config.processing.n_threads)
        ]
        
        # Execute command
        try:
            self.logger.debug(f"Running: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=input_file.parent
            )
            
            # Log any output from dwidenoise
            if result.stdout:
                self.logger.debug(f"dwidenoise stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"dwidenoise stderr: {result.stderr}")
            
            # Verify output file was created
            if not output_file.exists():
                raise RuntimeError(f"Output file was not created: {output_file}")
            
            return output_file
            
        except subprocess.CalledProcessError as e:
            error_msg = f"dwidenoise failed for {input_file}: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during denoising {input_file}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """
        Validate that required inputs exist for denoising.
        
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
            analysis_dir = self.config.paths.analysis_dir / subject_id
        
        dwi_dir = analysis_dir / "dwi"
        
        if not dwi_dir.exists():
            self.logger.error(f"DWI directory does not exist: {dwi_dir}")
            return False
        
        # Check for DWI files
        dwi_files = self._find_dwi_files(dwi_dir)
        if not dwi_files:
            self.logger.error(f"No DWI files found in {dwi_dir}")
            return False
        
        # Check that MRtrix3 is available
        try:
            subprocess.run(
                ["dwidenoise", "--help"],
                capture_output=True,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("MRtrix3 dwidenoise command not found. Please ensure MRtrix3 is installed and in PATH.")
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
            analysis_dir = self.config.paths.analysis_dir / subject_id
        
        dwi_dir = analysis_dir / "dwi"
        
        if not dwi_dir.exists():
            return []
        
        # Find input DWI files and generate expected output names
        dwi_files = self._find_dwi_files(dwi_dir)
        expected_outputs = []
        
        for dwi_file in dwi_files:
            if dwi_file.suffix == ".nii":
                output_file = dwi_file.parent / f"{dwi_file.stem}_denoised.nii.gz"
            else:  # .nii.gz
                stem = dwi_file.name.replace(".nii.gz", "")
                output_file = dwi_file.parent / f"{stem}_denoised.nii.gz"
            
            expected_outputs.append(output_file)
        
        return expected_outputs
    
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
        
        # Check if all expected outputs exist
        return all(output.exists() for output in expected_outputs) 