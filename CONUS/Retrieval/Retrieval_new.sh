#!/bin/bash

#SBATCH --job-name=Ra705
#SBATCH --output=JobInfo/%x_%a.out
#SBATCH --error=JobInfo/%x_%a.err
#SBATCH --array=0-999
#SBATCH --ntasks=1
#SBATCH -p konings,owners,normal
#SBATCH --time=15:00:00
#SBATCH --mem-per-cpu=2000

######################
# Begin work section #
######################

# Print this sub-job's task ID
echo "GRID: " $SLURM_ARRAY_TASK_ID >> Retrieval_new.out
python Retrieval_continue.py 0
python Retrieval_continue.py 1
python Retrieval_continue.py 2
python Retrieval_continue.py 3
python Retrieval_continue.py 4
python Retrieval_continue.py 5
python Retrieval_continue.py 6

