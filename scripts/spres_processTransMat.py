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

##parse args
import sys

##matrix diagonalisation
import numpy as np

##default
blockAverage=2000

    


##diagonalise the tm, write it out and the eigenvectors too.
def printTmsEvs( evFile, tm_outFile, meanTm, L ):

    ####experiment: what if the matrix is explicitly cyclic?
    for i in range(L):
        meanTm[L-1][i]=0.0
    meanTm[L-1][0]=1.0
    


    evals, evecs = np.linalg.eig( np.transpose(meanTm) )
    #evals, evecs = np.linalg.eig( (meanTm) )

    ##i^th eigenvector is in "column" i.
    for i in range(L):
        evFile.write(str(i)+" "+str(np.abs(evecs[i][0]))+\
                         " "+str(t)+"\n")          
    evFile.write("\n\n")

    for i in range(L):
        for j in range(L): 
            tm_outFile.write(str(i)+" "+str(j)+\
                                    " "+str(meanTm[i][j])+"\n")
        tm_outFile.write("\n")
    tm_outFile.write("\n")


##start execution.
arguments = sys.argv
if len(arguments) < 2:
    print "processTransmat.py: parses, takes running mean and diagonalises a transition matrix"
    print "require 1 argument, a SPRES output file with a transition matrix time series."
    print "Optional second argument, blocksize for time-average. default="+str(blockAverage)
    exit( str(arguments) )

tmName   = str(arguments[1])
if len(arguments) >= 3:
    blockAverage=int(arguments[2])

##Open the matrix file
tmFile   = open(tmName, 'r')
if not tmFile:
    exit( "Error, could not open file: "+tmName)

tm_outFile = open("meanTransMat.dat","w")
if not tm_outFile:
    exit( "Error, could not open file: meanTransMat.dat")

##Open an output file
evFile   = open('evecs.dat', 'w')
if not evFile:
    exit( "Error, could not open file: evecs.dat")


##we do not initially know the array size
L=1

##init matrix
##set up 2D arrays (resize later)
meanTm    = np.matrix([[0.0]])
rowVisits = [0.0]

##loop over lines to build the matrix
haveData = 0
t        = 0
for line in tmFile:
     line = line.rstrip()

     ##check if we have a complete matrix
     if not line:
         if haveData == 1:
             t = t + 1
             haveData = 0


             ##diagonalise the running average and do output
             if blockAverage == 0 or t % blockAverage == blockAverage - 1:
                 print "diagonalising block mean transmat at t="+str(t)
                 
                 for i in range(L):

                     invWeight = 1.0/rowVisits[i]
                     #print str(i)+" "+str(rowVisits[i])+\
                     #   " "+str(meanTm[i][i])+" "+str(meanTm[i][j] * invWeight)

                     rowSum = 0.0
                     for j in range(L):
                         meanTm[i][j] = meanTm[i][j] * invWeight
                         rowSum = rowSum + meanTm[i][j]
                     #print "   Row sum was:"+str(rowSum)


                 printTmsEvs( evFile, tm_outFile, meanTm, L )
    
                 for i in range(L):
                     rowVisits[i] = 0.0
                     for j in range(L): 
                         meanTm[i][j] = 0.0
         continue
     else:
         haveData = 1
           

     ##parse the line
     asList = line.split()
     x      = int(asList[0])
     y      = int(asList[1])
     entry  = float(asList[2])

     ##extend the matrices if we have a new high-point
     if x > L - 1 or y > L - 1:
         lNew    =  1 + max( x, y )
         meanTm2 =  np.zeros(shape=(lNew,lNew))
         
         for i in range(lNew):
             for j in range(lNew):
                 meanTm2[i][j] = 0.0
         for i in range(L):
             for j in range(L):
                 meanTm2[i][j] = meanTm[i][j]
         for i in range(lNew - L):
             rowVisits.append(0.0)
         L      = lNew
         meanTm = meanTm2

     meanTm[x][y] += entry
     rowVisits[x] += entry


##if we didn't just do a write, then do one
if blockAverage != 0 and t % blockAverage != blockAverage - 1:
    print "diagonalising block mean transmat at t="+str(t)
    for i in range(L):
        invWeight = 1.0/rowVisits[i]
        for j in range(L):
            meanTm[i][j] = meanTm[i][j] * invWeight
    printTmsEvs( evFile, tm_outFile, meanTm, L )

evFile.close()
tm_outFile.close()

