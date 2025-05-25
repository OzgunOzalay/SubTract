#!/bin/bash

# This script copies the data from the Data folder to the Analysis folder

# Disable warning about unused variables
# shellcheck disable=SC2154

set -e # Exit immediately if a command exits with a non-zero status.


cd "$data_dir" || { echo "Error: Failed to access $data_dir"; exit 1; }

# Create a subject list
subj_list=$(mktemp)
find . -mindepth 1 -maxdepth 1 -type d -exec basename {} \; > "$subj_list"

echo -e "\n"
echo -e "${BWhite}Step 001:${Color_Off} Creating Analysis Folders and moving data for subject:"
echo -e "\n"

while IFS= read -r subject
do  

    echo -e "${BWhite}Subject:${Color_Off} $subject"
    # Create subject analysis folder
    mkdir -p "$analysis_dir"/"$subject"

    # Copy folders
    cp -R "$data_dir"/"$subject"/ "$analysis_dir"/


done < "$subj_list"

echo -e "\n"
echo -e "${Green}Step 001 completed!"
echo -e "${Color_Off}###################\n"

