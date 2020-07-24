#!/bin/bash

#SBATCH --job-name=os2
#SBATCH --output=JobInfo/%x_%a.out
#SBATCH --error=JobInfo/%x_%a.err
#SBATCH --array=0-329
#SBATCH --ntasks=1
#SBATCH -p konings,owners,normal
#SBATCH --time=8:00:00
#SBATCH --mem-per-cpu=2000

######################
# Begin work section #
######################

# Print this sub-job's task ID
echo "GRID: " $SLURM_ARRAY_TASK_ID >> OSSE2.out
python OSSE.py 2 
~
