#!/usr/bin/python
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

## database
import sqlite3

##parse args
import sys

####################################################
file_stem="traj" ##default output file stem
file_suff=".dat" ##default output file suffix
####################################################


##start execution.
arguments = sys.argv
if len(arguments) < 4:
    print("extractTraj.py: require as arguments one SQLite database file,\n"+\
          "the index of a bin after which nucleation has occured.\n"+\
          "and the the time interval tau.")
    exit( str(arguments) )

db1_name = arguments[1]
max_l    = int(arguments[2])
tau      = float(arguments[3])

##open the target database
db1  = sqlite3.connect(db1_name)
cur1 = db1.cursor()

##select the first table in the database
cur1.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
tab = cur1.fetchone()
if tab != None:
   tab1=tab[0]
else:
   exit("Error, could not open")


##get the size
cur1.execute('select count(*) from '+tab1)
n1 = cur1.fetchone()[0]
print("database has: "+str(n1)+" rows")

##index the database by calcsteps for faster searching on this value
print("creating an index for database by field: calcsteps.")
cur1.execute('create index if not exists cs_index on '+tab1+' (calcsteps)')

##find the oldest configs
cur1.execute('select max(calcsteps) from '+tab1)
maxTime =  float(cur1.fetchone()[0])
print("database has oldest entries at: "+str(maxTime))

##loop over nucleated points
cur1.execute('select * from '+tab1+' where calcsteps = ? and lambda = ?', [float(maxTime), max_l])


lines = cur1.fetchall()
print("Got "+str(len(lines))+" nucleated configs at time "+str(maxTime))
traj_count=0
for line in lines:
    configPoint=line[1]
    originPoint=line[2]

    age              = maxTime

    ##posterior weight is the weight of the traj relative to other trajs 
    ##which reached the bin 
    posterior_weight = line[11] 

    print("\n")
    print("Writing traj id: "+file_stem+"_"+\
                        str(traj_count)+"_"+\
                  str(posterior_weight))
    print("in separate files for each frame")

    while configPoint :        

        ##write the config
        fileName   = file_stem       + "_"       +\
                     str(traj_count) + "_"       +\
                     str(posterior_weight) + "_" +\
                     str(age)        + file_suff
        trajFile   = open(fileName, 'w')

        ##writing one line at a time
        asArray=str(configPoint).split("]")
        for p in asArray:
            space_sepped=str(p).translate(None, '[],\'')
            trajFile.write(space_sepped+"\n")
        trajFile.close()

        print("Wrote file: "+fileName)


        ##find the parent point
        cur1.execute('select * from '+tab1+' where  calcsteps = ? and myid = ?', [age-tau,originPoint])
        parent = cur1.fetchone()
        if parent != None:
            configPoint=parent[1]
            originPoint=parent[2]
            age        =float(parent[3])
        else:
            configPoint = None
    traj_count += 1

    

