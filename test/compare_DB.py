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

########################  Helper function.
def status_exit( status, f1, f2 ):
    if status != 0:
        print("FAIL, files '"+str(f1)+"' and '"+str(f2)+"' differ.")
    else:
        print("SUCCESS, files '"+str(f1)+"' and '"+str(f2)+"' match.")
    
    quit()
####################################################

status=0

##start execution.
arguments = sys.argv
if len(arguments) < 3:
    print("compare_DB.py: require as arguments two SQLite database files.")
    status_exit( 1, arguments[1], "")

db1_name = arguments[1]
db2_name = arguments[2]

##open the two target databases
db1  = sqlite3.connect(db1_name)
db2  = sqlite3.connect(db2_name)
    
cur1 = db1.cursor()
cur2 = db2.cursor()

##select the first table in each database
cur1.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
tab = cur1.fetchone()
if tab != None:
   tab1=tab[0]
else:
   status_exit( 1, db1_name, db2_name )

cur2.execute('SELECT name FROM sqlite_master WHERE type IN (\'table\')')
tab = cur2.fetchone()
if tab != None:
   tab2=tab[0]
else:
   status_exit( 1, db1_name, db2_name )


##get the sizes of each one
cur1.execute('select count(*) from '+tab1)
n1 = cur1.fetchone()[0]
cur2.execute('select count(*) from '+tab2)
n2 = cur2.fetchone()[0]


##check that sizes match
if n1 != n2 :
    print(db1_name+" has: "+str(n1)+" rows")
    print(db2_name+" has: "+str(n2)+" rows")
    status_exit( 1, db1_name, db2_name )

##loop over rows
for i in range(n1) :
    cur1.execute('select * from '+tab1+' order by rowid limit 1 offset ?', [i])
    line1 = cur1.fetchone()




###########Here is the format of the table "config points"
#(lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, myid text, seed int, lambda_old int, weight real)

    ##count the number of lines in tab2 which match the line from tab1
    cur2.execute(\
        'select count(*) from '+tab2+' where lambda = ? and configpoint = ?  and seed = ? and lambda_old = ? and weight = ?',\
            [line1[0], line1[1], line1[9], line1[10], line1[11]] )
    result = cur2.fetchone()[0]
    if  result != 1:
        lineid  = line1[8]
        seed    = line1[9]
        print("FAIL: line with seed: "+str(seed)+" was matched "+str(result)+" times.")
        status += 1

        ##look for closest match:
        cur2.execute('select * from '+tab2+' where seed = ?',[seed])
        line2 = cur2.fetchone()
        if line2 :
            if len(line2) == len(line1) :
                print("In closest match, differing entries were:")
                for i in range(len(line1)): 
                    if str(line1[i]) != str(line2[i]):
                        s1 = str(line1[i])
                        s2 = str(line2[i])
                        print("'"+s1[0:min(50,len(s1))]+"' .vs. '"+s2[0:min(50,len(s2))]+"'")
            else :
                print("Lines lengths differ.  Target line was:")
                for i in range(len(line1)): 
                    s1 = str(line1[i])
                    print(s1[0:min(50,len(s1))]+" ... ")
        

##finished. Report number of mismatches and quit.            
status_exit( status, db1_name, db2_name )

       

     



