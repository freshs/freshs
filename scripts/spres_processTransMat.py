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

###make sure that integer division op "//" is present
from __future__ import division
import sys
from collections import defaultdict

##matrix diagonalisation
import numpy as np

##parse args
from   optparse import OptionParser

##diagonalise the tm, write it out and the eigenvectors too.
def printTmsEvs( evFiles, evFileNameStem, tm_outFile, meanTm, L ):

    ####experiment: what if the matrix is explicitly cyclic?
    #for i in range(L):
    #    meanTm[L-1][i]=0.0
    #meanTm[L-1][0]=1.0
    
    evals, evecs = np.linalg.eig( np.transpose(meanTm) )
    #evals, evecs = np.linalg.eig( meanTm )

    ###sort by eigenvalue
    ssorted=sorted(zip(evals,np.transpose(evecs)),key=lambda x: abs(x[0]), reverse=True)
    #ssorted=sorted(zip(evals,evecs),key=lambda x: abs(x[0]), reverse=True)
  
    for j in range(L):
    ##i^th eigenvector is in "column" i.

        EVAL=ssorted[j][0]
        print(EVAL)
        if abs(EVAL) > 0.99:

            EVEC=ssorted[j][1]
            if EVEC[0,0] >= 0.0:
                sign=1.0
            else:
                sign=-1.0
            EVEC = EVEC * sign

            print(EVEC)

           ##open evec output file
            while len(evFiles) < j+1:
                evFiles.append(open(evFileNameStem+"."+str(len(evFiles))+".dat", 'w'))
            if not evFiles[j]:
                exit( "Error, could not open file: "+evFileNameStem+"."+str(j))


            evFiles[j].write("#ev_number: "+str(j)+" eval: "+str(EVAL)+"\n")
            for i in range(L):
                evFiles[j].write(str(i)+" "+str(EVEC[0,i].real)+\
                                        " "+str(EVEC[0,i].imag)+\
                                        " "+str(t)+"\n")          
            evFiles[j].write("\n\n")

    for i in range(L):
        for j in range(L): 
            tm_outFile.write(str(i)+" "+str(j)+\
                                    " "+str(meanTm[i,j])+"\n")
        tm_outFile.write("\n")
    tm_outFile.write("\n")


####START EXECUTION HERE:

##parse arguments
parser = OptionParser()
parser.add_option("-t", "--tblock", dest="tBlockAverage", help="number of matrices blocks to average over in time", metavar="t_block_average", type="int", default=2000)
parser.add_option("-b", "--bblock", dest="bBlockAverage", help="number of matrix bins to block-average over", metavar="b_block_average", type="int", default=1)

(options, args) = parser.parse_args()
tBlockAverage=options.tBlockAverage
bBlockAverage=options.bBlockAverage


##Args will hold positional arguments... 
##if there is any argument without a flag,
## assume that it is a transition matrix file:
if len(args) > 0:
    tmNames=args
else:
    print("processTransmat.py: takes the mean and diagonalises a transition matrix")
    print("require minimum 1 arguments,  SPRES output files with transition matrix time series.")
    print("Optional argument: --tblock tBlockAverage, blocksize for time-average. default="+str(tBlockAverage))
    print("Optional argument: --bblock bBlockAverage, for bin-average. default="+str(bBlockAverage))
    exit(8)

##open all input files
matCount=0
L=1
##create a 3D array
allMats = np.zeros(shape=(1,1,1))  
for tmName in tmNames:

   ##Open the matrix file
    tmFile   = open(tmName, 'r')
    if not tmFile:
        exit( "Error, could not open file: "+tmName)
    else:
        print("Reading file: "+str(tmName))

    ##load the matrix files 
    tCount  = 0
    t_index = 0
    for line in tmFile:
        line   = line.rstrip()
        asList = line.split()
        if len(asList) == 3 :

            if bBlockAverage != 0:
                x_index = int(asList[0]) // bBlockAverage
                y_index = int(asList[1]) // bBlockAverage
            else:
                x_index = int(asList[0])
                y_index = int(asList[1])
            
            if x_index + 1 > L:
                allMats = np.resize(allMats,(t_index+1,x_index+1,x_index+1))
                for t in range(t_index+1):
                    for i in range(L,x_index+1):
                        for j in range(x_index+1):
                            allMats[t][i][j] = 0.0
                    for j in range(L,x_index+1):
                        for i in range(x_index+1):
                            allMats[t][i][j] = 0.0
                L = x_index + 1
                
            if y_index + 1 > L:
                allMats = np.resize(allMats,(t_index+1,y_index+1,y_index+1))
                for t in range(t_index+1):
                    for i in range(L,y_index+1):
                        for j in range(y_index+1):
                            allMats[t][i][j] = 0.0
                    for j in range(L,y_index+1):
                        for i in range(y_index+1):
                            allMats[t][i][j] = 0.0
                L = y_index + 1

            ##save the value
            allMats[t_index][x_index][y_index] += float(asList[2])

        else:
            tCount  = tCount + 1
            if tBlockAverage != 0:
                t_next = tCount // tBlockAverage
            else:
                t_next = tCount
            
            if t_next != t_index:
                t_index = t_next
                allMats = np.resize(allMats,(t_index+1,L,L))
                for i in range(L):
                    for j in range(L):
                        allMats[t_index][i][j] = 0.0

            if tCount % 100 == 0:
                print("   Read "+str(tCount)+" matrices, size: "+str(L)+" by "+str(L) )
            
     


##open output file
tm_outFile = open("meanTransMat.dat","w")
if not tm_outFile:
    exit( "Error, could not open file: meanTransMat.dat")

##init list of evecs files.
evFiles=[]

for t in range(t_index+1):

       ##create an actual matrix, rather than an array.
       meanTm    = np.matrix(np.zeros(shape=(L,L)))

       ##init matrix
       for i in range(L):
           rowSum = 0.0
           for j in range(L):
               rowSum = rowSum + allMats[t][i][j]
           if rowSum != 0.0:
               invWeight = 1.0/rowSum
           else:
               invWeight = 1.0
           for j in range(L):
               meanTm[i,j] = allMats[t][i][j] * invWeight

       print("Diagonalising at t = "+str(t * tBlockAverage))
       printTmsEvs( evFiles, "evecs", tm_outFile, meanTm, L )
    
tm_outFile.close()

