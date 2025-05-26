"""
Setup script for SubTract: Microstructure-informed tractography pipeline.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="subtract",
    version="1.0.0",
    author="SubTract Development Team",
    author_email="oozalay@unmc.edu",
    description="A Python implementation of microstructure-informed tractography for subcortical connectomics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/subtract",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=1.0.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.0.0",
        ],
        "jupyter": [
            "jupyter>=1.0.0",
            "ipywidgets>=8.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "subtract=subtract.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "subtract": [
            "data/templates/*",
            "data/rois/*",
            "configs/*.yaml",
        ],
    },
    keywords="neuroimaging tractography diffusion-mri connectomics",
    project_urls={
        "Bug Reports": "https://github.com/your-org/subtract/issues",
        "Source": "https://github.com/your-org/subtract",
        "Documentation": "https://subtract.readthedocs.io/",
    },
) 