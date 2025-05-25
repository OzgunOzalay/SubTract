#! /bin/bash

# It uses the FSL Topup tool to estimate the field inhomogeneity and applies it to the DWI data.


# Disable warning about unused variables
# shellcheck disable=SC2154

echo -e "\n"
echo -e "${BWhite}Step 003:${Color_Off} Field inhomogenity correction"
echo -e "\n"

cd "$analysis_dir" || exit

while IFS= read -r subject
do

	subj_num=${subject: -4}

	if [ $subj_num -lt 2000 ]; then

		echo -e "${BWhite}Subject:${Color_Off} $subject has only 1 encoding direction"
		echo -e "${BWhite}Skipping Topup for this subject${Color_Off}"

		continue

	else

		echo -e "${BWhite}Subject:${Color_Off} $subject has 2 encoding directions"
		echo -e "${BWhite}Running Topup for this subject${Color_Off}"

		cd "$analysis_dir" || exit
		mkdir -p "$subject"/dwi/Topup

		echo -e "Processing Subject: ""$subject"
		echo -e "Extracting and merging B0 images"

		fslroi "$subject"/dwi/"$subject"_dir-AP_dwi.nii "$subject"/dwi/Topup/"$subject"_dir-AP_dwi 0 1 
		fslroi "$subject"/dwi/"$subject"_dir-PA_dwi.nii "$subject"/dwi/Topup/"$subject"_dir-PA_dwi 0 1 

		cd "$subject"/dwi/Topup || exit
		# Merge AP & PA B0 images
		fslmerge -t "$subject"_dir-AP-PA_dwi "$subject"_dir-AP_dwi "$subject"_dir-PA_dwi 2>/dev/null

		# Create acquisiton parameters file. Last column is 'Total Readout Time' from .json file
		echo "0 1 0 0.0959097" > acq_params.txt
		echo "0 -1 0 0.0959097" >> acq_params.txt

		# Apply Topup
		echo -e "Calculating inhomogenity field"

		topup --imain="$analysis_dir"/"$subject"/dwi/Topup/"$subject"_dir-AP-PA_dwi \
				--datain="$analysis_dir"/"$subject"/dwi/Topup/acq_params.txt \
				--config=b02b0.cnf \
				--out="$analysis_dir"/"$subject"/dwi/Topup/"$subject"_dir-AP-PA_dwi_Topup \
				--nthr=24

		echo "Applying field to original AP phase encoded scan"
		applytopup --imain="$analysis_dir"/"$subject"/dwi/"$subject"_dir-AP_dwi.nii \
				--inindex=1 \
				--datain="$analysis_dir"/"$subject"/dwi/Topup/acq_params.txt \
				--topup="$analysis_dir"/"$subject"/dwi/Topup/"$subject"_dir-AP-PA_dwi_Topup \
				--method=jac \
				--out="$analysis_dir"/"$subject"/dwi/Topup/"$subject"_topup_dwi

		echo -e "Topup finished for subject\n"
	fi

	

done < <(grep -v '^ *#' subj_list.txt)

echo -e "\n"
echo -e "${Green}Step 003 completed!"
echo -e "${Color_Off}###################\n"