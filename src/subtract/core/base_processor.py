"""
Base processor class for all pipeline steps.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import logging
import subprocess
import shlex

from ..config.settings import SubtractConfig
from ..utils.conda_utils import run_tool_command, run_in_conda_env


@dataclass
class ProcessingResult:
    """Result of a processing step."""
    
    success: bool
    outputs: List[Path]
    metrics: Dict[str, Any]
    execution_time: float
    error_message: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class BaseProcessor(ABC):
    """Abstract base class for all processing steps."""
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        """
        Initialize the processor.
        
        Args:
            config: Pipeline configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        
    @abstractmethod
    def process(self, subject_id: str, **kwargs) -> ProcessingResult:
        """
        Process a subject.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional processing parameters
            
        Returns:
            ProcessingResult with outputs and metrics
        """
        pass
    
    @abstractmethod
    def validate_inputs(self, subject_id: str, **kwargs) -> bool:
        """
        Validate inputs before processing.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters
            
        Returns:
            True if inputs are valid
        """
        pass
    
    @abstractmethod
    def get_expected_outputs(self, subject_id: str, **kwargs) -> List[Path]:
        """
        Get list of expected output files.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters
            
        Returns:
            List of expected output file paths
        """
        pass
    
    def check_outputs_exist(self, subject_id: str, **kwargs) -> bool:
        """
        Check if expected outputs already exist.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters
            
        Returns:
            True if all expected outputs exist
        """
        expected_outputs = self.get_expected_outputs(subject_id, **kwargs)
        return all(output.exists() for output in expected_outputs)
    
    def should_skip(self, subject_id: str, **kwargs) -> bool:
        """
        Determine if processing should be skipped.
        
        Args:
            subject_id: Subject identifier
            **kwargs: Additional parameters
            
        Returns:
            True if processing should be skipped
        """
        if self.config.processing.force_overwrite:
            return False
        
        return self.check_outputs_exist(subject_id, **kwargs)
    
    def run_command(
        self, 
        command: Union[str, List[str]], 
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True,
        use_conda: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command safely.
        
        Args:
            command: Command to run (string or list)
            cwd: Working directory
            env: Environment variables
            capture_output: Whether to capture stdout/stderr
            use_conda: Whether to use appropriate conda environment
            
        Returns:
            CompletedProcess result
        """
        if use_conda:
            # Use conda environment based on tool
            return run_tool_command(
                command=command,
                cwd=cwd,
                env=env,
                capture_output=capture_output,
                check=True
            )
        else:
            # Original implementation for non-conda commands
            if isinstance(command, str):
                command_list = shlex.split(command)
            else:
                command_list = command
            
            self.logger.debug(f"Running command: {' '.join(command_list)}")
            
            try:
                result = subprocess.run(
                    command_list,
                    cwd=cwd,
                    env=env,
                    capture_output=capture_output,
                    text=True,
                    check=True
                )
                return result
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Command failed: {' '.join(command_list)}")
                self.logger.error(f"Return code: {e.returncode}")
                if e.stdout:
                    self.logger.error(f"Stdout: {e.stdout}")
                if e.stderr:
                    self.logger.error(f"Stderr: {e.stderr}")
                raise
    
    def run_command_in_env(
        self,
        command: Union[str, List[str]],
        env_name: str,
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a command in a specific conda environment.
        
        Args:
            command: Command to run
            env_name: Conda environment name
            cwd: Working directory
            env: Environment variables
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            CompletedProcess result
        """
        return run_in_conda_env(
            command=command,
            env_name=env_name,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            check=True
        )
    
    def create_output_directory(self, output_path: Path) -> None:
        """
        Create output directory if it doesn't exist.
        
        Args:
            output_path: Path to create
        """
        if output_path.is_file():
            output_path = output_path.parent
        
        output_path.mkdir(parents=True, exist_ok=True)
        self.logger.debug(f"Created directory: {output_path}")
    
    def get_subject_dir(self, subject_id: str, subdir: Optional[str] = None) -> Path:
        """
        Get subject-specific directory path in BIDS format.
        
        Args:
            subject_id: Subject identifier (without "sub-" prefix)
            subdir: Optional subdirectory
            
        Returns:
            Path to subject directory
        """
        subject_path = self.config.paths.analysis_dir / f"sub-{subject_id}"
        
        if subdir:
            subject_path = subject_path / subdir
        
        return subject_path
    
    def log_processing_start(self, subject_id: str, step_name: str) -> None:
        """Log the start of processing."""
        self.logger.info(f"Starting {step_name} for subject: {subject_id}")
    
    def log_processing_end(self, subject_id: str, step_name: str, result: ProcessingResult) -> None:
        """Log the end of processing."""
        status = "SUCCESS" if result.success else "FAILED"
        self.logger.info(
            f"Finished {step_name} for subject {subject_id}: {status} "
            f"(execution time: {result.execution_time:.2f}s)"
        )
        
        if result.warnings:
            for warning in result.warnings:
                self.logger.warning(f"{subject_id}: {warning}")
        
        if not result.success and result.error_message:
            self.logger.error(f"{subject_id}: {result.error_message}")


class FSLProcessor(BaseProcessor):
    """Base class for FSL-based processors."""
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self._check_fsl_installation()
    
    def _check_fsl_installation(self) -> None:
        """Check if FSL is properly installed in conda environment."""
        try:
            # Check fsl in the appropriate conda environment  
            result = self.run_command_in_env(
                command=["which", "fsl"],
                env_name="subtract", 
                capture_output=True
            )
            self.logger.debug(f"FSL found at: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.logger.warning("FSL not found in 'subtract' environment, but will try to use conda run for commands")


class MRtrix3Processor(BaseProcessor):
    """Base class for MRtrix3-based processors."""
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self._check_mrtrix3_installation()
    
    def _check_mrtrix3_installation(self) -> None:
        """Check if MRtrix3 is properly installed in conda environment."""
        try:
            # Check mrconvert in the appropriate conda environment
            result = self.run_command_in_env(
                command=["which", "mrconvert"],
                env_name="subtract",
                capture_output=True
            )
            self.logger.debug(f"MRtrix3 found at: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.logger.warning("MRtrix3 not found in 'subtract' environment, but will try to use conda run for commands")


class ANTsProcessor(BaseProcessor):
    """Base class for ANTs-based processors."""
    
    def __init__(self, config: SubtractConfig, logger: Optional[logging.Logger] = None):
        super().__init__(config, logger)
        self._check_ants_installation()
    
    def _check_ants_installation(self) -> None:
        """Check if ANTs is properly installed in conda environment."""
        try:
            # Check antsRegistration in the appropriate conda environment
            result = self.run_command_in_env(
                command=["which", "antsRegistration"],
                env_name="ants",
                capture_output=True
            )
            self.logger.debug(f"ANTs found at: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            self.logger.warning("ANTs not found in 'ants' environment, but will try to use conda run for commands") 