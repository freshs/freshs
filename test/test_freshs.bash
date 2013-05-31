#!/bin/bash
# Copyright (c) 2012 Josh Berryman, University of Luxembourg,
# Pfaffenwaldring 27, 70569 Stuttgart, Germany; all rights
# reserved unless otherwise stated.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston,
# MA 02111-1307 USA

usage()
{
cat << EOF
usage: $0 -r [ref] -c [conf] -h [harness] -e [exe] <-p [log]>  <-l [log]> 
OPTIONS:
   -k               server window persists
   -w               run each process in a separate window
   -r   file.sqlite reference DB output file
   -c   file.conf   conf file, contains options for the freshs server
   -s   file.dat    start system file, contains a system microstate 
   -h   /dir        harness directory, contains wrapper scripts for client MD 
   -e   file.exe    harness executable: interpreter for the harness scripts 
  <-p   prof.txt>   request profiling to output file prof.txt
  <-l   log.txt>    request logging to output file log.txt
EOF
}

##this test assumes that Xwindows is installed & functioning.
NUM_CLI=8
profile=0
separate_window=0
keep_server=0
prof_txt=prof.txt
if [ "$#" -lt 4 ]
then
    usage
    exit
fi 

while getopts “kwr:c:s:h:e:p:l:” OPTION
do
     case $OPTION in
         r)
             ref_file=$OPTARG
             ;;
         c)
             conf_file=$OPTARG
             ;;
         s)
             start_config=$OPTARG
             ;;
         h)
             harness_dir=$OPTARG
             ;;
         e)
             harness_exe=$OPTARG
             ;;
         p)
             profile=1
             prof_txt=$OPTARG
             ;;
	 w) 
	     separate_window=1
	     ;;
	 k) 
	     keep_server=1
	     ;;
	 l) 
	     log=1
             log_txt=$OPTARG
	     ;;
         ?)
             usage
             exit
             ;;
     esac
done

cmd="python"
if [ "$profile" -eq "1" ]
then
    cmd="python -m cProfile -o profile.dat"
fi 


#############################################################


rm -Rf DB CONF LOG OUTPUT

##start a terminal window with the server in it.
if [ "$keep_server" -eq "0" ]
then 
    xterm -e "$cmd ../server/main_server.py $conf_file" &
else
    xterm -e "$cmd ../server/main_server.py $conf_file; bash" & ##server xterm window will persist
fi

echo ""
echo "SERVER command was:"
echo "$cmd ../server/main_server.py $conf_file"
echo ""


##give it a second to open its port before we start the clients.
sleep 2

##open most of the clients in new windows, like the server.
for i in `seq 0 $[NUM_CLI - 2]`
do
    if [ $separate_window -eq "1" ]
    then
    	xterm -T "FRESHS client" -e "python ../client/main_client.py -s $start_config -c client_espresso.cfg -x $harness_exe -H $harness_dir" &
    else
	python ../client/main_client.py  -s $start_config -c client_espresso.cfg  -x $harness_exe -H $harness_dir &
    fi
done

echo ""
echo "CLIENT command was:"
echo "python ../client/main_client.py -s $start_config -c client_espresso.cfg -x $harness_exe -H $harness_dir"
echo ""

#xterm -e "python ../client/main_client.py -c client_espresso.cfg"
python ../client/main_client.py  -s $start_config -c client_espresso.cfg  -x $harness_exe -H $harness_dir

##diff the results
outfile=$(ls --sort=time DB/*configpoints.sqlite | head -1)
echo ""
echo "Attempting comparison of outputs with reference"
echo ""
if [ "$log" -eq "1" ]
then 
    ./compare_DB.py $ref_file $outfile | tee $log_txt
else
    ./compare_DB.py $ref_file $outfile
fi

##collect profile data
if [ $profile -eq "1" ]
then
    python -c "import pstats; pstats.Stats('profile.dat').strip_dirs().sort_stats('cumulative').print_stats()"\
            > $prof_txt
    echo "Saved profiling results to $prof_txt"
fi
