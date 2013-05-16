#!/bin/bash



file=$(ls ../../server/OUTPUT/*stateVec*.dat | tail -1)

##add a third column with the timecount in it
awk 'BEGIN{c=0}NF>0{print c/2,$1,$4}NF==0{c++;if(c%2==1){print}}'\
 $file > tmpSa.dat

##get the xsize
tMax=$(tail tmpSa.dat  | awk 'NF==3{print $1}' | tail -1)

##get the ysize
binMax=$(tail tmpSa.dat  | awk 'NF==3{print $2}' | tail -1)


##make the plot
gnuplot << EOF_G
set size 0.6
set terminal postscript eps color enhanced
set output 'sampling.eps'
set xlabel 'timestep'
set ylabel 'bin index'
set title 'Sampling Density'
set pm3d map
set xtics nomirror
set ytics nomirror
set xrange [0:$tMax]
set yrange [0:$binMax]
set pm3d corners2color c4
splot 'tmpSa.dat' w pm3d notitle
EOF_G

echo "Sampling plot should now be in the file 'sampling.eps'"






