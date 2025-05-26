#!/usr/bin/env python3
"""
Test script for SubTract Python pipeline.

This script tests the basic functionality of the pipeline
with data organization and denoising steps.
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from subtract.config.settings import SubtractConfig
from subtract.core.subject_manager import SubjectManager
from subtract.core.pipeline_runner import PipelineRunner


def setup_logging():
    """Setup basic logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("test_pipeline")


def test_legacy_pipeline():
    """Test pipeline with legacy (non-BIDS) data structure."""
    logger = setup_logging()
    logger.info("Testing legacy pipeline...")
    
    # Create configuration for current directory structure
    config = SubtractConfig.from_legacy_bash(Path.cwd())
    
    # Only run first two steps for testing
    config.steps_to_run = ["copy_data", "denoise"]
    config.processing.n_threads = 4  # Use fewer threads for testing
    
    logger.info(f"Data directory: {config.paths.data_dir}")
    logger.info(f"Analysis directory: {config.paths.analysis_dir}")
    
    # Initialize managers
    subject_manager = SubjectManager(config, logger)
    pipeline_runner = PipelineRunner(config, logger)
    
    # Discover subjects
    subjects = subject_manager.discover_subjects()
    logger.info(f"Found subjects: {subjects}")
    
    if not subjects:
        logger.warning("No subjects found in Data directory")
        return
    
    # Test with first subject only
    test_subject = subjects[0]
    logger.info(f"Testing with subject: {test_subject}")
    
    # Validate subject
    validation = subject_manager.validate_subject(test_subject)
    logger.info(f"Subject validation: {validation['valid']}")
    
    if validation['errors']:
        logger.error(f"Validation errors: {validation['errors']}")
    
    if validation['warnings']:
        logger.warning(f"Validation warnings: {validation['warnings']}")
    
    # Run pipeline for test subject
    try:
        results = pipeline_runner.run_subject(test_subject)
        
        logger.info("Pipeline results:")
        for step, result in results.items():
            status = "SUCCESS" if result.success else "FAILED"
            logger.info(f"  {step}: {status} ({result.execution_time:.2f}s)")
            
            if not result.success:
                logger.error(f"    Error: {result.error_message}")
            else:
                logger.info(f"    Outputs: {len(result.outputs)} files")
                logger.info(f"    Metrics: {result.metrics}")
    
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise


def test_bids_pipeline():
    """Test pipeline with BIDS data structure (if available)."""
    logger = setup_logging()
    logger.info("Testing BIDS pipeline...")
    
    # Look for BIDS dataset in current directory or subdirectories
    bids_candidates = [
        Path.cwd(),
        Path.cwd() / "bids_data",
        Path.cwd() / "Data"
    ]
    
    bids_root = None
    for candidate in bids_candidates:
        if (candidate / "dataset_description.json").exists():
            bids_root = candidate
            break
    
    if not bids_root:
        logger.info("No BIDS dataset found, skipping BIDS test")
        return
    
    logger.info(f"Found BIDS dataset: {bids_root}")
    
    # Create BIDS configuration
    config = SubtractConfig.from_bids_dataset(bids_root)
    config.steps_to_run = ["copy_data", "denoise"]
    config.processing.n_threads = 4
    
    # Initialize managers
    subject_manager = SubjectManager(config, logger)
    pipeline_runner = PipelineRunner(config, logger)
    
    # Discover subjects
    subjects = subject_manager.discover_subjects()
    logger.info(f"Found BIDS subjects: {subjects}")
    
    if not subjects:
        logger.warning("No subjects found in BIDS dataset")
        return
    
    # Test with first subject
    test_subject = subjects[0]
    logger.info(f"Testing BIDS subject: {test_subject}")
    
    # Check for sessions
    sessions = subject_manager.get_subject_sessions(test_subject)
    if sessions:
        logger.info(f"Found sessions: {sessions}")
        test_session = sessions[0]
        validation = subject_manager.validate_subject(test_subject, test_session)
        logger.info(f"Session validation: {validation['valid']}")
        
        # Run pipeline
        results = pipeline_runner.run_subject(test_subject, test_session)
    else:
        validation = subject_manager.validate_subject(test_subject)
        logger.info(f"Subject validation: {validation['valid']}")
        
        # Run pipeline
        results = pipeline_runner.run_subject(test_subject)
    
    logger.info("BIDS Pipeline results:")
    for step, result in results.items():
        status = "SUCCESS" if result.success else "FAILED"
        logger.info(f"  {step}: {status} ({result.execution_time:.2f}s)")


def main():
    """Main test function."""
    logger = setup_logging()
    logger.info("Starting SubTract pipeline tests...")
    
    try:
        # Test legacy pipeline
        test_legacy_pipeline()
        
        # Test BIDS pipeline if available
        test_bids_pipeline()
        
        logger.info("All tests completed!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 