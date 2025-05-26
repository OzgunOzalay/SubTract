"""
SubTract: A Python implementation of microstructure-informed tractography 
for subcortical connectomics.

This package provides a complete pipeline for white matter tractography analysis
with a focus on the BNST (Bed Nucleus of the Stria Terminalis) and amygdala.
"""

__version__ = "1.0.0"
__author__ = "SubTract Development Team"
__email__ = "oozalay@unmc.edu"

from .core.pipeline_runner import PipelineRunner
from .core.subject_manager import SubjectManager
from .config.settings import SubtractConfig

__all__ = [
    "PipelineRunner",
    "SubjectManager", 
    "SubtractConfig",
] 