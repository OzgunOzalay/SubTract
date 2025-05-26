"""
Data organization processor for SubTract pipeline.

This module handles copying and organizing data from BIDS datasets
to the analysis directory structure.
"""

import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig
from ..utils.bids_utils import BIDSLayout


class DataOrganizer(BaseProcessor):
    """
    Data organization processor for BIDS datasets.
    
    This processor copies DWI and anatomical data from BIDS structure
    to the analysis directory, organizing it for subsequent processing steps.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the data organizer.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        super().__init__(config, logger)
        
        # Initialize BIDS layout if available
        if self.config.paths.data_dir.exists():
            try:
                self.bids_layout = BIDSLayout(
                    self.config.paths.data_dir, 
                    self.config, 
                    self.logger
                )
                self.is_bids = True
            except Exception as e:
                self.logger.warning(f"Failed to initialize BIDS layout: {e}")
                self.bids_layout = None
                self.is_bids = False
        else:
            self.bids_layout = None
            self.is_bids = False
    
    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Process data organization for a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            ProcessingResult object
        """
        start_time = time.time()
        
        try:
            if self.is_bids and self.bids_layout:
                result = self._process_bids_subject(subject_id, session_id)
            else:
                result = self._process_legacy_subject(subject_id)
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Data organization failed for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=execution_time,
                error_message=error_msg
            )
    
    def _process_bids_subject(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """Process BIDS subject data organization."""
        outputs = []
        metrics = {}
        
        # Create analysis directory structure
        if session_id:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            analysis_dir = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        dwi_analysis_dir = analysis_dir / "dwi"
        anat_analysis_dir = analysis_dir / "anat"
        
        # Create directories
        dwi_analysis_dir.mkdir(parents=True, exist_ok=True)
        anat_analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Get DWI files
        dwi_files = self.bids_layout.get_dwi_files(subject_id, session_id)
        
        if not dwi_files:
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=0.0,
                error_message=f"No DWI files found for subject {subject_id}"
            )
        
        # Copy DWI files
        dwi_copied = 0
        for dwi_info in dwi_files:
            try:
                # Create descriptive filename
                entities = dwi_info['entities']
                filename_parts = [f"sub-{subject_id}"]
                
                if session_id:
                    filename_parts.append(f"ses-{session_id}")
                
                # Add other entities
                for entity in ['task', 'acq', 'dir', 'run']:
                    if entity in entities:
                        filename_parts.append(f"{entity}-{entities[entity]}")
                
                filename_parts.append("dwi")
                base_filename = "_".join(filename_parts)
                
                # Copy NIfTI file
                nii_dest = dwi_analysis_dir / f"{base_filename}.nii.gz"
                shutil.copy2(dwi_info['nii'], nii_dest)
                outputs.append(nii_dest)
                
                # Copy bval file
                if dwi_info['bval']:
                    bval_dest = dwi_analysis_dir / f"{base_filename}.bval"
                    shutil.copy2(dwi_info['bval'], bval_dest)
                    outputs.append(bval_dest)
                
                # Copy bvec file
                if dwi_info['bvec']:
                    bvec_dest = dwi_analysis_dir / f"{base_filename}.bvec"
                    shutil.copy2(dwi_info['bvec'], bvec_dest)
                    outputs.append(bvec_dest)
                
                # Copy JSON file
                if dwi_info['json']:
                    json_dest = dwi_analysis_dir / f"{base_filename}.json"
                    shutil.copy2(dwi_info['json'], json_dest)
                    outputs.append(json_dest)
                
                dwi_copied += 1
                self.logger.info(f"Copied DWI data: {dwi_info['nii'].name}")
                
            except Exception as e:
                self.logger.error(f"Failed to copy DWI file {dwi_info['nii']}: {e}")
        
        metrics['dwi_files_copied'] = dwi_copied
        
        # Get and copy anatomical files
        anat_files = self.bids_layout.get_anat_files(subject_id, session_id)
        anat_copied = 0
        
        for anat_info in anat_files:
            try:
                # Create descriptive filename
                entities = anat_info['entities']
                filename_parts = [f"sub-{subject_id}"]
                
                if session_id:
                    filename_parts.append(f"ses-{session_id}")
                
                # Add other entities
                for entity in ['acq', 'ce', 'rec', 'run']:
                    if entity in entities:
                        filename_parts.append(f"{entity}-{entities[entity]}")
                
                filename_parts.append(anat_info['suffix'])
                base_filename = "_".join(filename_parts)
                
                # Copy NIfTI file
                nii_dest = anat_analysis_dir / f"{base_filename}.nii.gz"
                shutil.copy2(anat_info['nii'], nii_dest)
                outputs.append(nii_dest)
                
                # Copy JSON file
                if anat_info['json']:
                    json_dest = anat_analysis_dir / f"{base_filename}.json"
                    shutil.copy2(anat_info['json'], json_dest)
                    outputs.append(json_dest)
                
                anat_copied += 1
                self.logger.info(f"Copied anatomical data: {anat_info['nii'].name}")
                
            except Exception as e:
                self.logger.error(f"Failed to copy anatomical file {anat_info['nii']}: {e}")
        
        metrics['anat_files_copied'] = anat_copied
        
        # Create processing log
        log_file = analysis_dir / "processing_log.txt"
        with open(log_file, 'w') as f:
            f.write(f"SubTract Pipeline Processing Log\n")
            f.write(f"Subject: {subject_id}\n")
            if session_id:
                f.write(f"Session: {session_id}\n")
            f.write(f"Data organization completed\n")
            f.write(f"DWI files copied: {dwi_copied}\n")
            f.write(f"Anatomical files copied: {anat_copied}\n")
        
        outputs.append(log_file)
        
        success = dwi_copied > 0
        
        return ProcessingResult(
            success=success,
            outputs=outputs,
            metrics=metrics,
            execution_time=0.0,  # Will be set by caller
            error_message=None if success else "No DWI files were successfully copied"
        )
    
    def _process_legacy_subject(self, subject_id: str) -> ProcessingResult:
        """Process legacy (non-BIDS) subject data organization."""
        outputs = []
        metrics = {}
        
        source_dir = self.config.paths.data_dir / subject_id
        analysis_dir = self.config.paths.analysis_dir / subject_id
        
        if not source_dir.exists():
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=0.0,
                error_message=f"Source directory does not exist: {source_dir}"
            )
        
        # Create analysis directory
        analysis_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy entire subject directory
        try:
            if analysis_dir.exists() and not self.config.processing.force_overwrite:
                # Directory exists, check if we should skip
                existing_files = list(analysis_dir.rglob("*"))
                if existing_files:
                    self.logger.info(f"Analysis directory exists for {subject_id}, skipping copy")
                    return ProcessingResult(
                        success=True,
                        outputs=[analysis_dir],
                        metrics={"files_copied": len(existing_files)},
                        execution_time=0.0,
                        error_message=None
                    )
            
            # Copy all files
            files_copied = 0
            for item in source_dir.rglob("*"):
                if item.is_file():
                    # Calculate relative path
                    rel_path = item.relative_to(source_dir)
                    dest_path = analysis_dir / rel_path
                    
                    # Create parent directories
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_path)
                    outputs.append(dest_path)
                    files_copied += 1
            
            metrics['files_copied'] = files_copied
            
            self.logger.info(f"Copied {files_copied} files for subject {subject_id}")
            
            return ProcessingResult(
                success=True,
                outputs=outputs,
                metrics=metrics,
                execution_time=0.0,  # Will be set by caller
                error_message=None
            )
            
        except Exception as e:
            error_msg = f"Failed to copy data for subject {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=0.0,
                error_message=error_msg
            )
    
    def validate_inputs(self, subject_id: str, **kwargs) -> bool:
        """
        Validate that the subject data directory exists and contains expected files.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters (unused)
            
        Returns:
            True if inputs are valid
        """
        source_dir = self.config.paths.data_dir / subject_id
        
        if not source_dir.exists():
            self.logger.error(f"Source directory does not exist: {source_dir}")
            return False
        
        if not source_dir.is_dir():
            self.logger.error(f"Source path is not a directory: {source_dir}")
            return False
        
        # Check for DWI subdirectory
        dwi_dir = source_dir / "dwi"
        if not dwi_dir.exists():
            self.logger.warning(f"DWI subdirectory not found: {dwi_dir}")
            # Don't fail validation - some datasets might have different structure
        
        # Check for at least some files
        files = list(source_dir.rglob("*"))
        if not files:
            self.logger.error(f"No files found in source directory: {source_dir}")
            return False
        
        self.logger.debug(f"Found {len(files)} files/directories in {source_dir}")
        return True
    
    def get_expected_outputs(self, subject_id: str, **kwargs) -> List[Path]:
        """
        Get list of expected output paths.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters (unused)
            
        Returns:
            List of expected output paths
        """
        dest_dir = self.config.paths.analysis_dir / subject_id
        
        # Return the main subject directory as the primary output
        # Additional files will be discovered during processing
        return [dest_dir]
    
    def get_dwi_files(self, subject_id: str) -> List[Path]:
        """
        Get list of DWI files for a subject.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            List of DWI file paths
        """
        subject_dir = self.config.paths.analysis_dir / subject_id
        dwi_dir = subject_dir / "dwi"
        
        if not dwi_dir.exists():
            return []
        
        # Look for common DWI file patterns
        dwi_patterns = ["*.nii", "*.nii.gz"]
        dwi_files = []
        
        for pattern in dwi_patterns:
            dwi_files.extend(dwi_dir.glob(pattern))
        
        # Filter for files that likely contain DWI data
        dwi_files = [f for f in dwi_files if "dwi" in f.name.lower()]
        
        return sorted(dwi_files)
    
    def get_bval_bvec_files(self, subject_id: str) -> tuple[Optional[Path], Optional[Path]]:
        """
        Get bval and bvec files for a subject.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            Tuple of (bval_file, bvec_file) or (None, None) if not found
        """
        subject_dir = self.config.paths.analysis_dir / subject_id
        dwi_dir = subject_dir / "dwi"
        
        if not dwi_dir.exists():
            return None, None
        
        # Look for bval and bvec files
        bval_files = list(dwi_dir.glob("*.bval"))
        bvec_files = list(dwi_dir.glob("*.bvec"))
        
        bval_file = bval_files[0] if bval_files else None
        bvec_file = bvec_files[0] if bvec_files else None
        
        return bval_file, bvec_file
    
    def validate_dwi_data(self, subject_id: str) -> bool:
        """
        Validate that DWI data is complete and consistent.
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            True if DWI data is valid
        """
        dwi_files = self.get_dwi_files(subject_id)
        bval_file, bvec_file = self.get_bval_bvec_files(subject_id)
        
        if not dwi_files:
            self.logger.warning(f"No DWI files found for subject {subject_id}")
            return False
        
        if not bval_file:
            self.logger.warning(f"No bval file found for subject {subject_id}")
            return False
        
        if not bvec_file:
            self.logger.warning(f"No bvec file found for subject {subject_id}")
            return False
        
        self.logger.info(f"Found {len(dwi_files)} DWI files for subject {subject_id}")
        return True 