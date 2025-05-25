#! /bin/bash

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 005:${Color_Off} Registering MNI <=> DWI for:"
echo -e "\n"

while IFS= read -r subject
do

  echo -e "$subject"

  # Create folder for registration matrices and outputs
  reg_folder=$analysis_dir/$subject/dwi/Reg
  roi_folder=$analysis_dir/$subject/dwi/Reg/ROIs
  mkdir -p "$roi_folder"

  cd "$reg_folder" || exit

  # Register MNI152 to subject nodif_brain
  nodif_brain=$analysis_dir/$subject/dwi/Eddy/"$subject"_brain.nii.gz
  template=$script_dir/Templates/MNI152_T1_1mm_brain.nii.gz

  antsRegistrationSyNQuick.sh -d 3 \
                              -f "$nodif_brain" \
                              -m "$template" \
                              -o MNI2DWI_ \
                              -t s

  # Use reg matrices to transform ROIs from MNI to individual DTI space
    declare -a ROIArray=("Amyg_L_MNI" "Amyg_R_MNI" \
                        "BNST_L_MNI" "BNST_R_MNI" \
                        "Hipp_L_MNI" "Hipp_R_MNI" \
                        "Insl_L_MNI" "Insl_R_MNI" \
                        "vmPF_L_MNI" "vmPF_R_MNI" \
                        "Hypo_L_MNI" "Hypo_R_MNI")

  for ROI in "${ROIArray[@]}" ; do

    warp=$reg_folder/MNI2DWI_1Warp.nii.gz
    affn=$reg_folder/MNI2DWI_0GenericAffine.mat
    atlas_roi=$script_dir/ROIs/"$ROI".nii.gz

    echo -e "Transforming: "$atlas_roi" to "$nodif_brain""

    antsApplyTransforms \
      -d 3 \
      -i "$atlas_roi" \
      -r "$nodif_brain" \
      -t "$warp" \
      -t "$affn" \
      -n GenericLabel \
      -o "$roi_folder"/"${ROI:0:7}"DWI.nii.gz

  done

done < <(grep -v '^ *#' subj_list.txt)

echo -e "\n"
echo -e "${Green}Step 005 completed!"
echo -e "${Color_Off}###################\n"