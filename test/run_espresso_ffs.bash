#!/bin/bash

echo "Searching for Espresso executable to run test...."
ESPRESSO_PATH=$(which Espresso)
if [ -a "$ESPRESSO_PATH" ]
then
       echo "found espresso at: $ESPRESSO_PATH" 
else
       echo "Searching home directory....."
       ESPRESSO_PATH=$(find ~/[E,e]spresso* /usr/local/[E,e]ffss* -name "Espresso"  | head -1)
       echo ""
       echo "Using the first Espresso executable located: $ESPRESSO_PATH"
       echo ""
fi



./test_freshs.bash  -w -k -l espresso_ffs_log.txt\
                          -r test_espresso_ffs/espresso_ffs_ref.sqlite\
                          -c test_espresso_ffs/espresso_ffs.conf \
                          -s test_espresso_ffs/example_initial_config.dat \
                          -h ../harnesses/espresso_sample \
                          -e $ESPRESSO_PATH \
                          -p bench_$tmax.txt


