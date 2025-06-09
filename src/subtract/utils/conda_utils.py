"""
Conda environment utilities for tool execution.

This module provides utilities for running commands in specific conda environments,
which is necessary for tools that have conflicting dependencies.
"""

import logging
import subprocess
import shlex
from pathlib import Path
from typing import List, Optional, Union, Dict

logger = logging.getLogger(__name__)


def get_conda_command(
    command: Union[str, List[str]], 
    env_name: str = "subtract"
) -> List[str]:
    """
    Wrap a command to run in a specific conda environment.
    
    Args:
        command: Command to run (string or list)
        env_name: Name of conda environment
        
    Returns:
        Command list wrapped with conda activation
    """
    if isinstance(command, str):
        command_list = shlex.split(command)
    else:
        command_list = command
    
    # Use conda run to execute in specific environment
    # This properly handles environment switching and deactivation
    conda_cmd = [
        "conda", "run", "-n", env_name, "--no-capture-output"
    ] + command_list
    
    return conda_cmd


def run_in_conda_env(
    command: Union[str, List[str]],
    env_name: str = "subtract",
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a command in a specific conda environment.
    
    Args:
        command: Command to run
        env_name: Conda environment name
        cwd: Working directory
        env: Environment variables
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        
    Returns:
        CompletedProcess result
    """
    conda_cmd = get_conda_command(command, env_name)
    
    logger.debug(f"Running in conda env '{env_name}': {' '.join(conda_cmd)}")
    
    try:
        result = subprocess.run(
            conda_cmd,
            cwd=cwd,
            env=env,
            capture_output=capture_output,
            text=True,
            check=check
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed in conda env '{env_name}': {' '.join(conda_cmd)}")
        logger.error(f"Return code: {e.returncode}")
        if e.stdout:
            logger.error(f"Stdout: {e.stdout}")
        if e.stderr:
            logger.error(f"Stderr: {e.stderr}")
        raise


# Environment mapping for different tools
TOOL_ENVIRONMENTS = {
    # ANTs tools - use dedicated ants environment
    "antsRegistrationSyNQuick.sh": "ants",
    "ConvertTransformFile": "ants", 
    "antsRegistration": "ants",
    "antsApplyTransforms": "ants",
    
    # MRtrix3 tools
    "mrconvert": "subtract",
    "dwi2response": "subtract", 
    "dwi2fod": "subtract",
    "mrcat": "subtract",
    "mtnormalise": "subtract",
    "5ttgen": "subtract",
    "dwiextract": "subtract",
    "mrmath": "subtract",
    "transformconvert": "subtract",
    "mrtransform": "subtract",
    "5tt2gmwmi": "subtract",
    "dwidenoise": "subtract",
    "tckgen": "subtract",
    "tcksift2": "subtract",
    "tck2connectome": "subtract",
    
    # MDT tools - use dedicated mdt environment
    "mdt": "mdt",
    "mdt-create-protocol": "mdt",
    "mdt-create-mask": "mdt",
    "mdt-fit-model": "mdt",
    "mdt-model-fit": "mdt",
    
    # FSL tools (use subtract environment)
    "fslroi": "subtract",
    "fslmerge": "subtract", 
    "fslmaths": "subtract",
    "topup": "subtract",
    "applytopup": "subtract",
    "eddy": "subtract",
    "eddy_cuda": "subtract",
    "bet": "subtract",
    "flirt": "subtract",
    "fnirt": "subtract",
}


def get_tool_environment(command: Union[str, List[str]]) -> str:
    """
    Get the appropriate conda environment for a command.
    
    Args:
        command: Command to run
        
    Returns:
        Environment name
    """
    if isinstance(command, str):
        tool_name = shlex.split(command)[0]
    else:
        tool_name = command[0]
    
    # Handle special cases for shell commands
    if tool_name in ["sh", "bash"]:
        return "subtract"
    
    return TOOL_ENVIRONMENTS.get(tool_name, "subtract")


def run_tool_command(
    command: Union[str, List[str]],
    cwd: Optional[Path] = None,
    env: Optional[Dict[str, str]] = None,
    capture_output: bool = True,
    check: bool = True
) -> subprocess.CompletedProcess:
    """
    Run a tool command in the appropriate conda environment.
    
    This function automatically determines the correct conda environment
    based on the tool being used.
    
    Args:
        command: Command to run
        cwd: Working directory
        env: Environment variables
        capture_output: Whether to capture stdout/stderr
        check: Whether to raise exception on non-zero exit
        
    Returns:
        CompletedProcess result
    """
    env_name = get_tool_environment(command)
    
    return run_in_conda_env(
        command=command,
        env_name=env_name,
        cwd=cwd,
        env=env,
        capture_output=capture_output,
        check=check
    ) 