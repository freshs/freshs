#!/bin/bash

n_bins=80
n_lambdas=$[n_bins - 2]
bin_min=0.0
bin_width=0.01
runs_per_bin=10

###print out a basic "Hypersurfaces" section for a control file
echo "[hypersurfaces]"
echo "lambdacount = $n_lambdas"
echo "borderA     = $bin_min"
lambda=$bin_min
for i in `seq 1 $n_lambdas`
do
    lambda=$(echo $lambda $bin_width | awk '{print $1+$2}')
echo "lambda$i     = $lambda"
done
lambda=$(echo $lambda $bin_width | awk '{print $1+$2}')
echo "borderB     = $lambda"
echo
echo

###print out a basic "Runs_per_interface" section for a control file
echo "[runs_per_interface]"
echo "borderA = $runs_per_bin"
echo "borderB = $runs_per_bin"
for i in `seq 1 $n_lambdas`
do
echo "lambda$i = $runs_per_bin"
done



