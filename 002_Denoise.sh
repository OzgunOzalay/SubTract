#!/bin/bash

# This script applies denoising to the raw DWI data.

# Disable warning about unused variables
# shellcheck disable=SC2154

set -e # Exit immediately if a command exits with a non-zero status.

# Change directory to the analysis directory
cd "$analysis_dir" || exit

# Create a subject list
find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \; > subj_list.txt

echo -e "\n"
echo -e "${BWhite}Step 002:${Color_Off} Denoising the data for:"
echo -e "\n"

while IFS= read -r subject
do

	echo -e "${BWhite}Subject:${Color_Off} $subject"

    # Denoise data
    cd "$analysis_dir"/"$subject"/dwi/ || exit
    
    # Loop over nifti files
    for file in *.nii; do

        # Check if the file is a DWI file
        if [[ $file == *"dwi"* ]]; then
            
            echo -e "${BWhite}Denoising:${Color_Off} $file"
            
            # Denoise the data using dwidenoise
            dwidenoise "$file" "${file%.nii}_denoised.nii.gz" \
                        -force \
                        -nthreads 24

        fi
    done

done < <(grep -v '^ *#' subj_list.txt)

echo -e "\n"
echo -e "${Green}Step 002 completed!"
echo -e "${Color_Off}###################\n"