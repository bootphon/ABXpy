#!/bin/bash
#
# This test contains a full run of the ABX pipeline in command line
# with randomly created database and features

set -e

cd "$( dirname "${BASH_SOURCE[0]}" )"

# input files already here
item=example_items/data.item
features=example_items/data.features

# output files produced by ABX
task=example_items/data.abx
distance=example_items/data.distance
score=example_items/data.score
analyze=example_items/data.csv

# generating task file
abx-task $item $task --verbose --on c0 --across c1 --by c2

# computing distances
abx-distance $features $task $distance --normalization 1 --njobs 1

# calculating the score
abx-score $task $distance $score

# collapsing the results
abx-analyze $score $task $analyze
