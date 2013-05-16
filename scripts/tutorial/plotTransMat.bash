#!/bin/bash

##get the most recent transmat file
file=$(ls ../../server/OUTPUT/*transMat*.dat | tail -1)

##get the most recent timepoint in a format gnuplot will like.
awk 'BEGIN{done=0;top=0}\
NF>0{if(done==1){done=0;for(i=0;i<=top;i++){for(j=0;j<=top;j++){m[i,j]=0}}}\
     else{if($1>top){\
            for(i=top+1;i<=$1;i++){for(j=0;j<=$1;j++){m[i,j]=0}}\
            for(i=0;i<=$1;i++){for(j=top+1;j<=$1;j++){m[i,j]=0}}\
            top=$1}\
          if($2>top){\
            for(i=top+1;i<=$2;i++){for(j=0;j<=$2;j++){m[i,j]=0}}\
            for(i=0;i<=$2;i++){for(j=top+1;j<=$2;j++){m[i,j]=0}}\
            top=$2}\
          m[$1,$2]=$3}}\
NF==0{done=1}\
END{for(i=0;i<=top;i++){for(j=0;j<=top;j++){print i,j,m[i,j]}printf "\n"}}'\
 $file > tmpTM.dat

##get the matrix size
bMax=$(tail tmpTM.dat  | awk 'NF==3{print $1}' | tail -1)

##make the plot
gnuplot << EOF_G
set terminal postscript eps color enhanced
set output 'transMat.eps'
set size 0.6
set xtics nomirror
set ytics nomirror
set pm3d map
set pm3d corners2color c4
set xlabel 'source bin'
set ylabel 'dest bin'
##set cblabel 'M[i,j]'
set title 'Transition Matrix'
set size square
set xrange [0:$bMax]
set yrange [0:$bMax]
splot 'tmpTM.dat' w pm3d notitle
EOF_G

echo "plot should now be saved to file 'transMat.eps'"





