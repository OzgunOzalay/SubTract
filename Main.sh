#!/bin/bash

# shellcheck disable=SC1090

# This is the main script for the project:
# A Microstructure-Informed Tractography Weighting Method for Subcortical Connectomics: Application to the BNST and Amygdala
#
# The script is organized in 11 steps:
# 1-Copy Data to Analysis folders
# 2-Denoise data
# 3-TopUp - Correct distortions caused by magnetic field inhomogeneities
# 4-Eddy current correction
# 5-Template --> DTI registration
# 6-Microstructure Diffusion Toolbox (MDT) Processing
# 7-mrtrix3 pre-processing
# 8-mrtrix3 probabilistic tracking
# 9-mrtrix3 tcksift2
# 10-mrtrix3 Register BNST parcellation to DTI
# 11-mrtrix3 connectome construction

# oozalay@unmc.edu


# Declare folders here
export base_path="$(dirname "$(dirname "$(readlink -fm "$0")")")"
export data_dir=$base_path/Data
export script_dir=$base_path/Scripts
export analysis_dir=$base_path/Analysis
export result_dir=$base_path/Results
export stat_dir=$base_path/Stats


# Source helper functions and variables 
source "$script_dir"/999_Helpers.sh


# 1-Copy Data to Analysis folders
source $script_dir/001_Copy_Data.sh

# 2-Denoise data
source $script_dir/002_Denoise.sh


# 3-TopUp - Correct distortions caused by magnetic field inhomogeneities
source $script_dir/003_Topup.sh


# 4-Eddy current correction
source $script_dir/004_Eddy_Corr.sh


# 5-Template <--> DTI registration
source $script_dir/005_Reg_MNI2DWI.sh


# 6-Microstructure Diffusion Toolbox (MDT) Processing
source $script_dir/006_mdt.sh

# 7-mrtrix3 pre-processing
source $script_dir/007_mrtrix3_prep.sh


# 8-mrtrix3 probabilistic tracking
source $script_dir/008_mrtrix3_tckgen.sh

# 9-mrtrix3 tcksift2
source $script_dir/009_mrtrix3_tcksift2.sh

# 10-mrtrix3 Register BNST parcellation to DTI
source $script_dir/010_mrtrix3_BNST_reg.sh


# 11-mrtrix3 connectome
source $script_dir/011_mrtrix3_conn.sh
