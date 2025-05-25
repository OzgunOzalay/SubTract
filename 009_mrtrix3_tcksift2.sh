#! /bin/bash
# mrtrix 3 tracking

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 009:${Color_Off} Refine tracking with tcksift2:"
echo -e "\n"

while IFS= read -r subject
do

        mrtrix_dir="$analysis_dir"/"$subject"/dwi/mrtrix3
        noddi_dir="$analysis_dir"/"$subject"/dwi/mdt/output/"$subject"_brain_mask/NODDIDA


        # Go to the folder
        cd "$mrtrix_dir" || exit
        
        # Create a mask that weights voxels based on NDI
        mrcalc "$noddi_dir"/NDI.nii.gz 0.1 -gt 5tt_coreg_fs_ants.mif -mult ndi_5tt_mask.mif -force


        # Refining the combined_BNST_tracks Streamlines with tcksift2
        tcksift2 -proc_mask ndi_5tt_mask.mif \
                -out_mu sift_mu_5M_BNST_L.txt \
                -out_coeffs sift_coeffs_5M_BNST_L.txt \
                -nthreads 24 \
                tracks_5M_BNST_L.tck \
                wmfod_norm.mif \
                sift_5M_BNST_L.txt

        tcksift2 -proc_mask ndi_5tt_mask.mif \
                -out_mu sift_mu_5M_BNST_R.txt \
                -out_coeffs sift_coeffs_5M_BNST_R.txt \
                -nthreads 24 \
                tracks_5M_BNST_R.tck \
                wmfod_norm.mif \
                sift_5M_BNST_R.txt


done < <(grep -v '^ *#' subj_list_2122.txt)


echo -e "\n"
echo -e "${Green}Step 009 completed!"
echo -e "${Color_Off}###################\n"