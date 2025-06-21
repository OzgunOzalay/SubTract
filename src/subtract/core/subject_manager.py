"""
Subject management for SubTract pipeline.

This module handles subject discovery, validation, and tracking throughout
the pipeline processing with BIDS support.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from ..config.settings import SubtractConfig
from ..utils.bids_utils import BIDSLayout


class SubjectManager:
    """
    Manager for subject discovery and validation with BIDS support.
    
    This class handles finding subjects in BIDS datasets,
    validating their data structure, and tracking processing status.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the subject manager.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Initialize BIDS layout if data directory exists
        if self.config.paths.data_dir.exists():
            try:
                self.bids_layout = BIDSLayout(
                    self.config.paths.data_dir, 
                    self.config, 
                    self.logger
                )
                self.is_bids = True
                self.logger.info("Initialized BIDS layout")
            except Exception as e:
                self.logger.warning(f"Failed to initialize BIDS layout: {e}")
                self.bids_layout = None
                self.is_bids = False
        else:
            self.bids_layout = None
            self.is_bids = False
    
    def discover_subjects(self) -> List[str]:
        """
        Discover all subjects in the data directory.
        
        Returns:
            List of subject identifiers
        """
        if not self.config.paths.data_dir.exists():
            self.logger.error(f"Data directory does not exist: {self.config.paths.data_dir}")
            return []
        
        if self.is_bids and self.bids_layout:
            # Use BIDS layout for subject discovery
            subjects = self.bids_layout.get_subjects()
            self.logger.info(f"Discovered {len(subjects)} BIDS subjects in {self.config.paths.data_dir}")
        else:
            # Fallback to directory-based discovery
            subject_dirs = [
                d for d in self.config.paths.data_dir.iterdir() 
                if d.is_dir() and not d.name.startswith('.')
            ]
            
            subjects = [d.name for d in subject_dirs]
            
            # Apply subject filter if specified
            if self.config.subject_filter:
                pattern = re.compile(self.config.subject_filter)
                subjects = [s for s in subjects if pattern.match(s)]
            
            self.logger.info(f"Discovered {len(subjects)} subjects in {self.config.paths.data_dir}")
        
        return sorted(subjects)
    
    def get_subject_sessions(self, subject_id: str) -> List[str]:
        """
        Get sessions for a subject (BIDS only).
        
        Args:
            subject_id: Subject identifier
            
        Returns:
            List of session identifiers, empty if no sessions or not BIDS
        """
        if self.is_bids and self.bids_layout:
            return self.bids_layout.get_sessions(subject_id)
        return []
    
    def validate_subject(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate a subject's data structure and completeness.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            Dictionary with validation results
        """
        if self.is_bids and self.bids_layout:
            return self._validate_bids_subject(subject_id, session_id)
        else:
            return self._validate_legacy_subject(subject_id)
    
    def _validate_bids_subject(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate BIDS subject data."""
        validation_result = self.bids_layout.validate_subject_data(subject_id, session_id)
        
        # Convert to our standard format
        result = {
            "subject_id": subject_id,
            "session_id": session_id,
            "valid": validation_result["valid"],
            "errors": validation_result["errors"],
            "warnings": validation_result["warnings"],
            "data_summary": {
                "dwi_files": len(validation_result["dwi_files"]),
                "anat_files": len(validation_result["anat_files"]),
                "dual_phase_encoding": validation_result["has_dual_pe"],
                "bids_compliant": True
            }
        }
        
        # Add detailed file information
        result["dwi_file_details"] = validation_result["dwi_files"]
        result["anat_file_details"] = validation_result["anat_files"]
        
        # Check for bval/bvec files
        bval_count = sum(1 for dwi in validation_result["dwi_files"] if dwi["bval"])
        bvec_count = sum(1 for dwi in validation_result["dwi_files"] if dwi["bvec"])
        
        result["data_summary"]["bval_files"] = bval_count
        result["data_summary"]["bvec_files"] = bvec_count
        
        return result
    
    def _validate_legacy_subject(self, subject_id: str) -> Dict[str, Any]:
        """Validate legacy (non-BIDS) subject data."""
        validation_result = {
            "subject_id": subject_id,
            "session_id": None,
            "valid": True,
            "errors": [],
            "warnings": [],
            "data_summary": {"bids_compliant": False}
        }
        
        subject_dir = self.config.paths.data_dir / subject_id
        
        # Check if subject directory exists
        if not subject_dir.exists():
            validation_result["valid"] = False
            validation_result["errors"].append(f"Subject directory does not exist: {subject_dir}")
            return validation_result
        
        # Check for DWI subdirectory
        dwi_dir = subject_dir / "dwi"
        if not dwi_dir.exists():
            validation_result["warnings"].append("No 'dwi' subdirectory found")
            # Look for DWI files in the main subject directory
            dwi_files = self._find_dwi_files(subject_dir)
        else:
            dwi_files = self._find_dwi_files(dwi_dir)
        
        validation_result["data_summary"]["dwi_files"] = len(dwi_files)
        
        if not dwi_files:
            validation_result["valid"] = False
            validation_result["errors"].append("No DWI files found")
        else:
            # Check for bval/bvec files
            bval_files, bvec_files = self._find_bval_bvec_files(dwi_dir if dwi_dir.exists() else subject_dir)
            
            validation_result["data_summary"]["bval_files"] = len(bval_files)
            validation_result["data_summary"]["bvec_files"] = len(bvec_files)
            
            if not bval_files:
                validation_result["warnings"].append("No .bval files found")
            
            if not bvec_files:
                validation_result["warnings"].append("No .bvec files found")
            
            # Check for dual phase encoding (for TopUp)
            ap_files = [f for f in dwi_files if "AP" in f.name or "dir-AP" in f.name]
            pa_files = [f for f in dwi_files if "PA" in f.name or "dir-PA" in f.name]
            
            validation_result["data_summary"]["dual_phase_encoding"] = len(ap_files) > 0 and len(pa_files) > 0
            
            if validation_result["data_summary"]["dual_phase_encoding"]:
                validation_result["data_summary"]["ap_files"] = len(ap_files)
                validation_result["data_summary"]["pa_files"] = len(pa_files)
            
        return validation_result
    
    def get_subject_info(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive information about a subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            Dictionary with subject information
        """
        validation = self.validate_subject(subject_id, session_id)
        
        subject_info = {
            "subject_id": subject_id,
            "session_id": session_id,
            "data_dir": self._get_subject_data_dir(subject_id, session_id),
            "analysis_dir": self._get_subject_analysis_dir(subject_id, session_id),
            "validation": validation,
            "processing_status": self._get_processing_status(subject_id, session_id),
            "is_bids": self.is_bids
        }
        
        return subject_info
    
    def _get_subject_data_dir(self, subject_id: str, session_id: Optional[str] = None) -> Path:
        """Get subject data directory path."""
        if self.is_bids:
            if session_id:
                return self.config.paths.data_dir / f"sub-{subject_id}" / f"ses-{session_id}"
            else:
                return self.config.paths.data_dir / f"sub-{subject_id}"
        else:
            return self.config.paths.data_dir / subject_id
    
    def _get_subject_analysis_dir(self, subject_id: str, session_id: Optional[str] = None) -> Path:
        """Get subject analysis directory path."""
        if session_id:
            return self.config.paths.analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            return self.config.paths.analysis_dir / f"sub-{subject_id}"
    
    def _find_dwi_files(self, directory: Path) -> List[Path]:
        """Find DWI files in a directory."""
        dwi_patterns = ["*.nii", "*.nii.gz"]
        dwi_files = []
        
        for pattern in dwi_patterns:
            files = list(directory.glob(pattern))
            # Filter for files that likely contain DWI data
            dwi_files.extend([f for f in files if "dwi" in f.name.lower()])
        
        return sorted(dwi_files)
    
    def _find_bval_bvec_files(self, directory: Path) -> tuple[List[Path], List[Path]]:
        """Find bval and bvec files in a directory."""
        bval_files = list(directory.glob("*.bval"))
        bvec_files = list(directory.glob("*.bvec"))
        
        return sorted(bval_files), sorted(bvec_files)
    
    def _get_processing_status(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, bool]:
        """
        Check processing status for each pipeline step.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            Dictionary mapping step names to completion status
        """
        status = {}
        analysis_dir = self._get_subject_analysis_dir(subject_id, session_id)
        
        # Check for each step's expected outputs
        step_checks = {
            "copy_data": analysis_dir.exists(),
            "denoise": (analysis_dir / "dwi").exists() and 
                      any((analysis_dir / "dwi").glob("*denoised*")),
            "degibbs": (analysis_dir / "dwi").exists() and 
                      any((analysis_dir / "dwi").glob("*degibbs*")),
            "topup": (analysis_dir / "dwi" / "Topup").exists(),
            "eddy": (analysis_dir / "dwi" / "Eddy").exists(),
            "registration": (analysis_dir / "dwi" / "Reg").exists(),
            "mdt": (analysis_dir / "dwi" / "mdt").exists(),
            "mrtrix_prep": (analysis_dir / "dwi" / "mrtrix3").exists(),
            "tractography": (analysis_dir / "dwi" / "mrtrix3").exists() and
                           any((analysis_dir / "dwi" / "mrtrix3").glob("tracks_*")),
            "sift2": (analysis_dir / "dwi" / "mrtrix3").exists() and
                    any((analysis_dir / "dwi" / "mrtrix3").glob("sift_*")),
            "roi_registration": (analysis_dir / "dwi" / "mrtrix3" / "ROIs").exists(),
            "connectome": any((analysis_dir / "dwi" / "mrtrix3").glob("*fingerprint*")) if 
                         (analysis_dir / "dwi" / "mrtrix3").exists() else False
        }
        
        for step, completed in step_checks.items():
            status[step] = completed
        
        return status
    
    def get_subjects_summary(self, subject_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get summary statistics for subjects.
        
        Args:
            subject_ids: List of subject IDs to summarize (default: all discovered subjects)
            
        Returns:
            Dictionary with summary statistics
        """
        if subject_ids is None:
            subject_ids = self.discover_subjects()
        
        summary = {
            "total_subjects": len(subject_ids),
            "valid_subjects": 0,
            "subjects_with_dual_encoding": 0,
            "subjects_with_sessions": 0,
            "processing_status": {step: 0 for step in self.config.steps_to_run},
            "validation_errors": [],
            "validation_warnings": [],
            "is_bids": self.is_bids
        }
        
        for subject_id in subject_ids:
            # Check for sessions
            sessions = self.get_subject_sessions(subject_id)
            if sessions:
                summary["subjects_with_sessions"] += 1
                # Validate each session
                for session_id in sessions:
                    validation = self.validate_subject(subject_id, session_id)
                    self._update_summary_with_validation(summary, validation, subject_id, session_id)
            else:
                # No sessions, validate subject directly
                validation = self.validate_subject(subject_id)
                self._update_summary_with_validation(summary, validation, subject_id)
        
        return summary
    
    def _update_summary_with_validation(
        self, 
        summary: Dict[str, Any], 
        validation: Dict[str, Any], 
        subject_id: str, 
        session_id: Optional[str] = None
    ) -> None:
        """Update summary with validation results."""
        if validation["valid"]:
            summary["valid_subjects"] += 1
        
        if validation["data_summary"].get("dual_phase_encoding", False):
            summary["subjects_with_dual_encoding"] += 1
        
        summary["validation_errors"].extend(validation["errors"])
        summary["validation_warnings"].extend(validation["warnings"])
        
        # Check processing status
        status = self._get_processing_status(subject_id, session_id)
        for step, completed in status.items():
            if step in summary["processing_status"] and completed:
                summary["processing_status"][step] += 1 