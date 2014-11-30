#!/bin/bash
#This test contains a full run of the ABX pipeline in command line
#with randomly created database and features


# directories
curdir=`pwd`
ABXdir=$curdir/../ABXpy
filesdir=$curdir/example_items

# files
item_file=$filesdir/data.item
feature_file=$filesdir/data.features
distance_file=$filesdir/data.distance
score_file=$filesdir/data.score
task_file=$filesdir/data.abx
analyze_file=$filesdir/data.csv

# Generating task file
echo python $ABXdir/task.py $item_file $task_file -o c0 -a c1 -b c2 -v 1 --features $feature_file
python $ABXdir/task.py $item_file $task_file -o c0 -a c1 -b c2 -v 1 --features $feature_file

# Computing distances
echo python $ABXdir/distance.py $feature_file $item_file $distance_file -d cosine
python $ABXdir/distance.py $feature_file $task_file $distance_file -d cosine

# Calculating the score
echo python $ABXdir/score.py $task_file $distance_file $score_file
python $ABXdir/score.py $task_file $distance_file $score_file

# Collapsing the results
echo python $ABXdir/analyze.py $score_file $task_file $analyze_file
python $ABXdir/analyze.py $score_file $task_file $analyze_file
