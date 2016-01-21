#!/bin/bash -l

#run the perm calculation many times.

NRUNS=1

echo "#k_AB ffs_pB perm_pB" > perm_bench.dat
for i in `seq 1 $NRUNS`
do

python ../../server/main_server.py -c permffs_particle_server.conf >server.log 2>&1 &
sleep 1
python main_particle.py >client.log 

ffs_pB=$(cat OUTPUT/rates.dat | tail -n 10 | awk 'BEGIN{r=1}{r*=$6;print $1,$6,r}')
perm_pB=$(grep renormed server.log | awk 'BEGIN{r=1}{r*=$NF;print NR,$NF,r}')
k_AB=$(grep -A 1 "# k_AB" server.log | tail -n 1)

echo "$k_AB $ffs_pB $perm_pB" >> perm_bench.dat

done 

mean=$(awk          '{t+=$1;c++}END{print t/c}' perm_bench.dat)
stde=$(awk  -v m=$m '{t+=($1-m)*($1-m);c++}END{print sqrt(t)/c}' perm_bench.dat)
count=$(wc -l perm_bench.dat | awk '{print $1}')

echo "Rate from PERM is: $mean p/m $stde over $count runs"


