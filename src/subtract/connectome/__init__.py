"""
Connectome generation module for SubTract pipeline.

This module handles Step 011: Creation of connectivity matrices and fingerprints
by combining microstructural metrics with tractography data.
"""

from .connectivity_matrix import ConnectivityMatrix

__all__ = ["ConnectivityMatrix"] 