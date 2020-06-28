#!/bin/bash

#SBATCH --job-name=instat
#SBATCH --output=JobInfo/%x_%a.out
#SBATCH --error=JobInfo/%x_%a.err
#SBATCH --array=0-13
#SBATCH --ntasks=1
#SBATCH -p konings,owners,normal
#SBATCH --time=0:15:00
#SBATCH --mem-per-cpu=1000

######################
# Begin work section #
######################

# Print this sub-job's task ID
echo "GRID: " $SLURM_ARRAY_TASK_ID >> InputStats.out
python InputStats.py
~