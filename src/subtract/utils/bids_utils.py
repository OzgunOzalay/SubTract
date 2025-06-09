"""
BIDS utilities for SubTract pipeline.

This module provides utilities for working with BIDS-structured datasets,
including subject discovery, file finding, and metadata extraction.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging
import re

from ..config.settings import SubtractConfig


class BIDSLayout:
    """
    Simple BIDS layout handler for SubTract pipeline.
    
    This class provides basic BIDS functionality without requiring pybids,
    focusing on DWI data discovery and organization.
    """
    
    def __init__(self, bids_root: Path, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize BIDS layout.
        
        Args:
            bids_root: Path to BIDS dataset root
            config: Pipeline configuration
            logger: Logger instance
        """
        self.bids_root = Path(bids_root)
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Validate BIDS root
        if not self.bids_root.exists():
            raise FileNotFoundError(f"BIDS root does not exist: {self.bids_root}")
        
        # Check for dataset_description.json
        dataset_desc = self.bids_root / "dataset_description.json"
        if not dataset_desc.exists():
            self.logger.warning(f"No dataset_description.json found in {self.bids_root}")
    
    def get_subjects(self) -> List[str]:
        """
        Get list of subjects in the BIDS dataset.
        
        Returns:
            List of subject IDs (without 'sub-' prefix)
        """
        subject_dirs = [
            d for d in self.bids_root.iterdir()
            if d.is_dir() and d.name.startswith('sub-')
        ]
        
        subjects = [d.name[4:] for d in subject_dirs]  # Remove 'sub-' prefix
        
        # Apply subject filter if specified
        if self.config.subject_filter:
            pattern = re.compile(self.config.subject_filter)
            subjects = [s for s in subjects if pattern.match(s)]
        
        return sorted(subjects)
    
    def get_sessions(self, subject: str) -> List[str]:
        """
        Get list of sessions for a subject.
        
        Args:
            subject: Subject ID (without 'sub-' prefix)
            
        Returns:
            List of session IDs (without 'ses-' prefix), empty if no sessions
        """
        subject_dir = self.bids_root / f"sub-{subject}"
        
        if not subject_dir.exists():
            return []
        
        session_dirs = [
            d for d in subject_dir.iterdir()
            if d.is_dir() and d.name.startswith('ses-')
        ]
        
        sessions = [d.name[4:] for d in session_dirs]  # Remove 'ses-' prefix
        
        # Apply session filter if specified
        if self.config.bids.sessions:
            sessions = [s for s in sessions if s in self.config.bids.sessions]
        
        return sorted(sessions)
    
    def get_dwi_files(self, subject: str, session: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get DWI files for a subject/session.
        
        Args:
            subject: Subject ID (without 'sub-' prefix)
            session: Session ID (without 'ses-' prefix), optional
            
        Returns:
            List of dictionaries containing DWI file information
        """
        if session:
            dwi_dir = self.bids_root / f"sub-{subject}" / f"ses-{session}" / "dwi"
        else:
            dwi_dir = self.bids_root / f"sub-{subject}" / "dwi"
        
        if not dwi_dir.exists():
            return []
        
        dwi_files = []
        
        # Find all DWI NIfTI files (both .nii.gz and .nii)
        for suffix in self.config.bids.dwi_suffixes:
            # Try both .nii.gz and .nii extensions
            for ext in ['.nii.gz', '.nii']:
                pattern = f"*_{suffix}{ext}"
                nii_files = list(dwi_dir.glob(pattern))
            
            for nii_file in nii_files:
                # Extract BIDS entities from filename
                entities = self._parse_bids_filename(nii_file.name)
                
                # Find associated files
                base_name = nii_file.name.replace(ext, '')
                
                bval_file = dwi_dir / f"{base_name}.bval"
                bvec_file = dwi_dir / f"{base_name}.bvec"
                json_file = dwi_dir / f"{base_name}.json"
                
                dwi_info = {
                    'nii': nii_file,
                    'bval': bval_file if bval_file.exists() else None,
                    'bvec': bvec_file if bvec_file.exists() else None,
                    'json': json_file if json_file.exists() else None,
                    'entities': entities,
                    'subject': subject,
                    'session': session
                }
                
                dwi_files.append(dwi_info)
        
        return dwi_files
    
    def get_anat_files(self, subject: str, session: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get anatomical files for a subject/session.
        
        Args:
            subject: Subject ID (without 'sub-' prefix)
            session: Session ID (without 'ses-' prefix), optional
            
        Returns:
            List of dictionaries containing anatomical file information
        """
        if session:
            anat_dir = self.bids_root / f"sub-{subject}" / f"ses-{session}" / "anat"
        else:
            anat_dir = self.bids_root / f"sub-{subject}" / "anat"
        
        if not anat_dir.exists():
            return []
        
        anat_files = []
        
        # Common anatomical suffixes
        anat_suffixes = ["T1w", "T2w", "FLAIR", "PD"]
        
        for suffix in anat_suffixes:
            # Try both .nii.gz and .nii extensions
            for ext in ['.nii.gz', '.nii']:
                pattern = f"*_{suffix}{ext}"
                nii_files = list(anat_dir.glob(pattern))
                
                for nii_file in nii_files:
                    entities = self._parse_bids_filename(nii_file.name)
                    base_name = nii_file.name.replace(ext, '')
                    json_file = anat_dir / f"{base_name}.json"
                    
                    anat_info = {
                        'nii': nii_file,
                        'json': json_file if json_file.exists() else None,
                        'entities': entities,
                        'subject': subject,
                        'session': session,
                        'suffix': suffix
                    }
                    
                    anat_files.append(anat_info)
        
        return anat_files
    
    def get_dwi_metadata(self, dwi_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metadata from DWI JSON sidecar.
        
        Args:
            dwi_info: DWI file information dictionary
            
        Returns:
            Dictionary containing metadata
        """
        metadata = {}
        
        if dwi_info['json'] and dwi_info['json'].exists():
            try:
                with open(dwi_info['json'], 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to read JSON metadata from {dwi_info['json']}: {e}")
        
        return metadata
    
    def get_phase_encoding_groups(self, subject: str, session: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group DWI files by phase encoding direction for TopUp.
        
        Args:
            subject: Subject ID (without 'sub-' prefix)
            session: Session ID (without 'ses-' prefix), optional
            
        Returns:
            Dictionary mapping phase encoding directions to DWI files
        """
        dwi_files = self.get_dwi_files(subject, session)
        pe_groups = {}
        
        for dwi_info in dwi_files:
            # Try to determine phase encoding direction
            pe_dir = self._get_phase_encoding_direction(dwi_info)
            
            if pe_dir:
                if pe_dir not in pe_groups:
                    pe_groups[pe_dir] = []
                pe_groups[pe_dir].append(dwi_info)
        
        return pe_groups
    
    def _parse_bids_filename(self, filename: str) -> Dict[str, str]:
        """
        Parse BIDS filename to extract entities.
        
        Args:
            filename: BIDS filename
            
        Returns:
            Dictionary of BIDS entities
        """
        entities = {}
        
        # Remove file extension
        name = filename.replace('.nii.gz', '').replace('.nii', '')
        
        # Common BIDS entities
        entity_patterns = {
            'sub': r'sub-([a-zA-Z0-9]+)',
            'ses': r'ses-([a-zA-Z0-9]+)',
            'task': r'task-([a-zA-Z0-9]+)',
            'acq': r'acq-([a-zA-Z0-9]+)',
            'ce': r'ce-([a-zA-Z0-9]+)',
            'dir': r'dir-([a-zA-Z0-9]+)',
            'run': r'run-([0-9]+)',
            'mod': r'mod-([a-zA-Z0-9]+)',
            'echo': r'echo-([0-9]+)',
            'flip': r'flip-([0-9]+)',
            'inv': r'inv-([0-9]+)',
            'mt': r'mt-([a-zA-Z0-9]+)',
            'part': r'part-([a-zA-Z0-9]+)',
            'recording': r'recording-([a-zA-Z0-9]+)'
        }
        
        for entity, pattern in entity_patterns.items():
            match = re.search(pattern, name)
            if match:
                entities[entity] = match.group(1)
        
        return entities
    
    def _get_phase_encoding_direction(self, dwi_info: Dict[str, Any]) -> Optional[str]:
        """
        Determine phase encoding direction from filename or metadata.
        
        Args:
            dwi_info: DWI file information dictionary
            
        Returns:
            Phase encoding direction string or None
        """
        # First try to get from filename (dir- entity)
        if 'dir' in dwi_info['entities']:
            pe_dir = dwi_info['entities']['dir']
            if pe_dir in self.config.bids.phase_encoding_directions:
                return pe_dir
        
        # Try to get from JSON metadata
        metadata = self.get_dwi_metadata(dwi_info)
        
        if 'PhaseEncodingDirection' in metadata:
            pe_direction = metadata['PhaseEncodingDirection']
            
            # Map BIDS phase encoding directions to common abbreviations
            pe_mapping = {
                'j-': 'AP',  # Anterior to Posterior
                'j': 'PA',   # Posterior to Anterior
                'i-': 'RL',  # Right to Left
                'i': 'LR'    # Left to Right
            }
            
            return pe_mapping.get(pe_direction)
        
        return None
    
    def validate_subject_data(self, subject: str, session: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate BIDS data for a subject.
        
        Args:
            subject: Subject ID (without 'sub-' prefix)
            session: Session ID (without 'ses-' prefix), optional
            
        Returns:
            Dictionary with validation results
        """
        validation = {
            'subject': subject,
            'session': session,
            'valid': True,
            'errors': [],
            'warnings': [],
            'dwi_files': [],
            'anat_files': [],
            'has_dual_pe': False
        }
        
        # Get DWI files
        dwi_files = self.get_dwi_files(subject, session)
        validation['dwi_files'] = dwi_files
        
        if not dwi_files:
            validation['valid'] = False
            validation['errors'].append("No DWI files found")
        else:
            # Check for required files
            for dwi_info in dwi_files:
                if not dwi_info['bval']:
                    validation['warnings'].append(f"Missing .bval file for {dwi_info['nii'].name}")
                
                if not dwi_info['bvec']:
                    validation['warnings'].append(f"Missing .bvec file for {dwi_info['nii'].name}")
                
                if not dwi_info['json']:
                    validation['warnings'].append(f"Missing .json file for {dwi_info['nii'].name}")
        
        # Check for dual phase encoding
        pe_groups = self.get_phase_encoding_groups(subject, session)
        if len(pe_groups) >= 2:
            validation['has_dual_pe'] = True
        
        # Get anatomical files
        anat_files = self.get_anat_files(subject, session)
        validation['anat_files'] = anat_files
        
        if not anat_files:
            validation['warnings'].append("No anatomical files found")
        
        return validation 