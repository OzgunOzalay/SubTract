"""
Gibbs ringing removal processor for SubTract pipeline.

This module handles Gibbs ringing removal using MRtrix3 mrdegibbs,
which should run after DWI denoising.
"""

import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class GibbsRemover(BaseProcessor):
    """
    Gibbs ringing removal processor using MRtrix3 mrdegibbs.
    
    This processor removes Gibbs ringing artifacts from DWI data using the
    method of local subvoxel-shifts proposed by Kellner et al.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the Gibbs remover.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        super().__init__(config, logger)
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Process Gibbs ringing removal for a subject.
        
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
            
            if not dwi_dir.exists():
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"DWI directory not found: {dwi_dir}"
                )
            
            # Find denoised DWI files to process
            dwi_files = self._find_denoised_dwi_files(dwi_dir)
            
            if not dwi_files:
                return ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=time.time() - start_time,
                    error_message=f"No denoised DWI files found in {dwi_dir}"
                )
            
            outputs = []
            metrics = {"files_processed": 0, "files_skipped": 0}
            
            # Process each denoised DWI file
            for dwi_file in dwi_files:
                try:
                    result = self._remove_gibbs(dwi_file)
                    if result:
                        outputs.append(result)
                        metrics["files_processed"] += 1
                        self.logger.info(f"Removed Gibbs ringing: {dwi_file.name}")
                    else:
                        metrics["files_skipped"] += 1
                        self.logger.info(f"Skipped (already exists): {dwi_file.name}")
                        
                except Exception as e:
                    self.logger.error(f"Failed to remove Gibbs ringing from {dwi_file}: {e}")
                    # Continue with other files
            
            execution_time = time.time() - start_time
            # Success if we processed files OR skipped files (outputs already exist)
            total_files_handled = metrics["files_processed"] + metrics["files_skipped"]
            success = total_files_handled > 0
            
            # Add skipped files to outputs (they already exist)
            if metrics["files_skipped"] > 0:
                dwi_files = self._find_denoised_dwi_files(dwi_dir)
                for dwi_file in dwi_files:
                    expected_output = self._get_expected_output_path(dwi_file)
                    if expected_output.exists() and expected_output not in outputs:
                        outputs.append(expected_output)
            
            return ProcessingResult(
                success=success,
                outputs=outputs,
                metrics=metrics,
                execution_time=execution_time,
                error_message=None if success else "No denoised DWI files found to process"
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Gibbs ringing removal failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _find_denoised_dwi_files(self, dwi_dir: Path) -> List[Path]:
        """
        Find denoised DWI files to process.
        
        Args:
            dwi_dir: DWI directory path
            
        Returns:
            List of denoised DWI file paths
        """
        dwi_files = []
        
        # Look for denoised .nii.gz files
        files = list(dwi_dir.glob("*.nii.gz"))
        dwi_files = [f for f in files if "denoised" in f.name.lower() and "degibbs" not in f.name.lower()]
        
        return sorted(dwi_files)
    
    def _get_expected_output_path(self, input_file: Path) -> Path:
        """
        Get the expected output path for a given input file.
        
        Args:
            input_file: Input denoised DWI file path
            
        Returns:
            Expected output file path
        """
        stem = input_file.name.replace(".nii.gz", "")
        return input_file.parent / f"{stem}_degibbs.nii.gz"
    
    def _remove_gibbs(self, input_file: Path) -> Optional[Path]:
        """
        Remove Gibbs ringing from a single DWI file using MRtrix3 mrdegibbs.
        
        Args:
            input_file: Input denoised DWI file path
            
        Returns:
            Output file path if successful, None if skipped
        """
        # Determine output filename
        output_file = self._get_expected_output_path(input_file)
        
        # Check if output already exists and we're not forcing overwrite
        if output_file.exists() and not self.config.processing.force_overwrite:
            self.logger.debug(f"Output exists, skipping: {output_file}")
            return None
        
        # Build mrdegibbs command with absolute paths
        cmd = [
            "mrdegibbs",
            str(input_file.resolve()),
            str(output_file.resolve()),
            "-force",
            "-nthreads", str(self.config.processing.n_threads)
        ]
        
        # Execute command
        try:
            result = self.run_command(cmd)
            
            # Log any output from mrdegibbs
            if result.stdout:
                self.logger.debug(f"mrdegibbs stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"mrdegibbs stderr: {result.stderr}")
            
            # Verify output file was created
            if not output_file.exists():
                raise RuntimeError(f"Output file was not created: {output_file}")
            
            return output_file
            
        except subprocess.CalledProcessError as e:
            error_msg = f"mrdegibbs failed for {input_file}: {e.stderr}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        except Exception as e:
            error_msg = f"Unexpected error during Gibbs removal {input_file}: {str(e)}"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """
        Validate that required inputs exist for Gibbs ringing removal.
        
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
        
        # Check for denoised DWI files
        dwi_files = self._find_denoised_dwi_files(dwi_dir)
        if not dwi_files:
            self.logger.error(f"No denoised DWI files found in {dwi_dir}")
            return False
        
        # Check that MRtrix3 is available
        try:
            self.run_command(["mrdegibbs", "--help"])
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.error("MRtrix3 mrdegibbs command not found. Please ensure MRtrix3 is installed and in PATH.")
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
        
        dwi_dir = analysis_dir / "dwi"
        
        if not dwi_dir.exists():
            return []
        
        # Find input denoised DWI files and generate expected output names
        dwi_files = self._find_denoised_dwi_files(dwi_dir)
        expected_outputs = []
        
        for dwi_file in dwi_files:
            stem = dwi_file.name.replace(".nii.gz", "")
            output_file = dwi_file.parent / f"{stem}_degibbs.nii.gz"
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