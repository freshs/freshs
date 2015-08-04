#!/usr/bin/env python 

# Assign statistical weights to trajectories

import numpy as np
import scipy.linalg as lin
import scipy.signal as signal
import bz2
import sys
import os
import glob
from   numpy import floor


###DB handling code to read trajectory weights
freshs_path="/home/users/jberryman/freshs"
sys.path.append(freshs_path+"/server")
sys.path.append(freshs_path+"/server/modules/ffs")
sys.setrecursionlimit(999999)
import configpoints

###Read id of run
if len(sys.argv) < 3:
    print("require db file and rates file.")
    exit(1)

dbFile=sys.argv[1]
rateFile=sys.argv[2]


###print(getWeight(run))

def getP( dbFile ):

    ###DB handler
    try:
        cfph   =  configpoints.configpoints('none',dbFile)
    except:
        print("NoDBFile:"+dbFile)
        exit(1)

    ###Get a list of nucleating pathways by endpoint.
    cfpcand = cfph.return_points_on_last_interface()
    tracecount = 0
    maxtr  = len(cfpcand)
    w_list = []

    ##backtrace each suvvessful trace to find its Rosenbluth weight
    for cfp in cfpcand:
	weight   = 1.0
	op = cfph.return_origin_point_by_id(cfp[2])
	while True:
	   cfph.cur.execute('select usecount from configpoints where myid = ?', [op[8]])
           result       = cfph.cur.fetchone()
	   if result:
	      siblings = int(result[0])
	   else:
	      print("Error backtracing for rates")
	      exit(1)
           weight = weight / float(siblings) 
	   if 'escape' in op[2]:
		break
	   op = cfph.return_origin_point_by_id(op[2])
        w_list.append(weight)
	print("cfp: "+cfp[8]+" has weight: "+str(weight))

    p_B_given_A = np.sum(np.asarray(w_list))

    return p_B_given_A

def get_kA(rateFile):
    rateTable = np.loadtxt(rateFile)
    kA = rateTable[0,4]
    return(kA)


p_B_given_A = getP(dbFile)
print("P(B|A)= %.12e" % p_B_given_A)

kA          = get_kA(rateFile)
print("kA=     %.12e" % kA)

print("rate=   %.12e" % (kA*p_B_given_A))


