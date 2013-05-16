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



##start execution.
arguments = sys.argv
if len(arguments) < 3:
    print "buildTree.py: require as arguments one SQLite database file, and the time interval tau\n"
    print "Prints out a tree diagram with IDs relative weights of configs within bins,"
    print ".. combine this view with the bin probability data (by default writted to the directory OUTPUT) for best results.\n"
    exit( str(arguments) )

db1_name = arguments[1]
tau      = int(arguments[2])

##open the target database
db1  = sqlite3.connect(db1_name)
cur1 = db1.cursor()

##get the tables in the database
cur1.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
tab = cur1.fetchall()
if tab != None:
   tab1=tab.pop(0)[0]
else:
   exit("Error, could not open table, db: "+str(db1_name))


##index the database by calcsteps for faster searching on this value
#print "#creating an index for database by field: calcsteps."
#cur1.execute('create index if not exists cs_index on '+tab1+' (calcsteps)')

##find the root point
cur1.execute('select * from '+tab1+' where calcsteps = 0')
lines = cur1.fetchall()
print "#Got "+str(len(lines))+" at time 0"
bin={}
posterior_weight={}
calcSteps={}
rc={}
bin['[\'escape\']']             = 0
posterior_weight['[\'escape\']']= 1.0
calcSteps['[\'escape\']']       = 0
rc['[\'escape\']']              = 0.0
time=0
while len(lines) > 0:
    nextT=0
    for line in lines:
        configId              = line[8]
        
        bin[configId]         = line[0]
        originId              = line[2]
        calcSteps[configId]   = line[3] 
        posterior_weight[configId] = line[11] 
        rc[configId]          = line[12]
        
        ##write the path segment
        print str(calcSteps[originId])+" "+str(rc[originId])+\
                        " "+str(bin[originId])+\
                        " "+str(posterior_weight[originId])+" "+str(originId)
        print str(calcSteps[configId])+" "+str(rc[configId])+\
                        " "+str(bin[configId])+\
                        " "+str(posterior_weight[configId])+" "+str(configId)
        print ""
        
    if tab:
        tab1 = tab.pop(0)[0]
    else:
        tab1 = None
    if tab1:
           ##find the next points
            cur1.execute('select * from '+tab1+\
             ' where calcsteps > ? and calcsteps <= ?',[time,time+tau])
            lines = cur1.fetchall()
            time = time + tau
    else:
            lines=None
    

