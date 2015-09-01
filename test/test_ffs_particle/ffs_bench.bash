#!/bin/bash -l

#run the ffs calculation many times.

rm -f ffs_bench.dat
for i in `seq 1 1000`
do

python ../../server/main_server.py -c ffs_particle_server.conf >c 2>&1 &
python main_particle.py 
grep -A 1 "# k_AB" c | tail -n 1 >> ffs_bench.dat

done 

mean=$(awk -F : '{t+=$NF;c++}END{print t/c}' ffs_bench.dat)
stde=$(awk -F :  -v m=$m '{t+=($NF-m)*($NF-m);c++}END{print sqrt(t)/c}' ffs_bench.dat)
count=$(wc -l ffs_bench.dat | awk '{print $1}')

echo "Rate from PERM is: $mean p/m $stde over $count runs"


