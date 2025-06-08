#! /bin/bash

# Eddy current correction for DWI data
# It uses the FSL Eddy tool to correct for eddy current distortions in the DWI data.
# It also generates a QC report for the corrected data.


# Disable warning about unused variables
# shellcheck disable=SC2154
cd "$analysis_dir" || exit

echo -e "\n"
echo -e "${BWhite}Step 004:${Color_Off} Eddy current correction for Subject:"
echo -e "\n"


while IFS= read -r subject
do

	echo -e "$subject"

	subj_num=${subject: -4}


		echo -e "${BWhite}Subject:${Color_Off} $subject has 2 encoding directions"
		echo -e "${BWhite}Running Eddy current correction for this subject${Color_Off}"

		# Create Eddy folders
		dwi_dir="$analysis_dir"/"$subject"/dwi
		topup_dir="$analysis_dir"/"$subject"/dwi/Topup
		eddy_dir="$analysis_dir"/"$subject"/dwi/Eddy
		mkdir -p "$eddy_dir"

		# Copy DWI scan, bvals, bvecs and generate acq_params
		cp "$topup_dir"/"$subject"_topup_dwi.nii.gz \
			"$eddy_dir"/"$subject"_dwi.nii.gz
		cp "$dwi_dir"/"$subject"_dir-AP_dwi.bval \
			"$eddy_dir"/"$subject"_dwi.bval
		cp "$dwi_dir"/"$subject"_dir-AP_dwi.bvec \
			"$eddy_dir"/"$subject"_dwi.bvec
		cp "$topup_dir"/acq_params.txt \
			"$eddy_dir"/acq_params.txt
		cp "$topup_dir"/"$subject"_dir-AP-PA_dwi_Topup_fieldcoef.nii.gz \
			"$eddy_dir"/"$subject"_dir-AP-PA_dwi_Topup_fieldcoef.nii.gz
		cp "$topup_dir"/"$subject"_dir-AP-PA_dwi_Topup_movpar.txt \
			"$eddy_dir"/"$subject"_dir-AP-PA_dwi_Topup_movpar.txt


		# Extract B0 Image 
		fslroi "$eddy_dir"/"$subject"_dwi.nii.gz "$eddy_dir"/"$subject"_1stVol 0 1

		# Create a brain mask
		bet "$eddy_dir"/"$subject"_1stVol "$eddy_dir"/"$subject"_brain -m -f 0.2

		# Create index file, number of rows is equal to the 4th dim of the image
		yes 1 | head -n 100 > "$eddy_dir"/index.txt

		# Run eddy current correction
		cd "$eddy_dir" || exit

		eddy_cuda10.2 --imain="$subject"_dwi \
			--mask="$subject"_brain_mask.nii.gz\
			--index=index.txt\
			--acqp=acq_params.txt\
			--bvecs="$subject"_dwi.bvec\
			--bvals="$subject"_dwi.bval\
			--topup="$subject"_dir-AP-PA_dwi_Topup\
			--flm=quadratic\
			--out="$subject"_eddy_unwarped\
			--data_is_shelled

		echo -e "Eddy current correction finished for subject\n"
		


done < <(grep -v '^ *#' subj_list.txt)

echo -e "\n"
# shellcheck disable=SC2154
echo -e "${Green}Step 004 completed!"
echo -e "${Color_Off}###################\n"