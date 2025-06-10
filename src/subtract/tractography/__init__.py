"""
Tractography module for SubTract pipeline.

This module implements white matter tractography using MRtrix3, including:
- ROI-based seed point generation
- Probabilistic tracking with anatomical constraints
- Track filtering and refinement
"""

from .track_generator import TrackGenerator

__all__ = ["TrackGenerator"] 