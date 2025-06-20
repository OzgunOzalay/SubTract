"""
Pipeline runner for SubTract pipeline.

This module orchestrates the execution of all processing steps for subjects.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from ..config.settings import SubtractConfig
from ..core.base_processor import ProcessingResult
from ..preprocessing.data_organizer import DataOrganizer
from ..preprocessing.denoiser import DWIDenoiser
from ..preprocessing.gibbs_remover import GibbsRemover
from ..preprocessing.distortion_corrector import DistortionCorrector
from ..preprocessing.eddy_corrector import EddyCorrector
from ..preprocessing.mdt_processor import MDTProcessor
from ..preprocessing.mrtrix_preprocessor import MRtrixPreprocessor
from ..tractography.track_generator import TrackGenerator
from ..tractography.track_filter import TrackFilter
from ..registration.roi_registration import ROIRegistration
try:
    from ..connectome.connectivity_matrix import ConnectivityMatrix
except ImportError:
    # Fall back to absolute import if relative import fails
    try:
        from subtract.connectome.connectivity_matrix import ConnectivityMatrix
    except ImportError:
        ConnectivityMatrix = None


class PipelineRunner:
    """
    Main pipeline runner that orchestrates all processing steps.
    
    This class manages the execution of the complete SubTract pipeline,
    handling step dependencies, error recovery, and progress tracking.
    """
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the pipeline runner.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
        # Initialize processors for each step
        self.processors = self._initialize_processors()
    
    def _initialize_processors(self) -> Dict[str, Any]:
        """Initialize all processing step classes."""
        processors = {}
        
        # Initialize available processors
        if "copy_data" in self.config.steps_to_run:
            processors["copy_data"] = DataOrganizer(self.config, self.logger)
        
        if "denoise" in self.config.steps_to_run:
            processors["denoise"] = DWIDenoiser(self.config, self.logger)
        
        if "degibbs" in self.config.steps_to_run:
            processors["degibbs"] = GibbsRemover(self.config, self.logger)
        
        if "topup" in self.config.steps_to_run:
            processors["topup"] = DistortionCorrector(self.config, self.logger)
        
        if "eddy" in self.config.steps_to_run:
            processors["eddy"] = EddyCorrector(self.config, self.logger)
        
        if "mdt" in self.config.steps_to_run:
            processors["mdt"] = MDTProcessor(self.config, self.logger)
        
        if "mrtrix_prep" in self.config.steps_to_run:
            processors["mrtrix_prep"] = MRtrixPreprocessor(self.config, self.logger)
        
        if "tractography" in self.config.steps_to_run:
            processors["tractography"] = TrackGenerator(self.config, self.logger)
        
        if "sift2" in self.config.steps_to_run:
            processors["sift2"] = TrackFilter(self.config, self.logger)
        
        if "roi_registration" in self.config.steps_to_run:
            processors["roi_registration"] = ROIRegistration(self.config, self.logger)
        
        if "connectome" in self.config.steps_to_run:
            if ConnectivityMatrix is not None:
                processors["connectome"] = ConnectivityMatrix(self.config, self.logger)
            else:
                self.logger.warning("ConnectivityMatrix not available, skipping connectome step")
        
        return processors
    
    def run_subject(self, subject_id: str, session_id: Optional[str] = None) -> Dict[str, ProcessingResult]:
        """
        Run the complete pipeline for a single subject.
        
        Args:
            subject_id: Subject identifier
            session_id: Session identifier (BIDS only)
            
        Returns:
            Dictionary mapping step names to ProcessingResult objects
        """
        session_str = f" session {session_id}" if session_id else ""
        self.logger.info(f"Starting pipeline for subject: {subject_id}{session_str}")
        start_time = time.time()
        
        results = {}
        
        # Execute steps in order
        for step_name in self.config.steps_to_run:
            if step_name not in self.processors:
                self.logger.warning(f"Processor for step '{step_name}' not implemented yet, skipping")
                continue
            
            self.logger.info(f"Running step: {step_name} for subject: {subject_id}{session_str}")
            
            try:
                processor = self.processors[step_name]
                result = processor.process(subject_id, session_id)
                results[step_name] = result
                
                if not result.success:
                    self.logger.error(f"Step {step_name} failed for subject {subject_id}{session_str}: {result.error_message}")
                    # Decide whether to continue or stop based on step criticality
                    if self._is_critical_step(step_name):
                        self.logger.error(f"Critical step {step_name} failed, stopping pipeline for {subject_id}{session_str}")
                        break
                
            except Exception as e:
                error_msg = f"Unexpected error in step {step_name} for subject {subject_id}{session_str}: {str(e)}"
                self.logger.error(error_msg)
                
                results[step_name] = ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=0.0,
                    error_message=error_msg
                )
                
                if self._is_critical_step(step_name):
                    self.logger.error(f"Critical step {step_name} failed, stopping pipeline for {subject_id}{session_str}")
                    break
        
        total_time = time.time() - start_time
        self.logger.info(f"Completed pipeline for subject {subject_id}{session_str} in {total_time:.2f} seconds")
        
        return results
    
    def run_multiple_subjects(
        self, 
        subject_ids: List[str], 
        parallel: bool = False,
        n_jobs: Optional[int] = None
    ) -> Dict[str, Dict[str, ProcessingResult]]:
        """
        Run the pipeline for multiple subjects.
        
        Args:
            subject_ids: List of subject identifiers
            parallel: Whether to run subjects in parallel
            n_jobs: Number of parallel jobs (default: use config n_threads)
            
        Returns:
            Dictionary mapping subject IDs to their results
        """
        if parallel:
            return self._run_subjects_parallel(subject_ids, n_jobs)
        else:
            return self._run_subjects_sequential(subject_ids)
    
    def _run_subjects_sequential(self, subject_ids: List[str]) -> Dict[str, Dict[str, ProcessingResult]]:
        """Run subjects sequentially."""
        all_results = {}
        
        # Import here to avoid circular imports
        from .subject_manager import SubjectManager
        subject_manager = SubjectManager(self.config, self.logger)
        
        for subject_id in subject_ids:
            try:
                # Check if subject has sessions
                sessions = subject_manager.get_subject_sessions(subject_id)
                
                if sessions:
                    # Process each session
                    for session_id in sessions:
                        session_key = f"{subject_id}_ses-{session_id}"
                        results = self.run_subject(subject_id, session_id)
                        all_results[session_key] = results
                else:
                    # Process subject without sessions
                    results = self.run_subject(subject_id)
                    all_results[subject_id] = results
                    
            except Exception as e:
                self.logger.error(f"Failed to process subject {subject_id}: {str(e)}")
                all_results[subject_id] = {}
        
        return all_results
    
    def _run_subjects_parallel(
        self, 
        subject_ids: List[str], 
        n_jobs: Optional[int] = None
    ) -> Dict[str, Dict[str, ProcessingResult]]:
        """Run subjects in parallel using joblib."""
        try:
            from joblib import Parallel, delayed
        except ImportError:
            self.logger.warning("joblib not available, falling back to sequential processing")
            return self._run_subjects_sequential(subject_ids)
        
        if n_jobs is None:
            n_jobs = min(self.config.processing.n_threads, len(subject_ids))
        
        self.logger.info(f"Running {len(subject_ids)} subjects in parallel with {n_jobs} jobs")
        
        def process_subject_wrapper(subject_id):
            try:
                # Import here to avoid circular imports
                from .subject_manager import SubjectManager
                subject_manager = SubjectManager(self.config, self.logger)
                
                # Check if subject has sessions
                sessions = subject_manager.get_subject_sessions(subject_id)
                
                if sessions:
                    # Process each session
                    session_results = {}
                    for session_id in sessions:
                        session_key = f"{subject_id}_ses-{session_id}"
                        results = self.run_subject(subject_id, session_id)
                        session_results[session_key] = results
                    return subject_id, session_results
                else:
                    # Process subject without sessions
                    results = self.run_subject(subject_id)
                    return subject_id, {subject_id: results}
                    
            except Exception as e:
                self.logger.error(f"Failed to process subject {subject_id}: {str(e)}")
                return subject_id, {}
        
        results_list = Parallel(n_jobs=n_jobs)(
            delayed(process_subject_wrapper)(subject_id) 
            for subject_id in subject_ids
        )
        
        # Flatten the results
        all_results = {}
        for subject_id, subject_results in results_list:
            all_results.update(subject_results)
        
        return all_results
    
    def run_step_for_subjects(
        self, 
        step_name: str, 
        subject_ids: List[str]
    ) -> Dict[str, ProcessingResult]:
        """
        Run a specific step for multiple subjects.
        
        Args:
            step_name: Name of the processing step
            subject_ids: List of subject identifiers
            
        Returns:
            Dictionary mapping subject IDs to ProcessingResult objects
        """
        if step_name not in self.processors:
            raise ValueError(f"Processor for step '{step_name}' not available")
        
        processor = self.processors[step_name]
        results = {}
        
        for subject_id in subject_ids:
            try:
                result = processor.process(subject_id)
                results[subject_id] = result
            except Exception as e:
                error_msg = f"Error in step {step_name} for subject {subject_id}: {str(e)}"
                self.logger.error(error_msg)
                
                results[subject_id] = ProcessingResult(
                    success=False,
                    outputs=[],
                    metrics={},
                    execution_time=0.0,
                    error_message=error_msg
                )
        
        return results
    
    def _is_critical_step(self, step_name: str) -> bool:
        """
        Determine if a step is critical (pipeline should stop if it fails).
        
        Args:
            step_name: Name of the processing step
            
        Returns:
            True if the step is critical
        """
        # Define critical steps that should stop the pipeline if they fail
        critical_steps = {
            "copy_data",  # Can't proceed without data
            "denoise",    # Essential preprocessing
            "eddy",       # Essential motion correction
        }
        
        return step_name in critical_steps
    
    def get_pipeline_summary(self, results: Dict[str, Dict[str, ProcessingResult]]) -> Dict[str, Any]:
        """
        Generate a summary of pipeline results across subjects.
        
        Args:
            results: Results from run_multiple_subjects
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_subjects": len(results),
            "successful_subjects": 0,
            "failed_subjects": 0,
            "step_success_rates": {},
            "total_execution_time": 0.0,
            "average_execution_time": 0.0
        }
        
        step_counts = {}
        step_successes = {}
        
        for subject_id, subject_results in results.items():
            subject_success = True
            subject_time = 0.0
            
            for step_name, result in subject_results.items():
                # Track step statistics
                if step_name not in step_counts:
                    step_counts[step_name] = 0
                    step_successes[step_name] = 0
                
                step_counts[step_name] += 1
                if result.success:
                    step_successes[step_name] += 1
                else:
                    subject_success = False
                
                subject_time += result.execution_time
            
            if subject_success:
                summary["successful_subjects"] += 1
            else:
                summary["failed_subjects"] += 1
            
            summary["total_execution_time"] += subject_time
        
        # Calculate success rates
        for step_name in step_counts:
            if step_counts[step_name] > 0:
                success_rate = step_successes[step_name] / step_counts[step_name]
                summary["step_success_rates"][step_name] = success_rate
        
        # Calculate average execution time
        if summary["total_subjects"] > 0:
            summary["average_execution_time"] = summary["total_execution_time"] / summary["total_subjects"]
        
        return summary 