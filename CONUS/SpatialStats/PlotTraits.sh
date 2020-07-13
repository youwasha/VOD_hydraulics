#!/bin/bash

#SBATCH --job-name=trait
#SBATCH --output=JobInfo/%x_%a.out
#SBATCH --error=JobInfo/%x_%a.err
#SBATCH --array=0-14
#SBATCH --ntasks=1
#SBATCH -p owners,normal
#SBATCH --time=0:30:00
#SBATCH --mem-per-cpu=1000

######################
# Begin work section #
######################

# Print this sub-job's task ID
echo "GRID: " $SLURM_ARRAY_TASK_ID >> PlotTraits.out
python PlotTraits.py
~
