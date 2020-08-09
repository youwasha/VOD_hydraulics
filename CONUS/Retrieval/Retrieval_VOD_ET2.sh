#!/bin/bash

#SBATCH --job-name=vod_et2
#SBATCH --output=JobInfo/%x_%a.out
#SBATCH --error=JobInfo/%x_%a.err
#SBATCH --array=0-999
#SBATCH --ntasks=1
#SBATCH -p konings,owners,normal
#SBATCH --time=20:00:00
#SBATCH --mem-per-cpu=2000

######################
# Begin work section #
######################

# Print this sub-job's task ID
echo "GRID: " $SLURM_ARRAY_TASK_ID >> Retrieval_VOD_ET.out
python Retrieval_VOD_ET.py 7
python Retrieval_VOD_ET.py 8
python Retrieval_VOD_ET.py 9
python Retrieval_VOD_ET.py 10
python Retrieval_VOD_ET.py 11
python Retrieval_VOD_ET.py 12
python Retrieval_VOD_ET.py 13
