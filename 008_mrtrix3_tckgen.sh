#! /bin/bash
# mrtrix 3 tracking

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 008:${Color_Off} Tracking Subject with mrtrix3:"
echo -e "\n"

while IFS= read -r subject
do

        # Go to the folder
        cd "$analysis_dir"/"$subject"/dwi/mrtrix3 || exit


        # tckgen Local tracking
        BNST_L="$analysis_dir"/"$subject"/dwi/Reg/ROIs/BNST_L_DWI
        BNST_R="$analysis_dir"/"$subject"/dwi/Reg/ROIs/BNST_R_DWI

        mrconvert "$BNST_L".nii.gz "$BNST_L".mif -force
        mrconvert "$BNST_R".nii.gz "$BNST_R".mif -force


        echo -e "\n"
        echo -e "${BPurple}Tracking from BNST Left:${Color_Off} for ${BWhite}$subject${Color_Off}"
        tckgen  -act 5tt_coreg_fs_ants.mif \
                -backtrack \
                -seed_image "$BNST_L".mif \
                -nthreads 24 \
                -select 5000000 \
                -force \
                wmfod_norm.mif \
                tracks_5M_BNST_L.tck

        echo -e "\n"
        echo -e "${BPurple}Tracking from BNST Right:${Color_Off} for ${BWhite}$subject${Color_Off}"
        tckgen  -act 5tt_coreg_fs_ants.mif \
                -backtrack \
                -seed_image "$BNST_R".mif \
                -nthreads 24 \
                -select 5000000 \
                -force \
                wmfod_norm.mif \
                tracks_5M_BNST_R.tck

done < <(grep -v '^ *#' subj_list.txt)

echo -e "\n"
echo -e "${Green}Step 008 completed!"
echo -e "${Color_Off}###################\n"