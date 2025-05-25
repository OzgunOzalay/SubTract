#! /bin/bash
# mrtrix 3 pre-processing

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 007:${Color_Off} Pre-process Subject with mrtrix3:"
echo -e "\n"


while IFS= read -r subject
do

    echo -e "$subject"

    mrtrix_dir="$analysis_dir"/"$subject"/dwi/mrtrix3
    mdt_dir="$analysis_dir"/"$subject"/dwi/mdt
    
    # Remove mrtrix_dir
    rm -rf "$mrtrix_dir"
    
    # Create folder for the subject
    if [ ! -d "$mrtrix_dir" ]; then
        mkdir -p "$mrtrix_dir"
    fi


    # Copy data to the folder
    cp "$mdt_dir"/"$subject".nii.gz "$mrtrix_dir"/"$subject".nii.gz
    cp "$mdt_dir"/"$subject".bvec "$mrtrix_dir"/"$subject".bvec
    cp "$mdt_dir"/"$subject".bval "$mrtrix_dir"/"$subject".bval
    cp "$mdt_dir"/"$subject"_brain_mask.nii.gz "$mrtrix_dir"/"$subject"_brain_mask.nii.gz

    # Go to the folder
    cd "$mrtrix_dir" || exit

    # Convert data to mif format
    mrconvert "$subject".nii.gz "$subject".mif -fslgrad "$subject".bvec "$subject".bval
    mrconvert "$subject"_brain_mask.nii.gz "$subject"_brain_mask.mif

    # dwi2response
    dwi2response dhollander "$subject".mif wm.txt gm.txt csf.txt -voxels voxels.mif

    # Fiber Orientation Density (FOD)
    # Constrained Spherical Deconvolution
    dwi2fod msmt_csd "$subject".mif -mask "$subject"_brain_mask.mif wm.txt wmfod.mif gm.txt gmfod.mif csf.txt csffod.mif

    # Combine the FOD images from all three tissue types into vf.mif
    mrconvert -coord 3 0 wmfod.mif - | mrcat csffod.mif gmfod.mif - vf.mif

    # Normalize the FODs for comparison
    mtnormalise wmfod.mif wmfod_norm.mif gmfod.mif gmfod_norm.mif csffod.mif csffod_norm.mif -mask "$subject"_brain_mask.mif

    # Generate the 5TT image
    5ttgen freesurfer \
            "$result_dir"/FS/subjects/"$subject"/mri/aseg.mgz \
            -lut "$script_dir"/Data/FreeSurferColorLUT.txt \
            5tt_nocoreg_fs.mif \
            -force
    # Coregister anatomical and diffusion images

    # We will first use the commands dwiextract and mrmath to average together the B0 images from the diffusion data
    dwiextract "$subject".mif - -bzero | mrmath - mean mean_b0.mif -axis 3 -force

    # Convert both the segmented anatomical image and the B0 images we just extracted:
    mrconvert mean_b0.mif mean_b0.nii.gz -force
    mrconvert 5tt_nocoreg_fs.mif 5tt_nocoreg_fs.nii.gz -force

    # Since flirt can only work with a single 3D image (not 4D datasets), 
    # we will use fslroi to extract the first volume of the segmented dataset, 
    # which corresponds to the Grey Matter segmentation
    fslroi 5tt_nocoreg_fs.nii.gz 5tt_fs_vol0.nii.gz 0 1


    #########################################################################
    # ANTs coregistration
    #########################################################################
    # We will use ANTs to coregister the diffusion image to the anatomical image
    # First extract the brain from the mean B0 image
    fslmaths mean_b0.nii.gz -mas "$subject"_brain_mask.nii.gz mean_b0_brain.nii.gz
    # Convert the brain image to mif format
    mrconvert mean_b0_brain.nii.gz mean_b0_brain.mif -force

    # Calculate transformation matrix
    antsRegistrationSyNQuick.sh -d 3 \
                                -f mean_b0_brain.nii.gz \
                                -m 5tt_fs_vol0.nii.gz \
                                -t r \
                                -o fs2diff_

    # Convert the transformation matrix to mrtrix format
    ConvertTransformFile 3 fs2diff_0GenericAffine.mat fs2diff_0GenericAffine.txt 
    transformconvert fs2diff_0GenericAffine.txt itk_import fs2diff_mrtrix.txt -force

    # Apply the transformation matrix to the diffusion image
    mrtransform 5tt_nocoreg_fs.mif --template mean_b0_brain.mif \
                -linear fs2diff_mrtrix.txt \
                -interp nearest \
                5tt_coreg_fs_ants.mif \
                -force
    #########################################################################
    # END OF THE ANTs COREGISTRATION
    #########################################################################

    # The last step to create the "seed" boundary - 
    # the boundary separating the grey from the white matter, 
    # which we will use to create the seeds for our streamlines
    5tt2gmwmi 5tt_coreg_fs_ants.mif gmwmSeed_coreg_fs_ants.mif \
                -force


done < <(grep -v '^ *#' subj_list.txt)


echo -e "\n"
echo -e "${Green}Step 007 completed!"
echo -e "${Color_Off}###################\n"