#!/bin/bash

echo "Searching for Espresso executable to run test...."

if [ "$ESPRESSO_PATH" == "" ];then
    ESPRESSO_PATH=$(which Espresso)
fi

if [ -a "$ESPRESSO_PATH" ]
then
       echo "found espresso at: $ESPRESSO_PATH" 
else
       echo "Searching home directory....."
       ESPRESSO_PATH=$(find ~/[E,e]spresso* /usr/local/[E,e]spress* -name "Espresso"  | head -1)
fi

if [ "$ESPRESSO_PATH" == "" ];then
    echo "Espresso not found. Please set ESPRESSO_PATH to the executable."
    exit 1
else
       echo ""
       echo "Using the Espresso executable located in $ESPRESSO_PATH"
       echo ""
fi


./test_freshs.bash  -w -k -l espresso_spres_log.txt\
                          -r test_espresso_spres/espresso_spres_ref.sqlite\
                          -c test_espresso_spres/espresso_spres.cfg \
                          -s test_espresso_spres/example_initial_config.dat \
                          -h ../harnesses/espresso_sample \
                          -e $ESPRESSO_PATH \
                          -p bench_$tmax.txt


