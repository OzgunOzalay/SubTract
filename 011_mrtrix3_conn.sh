#! /bin/bash
# mrtrix 3 connectome 

# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 011:${Color_Off} Creating connectivity matrix for Subject with mrtrix3:"
echo -e "\n"


while IFS= read -r subject
do
    mdt_folder="$analysis_dir"/"$subject"/dwi/mdt/output/"$subject"_brain_mask/
    mrtrix_dir="$analysis_dir"/"$subject"/dwi/mrtrix3

    # Change to the main mrtrix3 folder
    cd "$mrtrix_dir" || exit
    
    # Create composite microstructure image
    mrcalc "$mdt_folder"/NODDIDA/NDI.nii.gz 0.35 -mult \
            "$mdt_folder"/NODDIDA/ODI.nii.gz -neg 1 -add 0.25 -mult -add \
            "$mdt_folder"/BallStick_r1/w_stick0.w.nii.gz 0.25 -mult -add \
            "$mdt_folder"/BallStick_r1/w_ball.w.nii.gz -neg 1 -add 0.15 -mult -add \
            composite_microstructure.mif

    # Temporary track file
    tck_file_left=/media/ozgun/Hard_Bkup_1/Alcohol/Tracts/"$subject"/dwi/mrtrix3/tracks_5M_BNST_L.tck
    tck_file_right=/media/ozgun/Hard_Bkup_1/Alcohol/Tracts/"$subject"/dwi/mrtrix3/tracks_5M_BNST_R.tck

    # Sample the composite microstructure image along the tracks
    tcksample "$tck_file_left" \
            composite_microstructure.mif \
            track_weights_5M_BNST_L.txt \
            -stat_tck mean

    tcksample "$tck_file_right" \
            composite_microstructure.mif \
            track_weights_5M_BNST_R.txt \
            -stat_tck mean
    
    # Create connectivity matrix for the left BNST
    tck2connectome  -symmetric \
                    -zero_diagonal \
                    -scale_invnodevol \
                    -tck_weights_in track_weights_5M_BNST_L.txt \
                    tracks_5M_BNST_L.tck \
                    "$mrtrix_dir"/ROIs/L_combined_parc.mif \
                    "$subject"_BNST_L_parcel.csv \
                    -out_assignment assignments_"$subject"_BNST_L_parcel.csv

    # Create connectivity matrix for the right BNST
    tck2connectome  -symmetric \
                    -zero_diagonal \
                    -scale_invnodevol \
                    -tck_weights_in track_weights_5M_BNST_R.txt \
                    tracks_5M_BNST_R.tck \
                    "$mrtrix_dir"/ROIs/R_combined_parc.mif \
                    "$subject"_BNST_R_parcel.csv \
                    -out_assignment assignments_"$subject"_BNST_R_parcel.csv


    # Copy the connectivity matrices to the Results folder
    Parcellations_dir="$result_dir"/Network/"$subject"/Parcellations
    if [ ! -d "$Parcellations_dir" ]; then
        mkdir -p "$Parcellations_dir"
    fi

    # Copy the connectivity matrices to the Parcellations folder
    cp "$subject"_BNST_L_parcel.csv "$Parcellations_dir"/
    cp "$subject"_BNST_R_parcel.csv "$Parcellations_dir"/


    # Generate the connectivity fingerprint for the left BNST
    tck2connectome "$tck_file_left" \
                    "$mrtrix_dir"/ROIs/left_bnst_network_parcellation.mif \
                    L_BNST_fingerprint.csv \
                    -scale_invnodevol \
                    -scale_file track_weights_5M_BNST_L.txt \
                    -stat_edge mean \
                    -vector \
                    -force              

    # Generate the connectivity fingerprint for the right BNST
    tck2connectome "$tck_file_right" \
                    "$mrtrix_dir"/ROIs/right_bnst_network_parcellation.mif \
                    R_BNST_fingerprint.csv \
                    -scale_invnodevol \
                    -scale_file track_weights_5M_BNST_R.txt \
                    -stat_edge mean \
                    -vector \
                    -force

    # Copy the connectivity fingerprints to the Results folder
    cp L_BNST_fingerprint.csv "$result_dir"/Network/Fingerprints/"$subject"_L_BNST_fingerprint.csv
    cp R_BNST_fingerprint.csv "$result_dir"/Network/Fingerprints/"$subject"_R_BNST_fingerprint.csv

done < <(grep -v '^ *#' subj_list.txt)


echo -e "\n"
echo -e "${Green}Step 011 completed!"
echo -e "${Color_Off}###################\n"