# -*- coding: utf-8 -*-
# Copyright (c) 2012 Josh Berryman, University of Luxembourg,
# Allmandring 3, 70569 Stuttgart, Germany; all rights
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


# Formatting
import modules.concolors as cc

class spres_helper():
    
    def __init__(self, server, control ):
        self.server        = server
        self.control       = control
        return(None)

    def read_restart( self, timeStamp,  nBins ):
        
        ss=self.server
        epoch    = self.read_transMat( nBins )
        epoch_sv = self.read_stateVec()

	if epoch_sv != epoch:
	     ss.logger_freshs.error(cc.c_red +\
		 'Restart Error! Transmat and statevec files have different timepoints, transmat:'+ str(epoch)\
		+ ' and statevec: '+str(epoch_sv)  +cc.reset)
	     exit('Restart error: transmat and statevec files have different timepoints.')


        return epoch


    ##read the *second-last* transmat from a file
    def read_transMat( self, nBins ):
         
        ss = self.server
        sc = self.control ##spaghetti-trail of backpointers

        mf = open( self.server.matfile, "r")
        ss.logger_freshs.info(cc.c_magenta +\
         'reading transmat... this function not yet optimised for speed'\
                                  +cc.reset)

        endBlock = False
        epoch    = 0

        transMat = [ {} for x in xrange( nBins ) ]

        line = mf.readline()
        while( line ):
            fields = line.split()
            if len(fields) >= 3 :

                ##check if we need to overwrite with a new block
                if endBlock == True:

                   transMat = [ {} for x in xrange(nBins) ]
                   endBlock = False
                   epoch    = epoch + self.server.tau

                ##save the bin-pair transition weight
                i      = int(fields[0])
                j      = int(fields[1])
                t      = float(fields[2])

                transMat[j][i] = t
            else:
                ##empty line: set a flag
                endBlock = True

            ##try to get another line
            line = mf.readline()

        ##copy current transmat to the output
        sc.transMat1 = [ {} for x in xrange( nBins ) ]
        for i in range( nBins ):
            for j in transMat[i].keys():
                sc.transMat1[i][j] = transMat[i][j]


        mf.close()
        epoch    = epoch + self.server.tau
        ss.logger_freshs.info(cc.c_magenta +\
                                  'read transmat, epoch: '+str(epoch)\
                                  +cc.reset)

        return epoch



    def write_matrix_sparse( self, fname, transMat, nBins ):
        
        h_f = open(fname,'a')
        
        ##there has to be a better way to write this
        for binFrom in range( 0, nBins ):
            for binTo in range( 0, nBins ):
                if binFrom in transMat[binTo].keys():
                    h_f.write(str(binFrom) + " " +\
                      str(binTo) + " " +\
                      str(transMat[binTo][binFrom])+'\n')
                    


        h_f.write('\n')
        h_f.close()
        
    def write_sampfreq( self, fname, nBins ):
        
        h_f = open(fname,'a')
        for bin in range( 0, nBins ):
            h_f.write(str(bin) + " " +\
                      str(self.server.lambdas[bin])  +  " " +\
                      str(self.server.M_0_runs[bin]) + '\n')
                
        h_f.write('\n\n')
        h_f.close()

    def read_stateVec( self ):

        ##open for read
        ss        = self.server
        sc        = self.control
        vf        = open(self.server.vecfile, "r")
        sv        = [0.0]*sc.nBins
        sv_old    = [0.0]*sc.nBins
        samp      = [0]*sc.nBins
        samp_old  = [0]*sc.nBins
        sv[0]     = 1.0
        sv_old[0] = 1.0

	epoch     = 0
        haveBlank = False

        ##return the most recent state vector
        line = vf.readline()
        while( line ):
            fields = line.split()
            if len(fields) >= 4 :
                i = int(fields[0])
                w = float(fields[2])
                s = int(fields[3])
                
                sv_old[i]   = sv[i]
                sv[i]       = w
                samp_old[i] = samp[i]
                samp[i]     = s
		
		if haveBlank:
		    epoch     = epoch + self.server.tau
		    haveBlank = False

	    else:
	        ##two blank lines between each block
		haveBlank = True

            line = vf.readline()

        ##copy the sv that has been read to the output buffer
        ss.M_0_prev = [0] * len(sv)
        ss.M_0_runs = [0] * len(sv)
        for i in range(len(sv)):
              sc.stateVector[i]     = sv[i]
              sc.stateVector_old[i] = sv_old[i]
              ss.M_0_runs[i]        = samp[i]
              ss.M_0_prev[i]        = samp_old[i]
        
        ##close the file 
        vf.close()
 
        epoch    = epoch + self.server.tau
	ss.logger_freshs.info(cc.c_magenta +\
	           'read statevec, epoch: '+str(epoch)\
	                          +cc.reset)

        return epoch


    def write_statevec( self, fname, stateVec, nBins ):
        
        h_f = open(fname,'a')
        for bin in range( 0, nBins ):
            h_f.write(str(bin)                       + " " +\
                      str(self.server.lambdas[bin])  + " " +\
                      str(stateVec[bin])             + " " +\
                      str(self.server.M_0_runs[bin]) +'\n')
                
        h_f.write('\n\n')
        h_f.close()

    def write_rate( self, fname, time, lambda_B, rate ):
        
        self.server.logger_freshs.info(concolors.c_red +"Rate into B: " +\
                                        str(rate) + concolors.reset) 

        if rate != 0.0:
            h_f = open(fname,'a')
            h_f.write(str(time)+" "+str(lambda_B)+" "+str(rate)+'\n')
            h_f.close()
