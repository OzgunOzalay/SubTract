#! /bin/bash
# mrtrix 3 connectome 

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 010:${Color_Off} Registering ROIs and creating combined parcellation mrtrix3:"
echo -e "\n"

export SUBJECTS_DIR="$result_dir"/FS/subjects

while IFS= read -r subject
do

  mrtrix_dir="$analysis_dir"/"$subject"/dwi/mrtrix3
  roi_dir="$script_dir"/ROIs

  # Create folder for the ROIs
  if [ ! -d "$mrtrix_dir"/ROIs ]; then
      mkdir -p "$mrtrix_dir"/ROIs
  fi

  # Go to the folder
  cd "$mrtrix_dir"/ROIs || exit

  
  
  # bnst_regions=("L_amygdala_fsaverage" \
  #               "R_amygdala_fsaverage" \
  #               "L_hippocampus_fsaverage" \
  #               "R_hippocampus_fsaverage" \
  #               "L_vmPFC_fsaverage" \
  #               "R_vmPFC_fsaverage" \
  #               "L_insula_fsaverage" \
  #               "R_insula_fsaverage" \
  #               "L_hypothalamus_fsaverage" \
  #               "R_hypothalamus_fsaverage" \
  #               "L_bnst_fsaverage" \
  #               "R_bnst_fsaverage")

  # for ROI in "${bnst_regions[@]}"; do
  #   mri_binarize --i "$roi_dir"/"$ROI".nii.gz --match 1 --o "${ROI}.nii.gz"
  #   mrtransform "${ROI}.nii.gz" --template "$mrtrix_dir"/mean_b0_brain.mif \
  #       -linear "$mrtrix_dir"/fs2diff_mrtrix.txt \
  #       -interp nearest \
  #       "${ROI:0:-10}_DWI.mif" \
  #       -force
  # done

  # Create left and right hemisphere parcellations
  echo "Creating left and right hemisphere parcellation files..."

  # Create zero images to start
  mrcalc L_amygdala_DWI.mif 0 -mult left_bnst_network_parcellation.mif -force
  mrcalc R_amygdala_DWI.mif 0 -mult right_bnst_network_parcellation.mif -force

  # Left hemisphere parcellation
  mrcalc L_amygdala_DWI.mif 1 -eq left_bnst_network_parcellation.mif 0 -eq -mult 1 -mult left_bnst_network_parcellation.mif -add left_bnst_network_parcellation.mif -force
  mrcalc L_hippocampus_DWI.mif 1 -eq left_bnst_network_parcellation.mif 0 -eq -mult 2 -mult left_bnst_network_parcellation.mif -add left_bnst_network_parcellation.mif -force
  mrcalc L_vmPFC_DWI.mif 1 -eq left_bnst_network_parcellation.mif 0 -eq -mult 3 -mult left_bnst_network_parcellation.mif -add left_bnst_network_parcellation.mif -force
  mrcalc L_insula_DWI.mif 1 -eq left_bnst_network_parcellation.mif 0 -eq -mult 4 -mult left_bnst_network_parcellation.mif -add left_bnst_network_parcellation.mif -force
  mrcalc L_hypothalamus_DWI.mif 1 -eq left_bnst_network_parcellation.mif 0 -eq -mult 5 -mult left_bnst_network_parcellation.mif -add left_bnst_network_parcellation.mif -force

  # Right hemisphere parcellation
  mrcalc R_amygdala_DWI.mif 1 -eq right_bnst_network_parcellation.mif 0 -eq -mult 1 -mult right_bnst_network_parcellation.mif -add right_bnst_network_parcellation.mif -force
  mrcalc R_hippocampus_DWI.mif 1 -eq right_bnst_network_parcellation.mif 0 -eq -mult 2 -mult right_bnst_network_parcellation.mif -add right_bnst_network_parcellation.mif -force
  mrcalc R_vmPFC_DWI.mif 1 -eq right_bnst_network_parcellation.mif 0 -eq -mult 3 -mult right_bnst_network_parcellation.mif -add right_bnst_network_parcellation.mif -force
  mrcalc R_insula_DWI.mif 1 -eq right_bnst_network_parcellation.mif 0 -eq -mult 4 -mult right_bnst_network_parcellation.mif -add right_bnst_network_parcellation.mif -force
  mrcalc R_hypothalamus_DWI.mif 1 -eq right_bnst_network_parcellation.mif 0 -eq -mult 5 -mult right_bnst_network_parcellation.mif -add right_bnst_network_parcellation.mif -force

  echo "Left and right hemisphere parcellation files created successfully"

done < <(grep -v '^ *#' subj_list.txt)


echo -e "\n"
echo -e "${Green}Step 010 completed!"
echo -e "${Color_Off}###################\n"