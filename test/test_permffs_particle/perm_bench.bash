#!/bin/bash -l

#run the perm calculation many times.

NRUNS=1

rm -f perm_bench.dat
for i in `seq 1 $NRUNS`
do

python ../../server/main_server.py -c permffs_particle_server.conf &

sleep 1
#>c 2>&1 &
python main_particle.py >client.log 
grep -A 1 "# k_AB" c | tail -n 1 >> perm_bench.dat

done 

mean=$(awk          '{t+=$NF;c++}END{print t/c}' perm_bench.dat)
stde=$(awk  -v m=$m '{t+=($NF-m)*($NF-m);c++}END{print sqrt(t)/c}' perm_bench.dat)
count=$(wc -l perm_bench.dat | awk '{print $1}')

echo "Rate from PERM is: $mean p/m $stde over $count runs"


