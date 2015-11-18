#!/bin/bash
#This test contains a full run of the ABX pipeline in command line
#with randomly created database and features

# TODO Integrate item and feature generation in this script :
# -> a main in misc/generate_data
# -> clean filesdir before launching the pipeline

# directories
curdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ABXdir=$curdir/../ABXpy
filesdir=$curdir/data

# create filesdir if needed
mkdir -p $filesdir

# files
item_file=$filesdir/data.item
feature_file=$filesdir/data.features
distance_file=$filesdir/data.distance
score_file=$filesdir/data.score
task_file=$filesdir/data.abx
analyze_file=$filesdir/data.csv

# Generating task file
echo python $ABXdir/task.py $item_file $task_file -o c0 -a c1 -b c2 -v 1
python $ABXdir/task.py $item_file $task_file -o c0 -a c1 -b c2 -v 1

echo
echo Task done
echo

# Computing distances
echo python $ABXdir/distance.py $feature_file $item_file $distance_file -j 1
python $ABXdir/distance.py $feature_file $task_file $distance_file -j 1

echo
echo Distance done
echo

# Calculating the score
echo python $ABXdir/score.py $task_file $distance_file $score_file
python $ABXdir/score.py $task_file $distance_file $score_file

echo
echo Score done
echo

# Collapsing the results
echo python $ABXdir/analyze.py $score_file $task_file $analyze_file
python $ABXdir/analyze.py $score_file $task_file $analyze_file
