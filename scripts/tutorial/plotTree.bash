#!/bin/bash

FRESHS=.

##read the tau in as an argument
if [ "$#" -eq "1" ]
then
    tau=$1
else
    echo "plotTree.bash: require 1 argument: tau."
    exit
fi

##get the most recent DB file
file=$(ls -t ../../server/DB/*config*.sqlite | head -1)
echo "Using"
ls -lh $file

##build the tree
../spres_buildTree.py $file $tau > tmp.dat


##plot it
gnuplot << EOF_G
set size 0.6
set xlabel 'tau'
set ylabel 'RC'
set terminal postscript eps color enhanced
set output 'tree.eps'
plot 'tmp.dat' w l notitle
EOF_G

echo "Plotted tree should now be in the file 'tree.eps'."





