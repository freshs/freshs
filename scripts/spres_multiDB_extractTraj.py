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
if len(arguments) < 2:
    print "extractTraj.py: require as arguments:"+\
          "the index of a minimum bin for trajectory endpoints.\n"+\
          "and a time-ordered list of DB files (newest first)\n"
    exit( str(arguments) )

max_l     = float(arguments[1])
db1_name  = arguments[2]


##open the target database
db1     = sqlite3.connect(db1_name)
cur1    = db1.cursor()

##select the first table in the database
cur1.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
tab = cur1.fetchone()
if tab != None:
   tab1=tab[0]
else:
   exit("Error, could not open tab in DB: "+str(db1_name))


##get the size
cur1.execute('select count(*) from '+tab1)
n1 = cur1.fetchone()[0]
print "database has: "+str(n1)+" rows"

##find the oldest configs
cur1.execute('select max(calcsteps) from '+tab1)
maxTime =  float(cur1.fetchone()[0])
print "database has oldest entries at: "+str(maxTime)



##select all nucleated points
cur1.execute('select * from '+tab1+' where lambda = ?', [max_l])
lines = cur1.fetchall()
print "Got "+str(len(lines))+" nucleated configs at time "+str(maxTime)
age              = maxTime

posterior_weight=['0']*len(lines)
originPoint=['0']*len(lines)
fileName=['0']*len(lines)

##loop over them
trajCount=0
for line in lines:
    ##posterior weight is the weight of the traj relative to other trajs 
    ##which reached the bin 

    print "Id: "+line[2]
    print "weight: "+str(float(line[11]))

    originPoint[trajCount]= line[2]
    age                   = line[3]
    posterior_weight[trajCount] = str(float(line[11])) 
    fileName[trajCount]   =file_stem+"_"+\
        str(trajCount)+"_w"+\
        str(posterior_weight[trajCount])

    print "\n"
    print "Writing traj id: "+fileName[trajCount]
    print "in separate files for each frame"

    
    ##write the child config
    frameFileName   =  fileName[trajCount]+ "_" +\
                str(age).zfill(8) + file_suff
    trajFile   = open(frameFileName, 'w')

    ##writing one line at a time
    asArray=str(line[1]).split("]")
    for p in asArray:
            space_sepped=str(p).translate(None, '[],\'')
            trajFile.write(space_sepped+"\n")
    trajFile.close()
    print "Wrote file: "+frameFileName
    trajCount = trajCount + 1

numTraj   = trajCount

##loop backwards over the DBS
for argc in range(3,len(arguments)-1):
    db1_name = arguments[argc]
    print "#reading db: "
    print "#"+str(db1_name)


    ##open the target database
    db1     = sqlite3.connect(db1_name)
    cur1    = db1.cursor()

    ##select the first table in the database
    cur1.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
    tab = cur1.fetchone()
    if tab != None:
        tab1=tab[0]
    else:
        exit("Error, could not open tab in DB: "+str(db1_name))

    ##for each db, we are going to loop over each traj
    for trajCount in range(numTraj):  

        ##select the parent of the later config
        cur1.execute('select * from '+tab1+' where myid = ?',\
                                         [originPoint[trajCount]])
        line = cur1.fetchone()

        ##make this config the new parent config
        originPoint[trajCount]=line[2]
        newAge                =line[3]

        ##write the child config
        frameFileName   =  fileName[trajCount]+ "_" +\
                str(age).zfill(8) + file_suff
        trajFile   = open(frameFileName, 'w')

        ##writing one line at a time
        asArray=str(line[1]).split("]")
        for p in asArray:
            space_sepped=str(p).translate(None, '[],\'')
            trajFile.write(space_sepped+"\n")
        trajFile.close()
        print "Wrote file: "+frameFileName

    age = newAge


    




