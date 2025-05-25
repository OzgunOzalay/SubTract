#! /bin/bash
# Microstructure Diffusion Toolbox (MDT) pre-processing

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 006:${Color_Off} Process Subject with mdt:"
echo -e "\n"


while IFS= read -r subject
do

    echo -e "$subject"

    # Create mdt folder for the subject
    mdt_dir="$analysis_dir"/"$subject"/dwi/mdt
    if [ ! -d "$mdt_dir" ]; then
        mkdir -p "$mdt_dir"
    fi


    # Copy data to the folder
    eddy_dir="$analysis_dir"/"$subject"/dwi/Eddy
    cp "$eddy_dir"/"$subject"_eddy_unwarped.nii.gz "$mdt_dir"/"$subject".nii.gz
    cp "$eddy_dir"/"$subject"_dwi.bval "$mdt_dir"/"$subject".bval
    cp "$eddy_dir"/"$subject"_dwi.bvec "$mdt_dir"/"$subject".bvec
    cp "$eddy_dir"/"$subject"_brain_mask.nii.gz "$mdt_dir"/"$subject"_brain_mask.nii.gz
    
    # Go to the folder
    cd "$mdt_dir" || exit

    # Create protocol file
    mdt-create-protocol "$subject".bvec "$subject".bval
    
    # Fit NODDI model
    mdt-model-fit NODDIDA "$subject".nii.gz "$subject".prtcl "$subject"_brain_mask.nii.gz

done < <(grep -v '^ *#' subj_list.txt)


echo -e "\n"
echo -e "${Green}Step 006 completed!"
echo -e "${Color_Off}###################\n"