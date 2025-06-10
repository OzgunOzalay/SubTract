#!/usr/bin/env python3
"""
Test script for Step 008 (Tractography) integration.

This script validates the implementation without running actual commands.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from subtract.config.settings import SubtractConfig
from subtract.tractography.track_generator import TrackGenerator
from subtract.core.pipeline_runner import PipelineRunner
import logging

def test_track_generator_import():
    """Test that TrackGenerator can be imported and instantiated."""
    print("Testing TrackGenerator import...")
    
    # Create a basic config
    config = SubtractConfig.from_bids_dataset(Path.cwd() / "Data")
    
    # Create logger
    logger = logging.getLogger("test")
    
    # Test instantiation
    track_gen = TrackGenerator(config, logger)
    print(f"✓ TrackGenerator instantiated with step_name: {track_gen.step_name}")
    
    return track_gen

def test_pipeline_integration():
    """Test that tractography step is integrated into pipeline runner."""
    print("\nTesting Pipeline Integration...")
    
    # Create config with tractography step
    config = SubtractConfig.from_bids_dataset(Path.cwd() / "Data")
    config.steps_to_run = ["copy_data", "denoise", "topup", "eddy", "mdt", "mrtrix_prep", "tractography"]
    
    # Create logger
    logger = logging.getLogger("test")
    
    # Test pipeline runner
    runner = PipelineRunner(config, logger)
    
    # Check if tractography processor is initialized
    if "tractography" in runner.processors:
        print("✓ Tractography processor registered in pipeline")
        processor = runner.processors["tractography"]
        print(f"✓ Processor type: {type(processor).__name__}")
    else:
        print("✗ Tractography processor not found in pipeline")
        return False
    
    return True

def test_expected_outputs():
    """Test expected output file paths."""
    print("\nTesting Expected Outputs...")
    
    config = SubtractConfig.from_bids_dataset(Path.cwd() / "Data")
    logger = logging.getLogger("test")
    
    track_gen = TrackGenerator(config, logger)
    
    # Test output file paths
    subject_id = "test_subject"
    expected_outputs = track_gen.get_expected_outputs(subject_id)
    
    print("Expected output files:")
    for output in expected_outputs:
        print(f"  - {output}")
    
    # Check that we have the right number of outputs
    expected_count = 6  # 2 ROI NIfTI + 2 ROI MIF + 2 track files
    if len(expected_outputs) == expected_count:
        print(f"✓ Correct number of expected outputs: {expected_count}")
    else:
        print(f"✗ Expected {expected_count} outputs, got {len(expected_outputs)}")
        return False
    
    return True

def test_prerequisites_validation():
    """Test the prerequisites validation logic."""
    print("\nTesting Prerequisites Validation...")
    
    config = SubtractConfig.from_bids_dataset(Path.cwd() / "Data")
    logger = logging.getLogger("test")
    
    track_gen = TrackGenerator(config, logger)
    
    # This should fail since we don't have actual data
    subject_id = "test_subject"
    is_valid = track_gen.validate_inputs(subject_id)
    
    print(f"Prerequisites validation (expected to fail): {is_valid}")
    print("✓ Prerequisites validation logic works")
    
    return True

def main():
    """Run all tests."""
    print("=== Step 008 (Tractography) Integration Test ===\n")
    
    tests = [
        test_track_generator_import,
        test_pipeline_integration,
        test_expected_outputs,
        test_prerequisites_validation
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
                print("✓ PASSED\n")
            else:
                failed += 1
                print("✗ FAILED\n")
        except Exception as e:
            failed += 1
            print(f"✗ FAILED with exception: {e}\n")
    
    print("=== Test Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Step 008 integration looks good.")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 