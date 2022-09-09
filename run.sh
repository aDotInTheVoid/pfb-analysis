#!/bin/bash
PF=~/profuzzbench
PFA=~/pfb-analysis
source $PF/venv/bin/activate

# Must come after
set -eoux pipefail

# rm -rf results
# curl -OL http://mars.doc.ic.ac.uk:8000/archive.tar.xz
# tar xf archive.tar.xz

for i in results-long/*
do
    pushd $i
    subj=$(basename $i)
    # $PF/scripts/analysis/profuzzbench_generate_csv.sh $subj 4 snapfuzz results.csv 0
    # $PF/scripts/analysis/profuzzbench_generate_csv.sh $subj 4 aflnet   results.csv 1
    $PFA/profuzzbench_plot.py -i results.csv -p $subj -r 4 -c 480 -s 1  -o cov_pres.png
    popd
    ./subject.py $i
done
