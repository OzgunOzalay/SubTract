"""
ROI Registration processor for SubTract pipeline.

This module handles the registration of template ROIs from fsaverage to subject DWI space using ANTs transformations.
"""

import time
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess
import shutil

from ..core.base_processor import BaseProcessor, ProcessingResult
from ..config.settings import SubtractConfig


class ROIRegistration(BaseProcessor):
    """
    ROI Registration processor for transforming template ROIs to subject DWI space.
    
    This processor:
    1. Transforms BNST network ROIs from fsaverage to subject DWI space
    2. Uses ANTs transformation matrices from Step 007
    3. Creates combined parcellation files for connectivity analysis
    4. Validates transformed ROIs
    """

    def __init__(self, config: SubtractConfig, logger):
        super().__init__(config, logger)
        self.name = "ROI Registration"
        
        # Define the BNST network ROIs to transform
        self.bnst_regions = [
            "L_amygdala_fsaverage",
            "R_amygdala_fsaverage", 
            "L_hippocampus_fsaverage",
            "R_hippocampus_fsaverage",
            "L_vmPFC_fsaverage",
            "R_vmPFC_fsaverage",
            "L_insula_fsaverage",
            "R_insula_fsaverage",
            "L_hypothalamus_fsaverage",
            "R_hypothalamus_fsaverage",
            "L_bnst_fsaverage",
            "R_bnst_fsaverage"
        ]

    def process(self, subject_id: str, session_id: Optional[str] = None) -> ProcessingResult:
        """
        Register ROIs from fsaverage to subject DWI space.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (for BIDS datasets)
            
        Returns:
            ProcessingResult with success status and output files
        """
        self.logger.info(f"Starting ROI registration for subject: {subject_id}")
        start_time = time.time()
        
        try:
            # Setup paths
            subject_paths = self._setup_paths(subject_id, session_id)
            
            # Check prerequisites
            self._validate_inputs(subject_paths)
            
            # Create ROI output directory
            roi_dir = subject_paths["mrtrix_dir"] / "ROIs"
            roi_dir.mkdir(parents=True, exist_ok=True)
            
            # Transform each ROI to subject DWI space
            transformed_rois = self._transform_rois(subject_paths, roi_dir)
            
            # Create combined parcellation files
            parcellation_files = self._create_parcellations(roi_dir)
            
            # Validate outputs
            self._validate_outputs(transformed_rois + parcellation_files)
            
            execution_time = time.time() - start_time
            self.logger.info(f"ROI registration completed in {execution_time:.2f} seconds")
            
            return ProcessingResult(
                success=True,
                outputs=transformed_rois + parcellation_files,
                metrics={
                    "execution_time": execution_time,
                    "rois_transformed": len(transformed_rois),
                    "parcellations_created": len(parcellation_files)
                },
                execution_time=execution_time
            )
            
        except Exception as e:
            error_msg = f"ROI registration failed for {subject_id}: {str(e)}"
            self.logger.error(error_msg)
            return ProcessingResult(
                success=False,
                outputs=[],
                metrics={},
                execution_time=time.time() - start_time,
                error_message=error_msg
            )

    def _setup_paths(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, Path]:
        """Setup file paths for ROI registration."""
        analysis_dir = self.config.paths.analysis_dir
        
        # Always use BIDS format
        if session_id:
            subject_analysis_dir = analysis_dir / f"sub-{subject_id}" / f"ses-{session_id}"
        else:
            subject_analysis_dir = analysis_dir / f"sub-{subject_id}"
            
        return {
            "subject_analysis_dir": subject_analysis_dir,
            "mrtrix_dir": subject_analysis_dir / "dwi" / "mrtrix3",
            "roi_source_dir": Path(self.config.paths.base_path) / "ROIs",
            "transformation_matrix": subject_analysis_dir / "dwi" / "mrtrix3" / "fs2diff_0GenericAffine.mat",
            "reference_image": subject_analysis_dir / "dwi" / "mrtrix3" / "mean_b0_brain.mif"
        }

    def _validate_inputs(self, paths: Dict[str, Path]) -> None:
        """Validate that required input files exist."""
        required_files = [
            ("transformation_matrix", "ANTs transformation matrix from Step 007"),
            ("reference_image", "Reference DWI image from Step 007"),
            ("roi_source_dir", "ROI source directory")
        ]
        
        for file_key, description in required_files:
            if not paths[file_key].exists():
                raise FileNotFoundError(f"Required {description} not found: {paths[file_key]}")
        
        # Check that all ROI files exist
        for roi_name in self.bnst_regions:
            roi_file = paths["roi_source_dir"] / f"{roi_name}.nii.gz"
            if not roi_file.exists():
                raise FileNotFoundError(f"ROI file not found: {roi_file}")

    def _transform_rois(self, paths: Dict[str, Path], roi_dir: Path) -> List[Path]:
        """Transform ROIs from fsaverage to subject DWI space."""
        self.logger.info("Transforming ROIs to subject DWI space")
        
        transformed_rois = []
        
        for roi_name in self.bnst_regions:
            self.logger.info(f"Transforming ROI: {roi_name}")
            
            # Input and output file paths
            input_roi = paths["roi_source_dir"] / f"{roi_name}.nii.gz"
            output_roi_nii = roi_dir / f"{roi_name.replace('_fsaverage', '_DWI')}.nii.gz"
            output_roi_mif = roi_dir / f"{roi_name.replace('_fsaverage', '_DWI')}.mif"
            
            # Step 1: Binarize ROI (ensure binary mask)
            binarized_roi = roi_dir / f"{roi_name}_binarized.nii.gz"
            self._run_mri_binarize(input_roi, binarized_roi)
            
            # Step 2: Apply ANTs transformation to register ROI to DWI space
            self._apply_ants_transform(
                input_image=binarized_roi,
                output_image=output_roi_nii,
                reference_image=paths["reference_image"],
                transformation_matrix=paths["transformation_matrix"]
            )
            
            # Step 3: Convert to MIF format for MRtrix3 compatibility
            self._convert_to_mif(output_roi_nii, output_roi_mif)
            
            # Clean up temporary binarized file
            binarized_roi.unlink(missing_ok=True)
            
            transformed_rois.append(output_roi_mif)
            
        return transformed_rois

    def _run_mri_binarize(self, input_file: Path, output_file: Path) -> None:
        """Binarize ROI using FreeSurfer mri_binarize."""
        cmd = [
            "mri_binarize",
            "--i", str(input_file),
            "--match", "1",
            "--o", str(output_file)
        ]
        
        try:
            # Run in subtract environment (FreeSurfer tools should be available)
            self._run_conda_command(cmd, env_name="subtract")
        except subprocess.CalledProcessError as e:
            # Fallback: try with simple thresholding using MRtrix3
            self.logger.warning(f"mri_binarize failed, using MRtrix3 mrcalc as fallback: {e}")
            self._run_mrcalc_binarize(input_file, output_file)

    def _run_mrcalc_binarize(self, input_file: Path, output_file: Path) -> None:
        """Fallback binarization using MRtrix3 mrcalc."""
        cmd = [
            "mrcalc", str(input_file), "0", "-gt", str(output_file), "-force"
        ]
        self._run_conda_command(cmd, env_name="subtract")

    def _apply_ants_transform(
        self, 
        input_image: Path, 
        output_image: Path, 
        reference_image: Path,
        transformation_matrix: Path
    ) -> None:
        """Apply ANTs transformation to register ROI to DWI space."""
        
        # First, convert reference MIF to NIfTI for ANTs
        reference_nii = output_image.parent / "temp_reference.nii.gz"
        self._convert_mif_to_nii(reference_image, reference_nii)
        
        cmd = [
            "antsApplyTransforms",
            "-d", "3",
            "-i", str(input_image),
            "-r", str(reference_nii),
            "-t", str(transformation_matrix),
            "-o", str(output_image),
            "-n", "NearestNeighbor"  # Use nearest neighbor for binary masks
        ]
        
        try:
            self._run_conda_command(cmd, env_name="ants")
            # Clean up temporary reference file
            reference_nii.unlink(missing_ok=True)
        except subprocess.CalledProcessError as e:
            # Clean up temporary reference file even on error
            reference_nii.unlink(missing_ok=True)
            raise RuntimeError(f"ANTs transformation failed: {e}")

    def _convert_mif_to_nii(self, mif_file: Path, nii_file: Path) -> None:
        """Convert MIF file to NIfTI format."""
        cmd = ["mrconvert", str(mif_file), str(nii_file), "-force"]
        self._run_conda_command(cmd, env_name="subtract")

    def _convert_to_mif(self, nii_file: Path, mif_file: Path) -> None:
        """Convert NIfTI to MIF format."""
        cmd = ["mrconvert", str(nii_file), str(mif_file), "-force"]
        self._run_conda_command(cmd, env_name="subtract")

    def _create_parcellations(self, roi_dir: Path) -> List[Path]:
        """Create combined parcellation files for left and right hemispheres."""
        self.logger.info("Creating combined parcellation files")
        
        parcellation_files = []
        
        # Create left hemisphere parcellation
        left_parc_file = roi_dir / "left_bnst_network_parcellation.mif"
        self._create_hemisphere_parcellation(roi_dir, "L", left_parc_file)
        parcellation_files.append(left_parc_file)
        
        # Create right hemisphere parcellation  
        right_parc_file = roi_dir / "right_bnst_network_parcellation.mif"
        self._create_hemisphere_parcellation(roi_dir, "R", right_parc_file)
        parcellation_files.append(right_parc_file)
        
        return parcellation_files

    def _create_hemisphere_parcellation(self, roi_dir: Path, hemisphere: str, output_file: Path) -> None:
        """Create parcellation file for one hemisphere with numbered ROIs."""
        
        # Define ROI mapping (1-based indexing for connectivity analysis)
        roi_mapping = {
            f"{hemisphere}_amygdala_DWI.mif": 1,
            f"{hemisphere}_hippocampus_DWI.mif": 2, 
            f"{hemisphere}_vmPFC_DWI.mif": 3,
            f"{hemisphere}_insula_DWI.mif": 4,
            f"{hemisphere}_hypothalamus_DWI.mif": 5
        }
        
        # Start with zero image based on first ROI
        first_roi = roi_dir / f"{hemisphere}_amygdala_DWI.mif"
        temp_zero = roi_dir / f"temp_zero_{hemisphere}.mif"
        
        cmd = ["mrcalc", str(first_roi), "0", "-mult", str(temp_zero), "-force"]
        self._run_conda_command(cmd, env_name="subtract")
        
        # Initialize parcellation with zero image
        shutil.copy(temp_zero, output_file)
        
        # Add each ROI with its assigned number
        for roi_file, roi_number in roi_mapping.items():
            roi_path = roi_dir / roi_file
            
            if roi_path.exists():
                self.logger.info(f"Adding {roi_file} as region {roi_number}")
                
                # Create temporary file for this step
                temp_file = roi_dir / f"temp_parc_{hemisphere}_{roi_number}.mif"
                
                # Add ROI to parcellation: 
                # where ROI==1 AND parcellation==0, set to roi_number, otherwise keep parcellation
                cmd = [
                    "mrcalc", 
                    str(roi_path), "1", "-eq",  # ROI mask
                    str(output_file), "0", "-eq", "-mult",  # AND parcellation is zero
                    str(roi_number), "-mult",  # Multiply by ROI number
                    str(output_file), "-add",  # Add to existing parcellation
                    str(temp_file), "-force"
                ]
                
                self._run_conda_command(cmd, env_name="subtract")
                
                # Replace parcellation with updated version
                shutil.move(temp_file, output_file)
            else:
                self.logger.warning(f"ROI file not found: {roi_path}")
        
        # Clean up temporary zero file
        temp_zero.unlink(missing_ok=True)

    def _validate_outputs(self, output_files: List[Path]) -> None:
        """Validate that all expected output files were created."""
        for output_file in output_files:
            if not output_file.exists():
                raise FileNotFoundError(f"Expected output file not created: {output_file}")
            
            # Check file size (should be > 0)
            if output_file.stat().st_size == 0:
                raise ValueError(f"Output file is empty: {output_file}")

    def validate_inputs(self, subject_id: str, session_id: Optional[str] = None) -> bool:
        """Validate inputs for ROI registration."""
        try:
            paths = self._setup_paths(subject_id, session_id)
            self._validate_inputs(paths)
            return True
        except Exception as e:
            self.logger.error(f"Input validation failed: {e}")
            return False

    def get_expected_outputs(self, subject_id: str, session_id: Optional[str] = None) -> List[Path]:
        """Get expected output files for ROI registration."""
        paths = self._setup_paths(subject_id, session_id)
        roi_dir = paths["mrtrix_dir"] / "ROIs"
        
        outputs = []
        
        # Individual transformed ROIs
        for roi_name in self.bnst_regions:
            output_roi = roi_dir / f"{roi_name.replace('_fsaverage', '_DWI')}.mif"
            outputs.append(output_roi)
        
        # Combined parcellation files
        outputs.extend([
            roi_dir / "left_bnst_network_parcellation.mif",
            roi_dir / "right_bnst_network_parcellation.mif"
        ])
        
        return outputs

    def get_outputs(self, subject_id: str, session_id: Optional[str] = None) -> List[Path]:
        """Get expected output files for ROI registration (alias for get_expected_outputs)."""
        return self.get_expected_outputs(subject_id, session_id)

    def _run_conda_command(self, cmd: List[str], env_name: str) -> None:
        """Run command in specified conda environment."""
        self.run_command_in_env(cmd, env_name) 