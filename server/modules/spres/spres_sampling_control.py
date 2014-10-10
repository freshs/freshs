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

# Date and Time
import datetime as dt
import time

# System
import os
import math

##sorting & selecting config points
import operator
import random

# Formatting
import modules.concolors as cc
import modules.server    as server
import spres_helper

# -------------------------------------------------------------------------------------------------

#### SPRES-SPECIFIC SERVER CLASS ####
class spres_sampling_control():
    
    ##init, saving a backpointer to the parent "server" class which handles comms.
    def __init__( self, myServer ):
        
        ##save the backpointer
        self.server     = myServer
        ss              = self.server
        
        ##setup some useful variables
        self.nBins             = ss.nohs+2
        self.parentShots       = []
        self.min_weight        = 1e-250 ##round weights below this value to zero

        ##build some data structures.
        self.stateVector        = self.nBins * [0.0]
        self.stateVector_old    = self.nBins * [0.0]
        self.stateVector[0]     = 1.0;
        self.stateVector_old[0] = 1.0;

        ##set up 2D lists-of-dicts ("near-diagonal arrays") for the transition matrices
        self.transMat1= [ {} for x in xrange(self.nBins) ]
        self.transMat2= [ {} for x in xrange(self.nBins) ]

        ##To save re-checking if a bin is full more than once per epoch
        self.flag_bin_complete = [False] * self.nBins
        
        ##to save searching the DB over all timepoints...
        ##an array of dicts of lists of (point, seed) tuples.
        self.epoch_points_buf   = [{} for x in xrange(self.nBins)]
        self.epoch_points_old   = [{} for x in xrange(self.nBins)]

        ##init an i-o helper class
        self.helper     = spres_helper.spres_helper(ss, self)

        if ss.dbload == False:
            ##convention is transMat[toBin][fromBin]
            self.transMat1[0][0] = 1.0;
            self.epoch_points_old[0][0]=[('0',0)]
            ss.epoch            = 0  ##current number of timesteps
            self.start_epoch    = 0
        else:
            ##get the transmats and state vectors from files
            ss.epoch            = self.helper.read_restart(ss.timestamp,\
                                                         self.nBins)
            self.start_epoch    = ss.epoch
            
            ss.logger_freshs.debug(cc.c_magenta +\
                'Recovered sampling frequencies: '+str(ss.M_0_runs)\
                                      + cc.reset)

        #make sure we have folders for output
        if ss.clients_use_fs == True:
            if not os.path.exists(ss.folder_conf+str(ss.epoch)):
                os.makedirs(ss.folder_conf+str(ss.epoch))
            if not os.path.exists(ss.folder_conf+str(ss.epoch+ss.tau)):
                os.makedirs(ss.folder_conf+str(ss.epoch+ss.tau))
         

        ##setup an array for count of launched runs from each bin
        ss.run_count = [0] * self.nBins
        
                  
# -------------------------------------------------------------------------------------------------
    def load_points( self, epoch ):
        
        ss = self.server

        ##load the list of points made in the previous (completed?) epoch
        self.epoch_points_old   = [{} for x in xrange(self.nBins)]        
        ep_count = ss.storepoints.return_epoch_points( self.epoch_points_old )
        
        ss.logger_freshs.info(cc.c_blue +\
                                      "read restart points: "+str(ep_count)\
                                      + cc.reset)

        ##the DB is now ready for the first (after the zeroth) epoch
        if self.test_db_complete():

           ##start a new epoch
           for bin in range( 0, self.nBins ):
               self.flag_bin_complete[bin] = False
           self.reset_bin_index()
           if ss.storepoints.use_multDB:
               ss.storepoints.increment_active_db(ss.epoch + ss.tau)
           else:
               ss.storepoints.increment_active_table( ss.epoch+ss.tau )
                    
           ss.logger_freshs.info(cc.c_red +\
                          'Deciding that we loaded\
                           a complete timestep, and advancing epoch'+ cc.reset)
        else:
           ss.logger_freshs.warn(cc.c_red +\
                          'Error! DB loaded was corrupted or incomplete'+ cc.reset)
           ss.logger_freshs.warn(cc.c_red +\
                          'Error! Advise restart from earlier time point'+ cc.reset)
           exit()
             
# -------------------------------------------------------------------------------------------------
    def test_db_complete( self ):
        ss = self.server

        allShots = True

        for bin in range( 0, self.nBins ):
            shots_required = ss.M_0_prev[bin]
            shots_made     = ss.storepoints.return_nop_lold( bin )
        
            if shots_made < shots_required and self.stateVector_old[bin] > self.min_weight:
               allShots  = False
               bin_short = bin
               self.flag_bin_complete[bin] = False
               ss.act_lambda               = bin

               ss.logger_freshs.info(cc.c_blue)
               ss.logger_freshs.info("reading DB, bin "+str(bin)+\
                  " had: "+str(shots_made)+\
                  " shots complete, out of: "+str(shots_required)+\
                  " with statevector weight: "+str(self.stateVector_old[bin]))
               ss.logger_freshs.info(cc.reset)

               ##No break on fail of this integrity check....
	       ##...might as well keep going to produce more info.
               #break
            else:
               self.flag_bin_complete[bin] = True
                


        return allShots

                  
# -------------------------------------------------------------------------------------------------
    def launch_jobs( self ):
        ss = self.server
        
        self.reset_bin_index()

        # desired number of successful runs per interface 0 to n-1...
        ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderA'))
        for act_entry in range( 1, self.nBins - 1 ):
            ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'lambda' + str(act_entry)))
        if ss.absorb_at_B == 0 :
            ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderB'))
        else:
            ss.M_0_runs.append(0)
            
        for row in range ( 0, self.nBins ):
            
            ##save the number of total jobs from each row
            ss.run_count.append(0)
            
            ##save the number of outstanding jobs from each row
            ss.M_0.append(0)
            ss.logger_freshs.info(cc.c_magenta + 'Current lambda is: ' + str(row) + \
                                                    ' : ' + str(ss.M_0[row]) + cc.reset)
             
# -------------------------------------------------------------------------------------------------
    def test_epoch_complete( self ):
        ss = self.server
        
        if ss.absorb_at_B > 0 :

            for bin in range (0, self.nBins - 1):


	        ##skip bins with weight below min_weight
		if self.stateVector[bin] < self.min_weight:
		       self.flag_bin_complete[bin] = True
		       if self.stateVector[bin] > 0.0:
		          ss.logger_freshs.info(cc.c_magenta + 'Skipping bin '+str(bin)+' with weight below ' +\
		                     str(self.min_weight) + cc.reset)


		elif self.flag_bin_complete[bin] == False:
                    population = ss.storepoints.count_points_in_if_at_t(bin, ss.epoch)

                    if population > 0:
                        complete = ss.storepoints.count_points_from_if_between_t(bin, ss.epoch, ss.epoch + ss.tau)
                        ss.logger_freshs.debug(cc.c_magenta +"saved shots from bin " + str(bin) +\
                                     " are: " + str(complete) +\
                                     " of: " + str(ss.M_0_runs[bin]) + cc.reset)

                        if  complete < ss.M_0_runs[bin]:
                            ss.logger_freshs.debug(cc.c_magenta + 'bin ' + str(bin) + \
                                                                ' has outstanding configs' + \
                                                                  cc.reset)
                            return( False )
                        else:
                            ss.logger_freshs.debug(cc.c_magenta + 'logging bin ' + str(bin) + \
                                                                ' as complete for this epoch' + \
                                                                  cc.reset)
                            self.flag_bin_complete[bin] = True

                ss.logger_freshs.debug(cc.c_magenta +"epoch up for bin: " + str(bin) + cc.reset)         
        else:

            for bin in range (0, self.nBins ):

	        ##skip bins with weight below min_weight
                if self.stateVector[bin] < self.min_weight:
		    self.flag_bin_complete[bin] = True
		    if self.stateVector[bin] > 0.0:
		           ss.logger_freshs.info(cc.c_magenta + 'Skipping bin '+str(bin)+' with weight below ' +\
		                        str(self.min_weight) + cc.reset)


		elif self.flag_bin_complete[bin] == False:

                    population = ss.storepoints.count_points_in_if_at_t(bin, ss.epoch)

                    if population > 0:
		        complete =  ss.storepoints.count_points_from_if_at_t(bin, ss.epoch + ss.tau)

                        if complete < ss.M_0_runs[bin] :
                           
			    ss.logger_freshs.debug(cc.c_magenta + 'sv:    ' + str(self.stateVector[bin]) + \
							         cc.reset)
                            ss.logger_freshs.debug(cc.c_magenta + 'sv_old:' + str(self.stateVector_old[bin]) + \
				                                                                 cc.reset)




                            ss.logger_freshs.debug(cc.c_magenta + 'bin ' + str(bin) + \
                                                                ' has outstanding configs: ' +\
                                                                cc.reset)
                            ss.logger_freshs.debug(cc.c_magenta + 'counted ' + str(complete) +\
                                                                ' shots complete, with age of ' +\
                                                                  str(ss.epoch + ss.tau) +\
                                                                  cc.reset)
                            ss.logger_freshs.debug(cc.c_magenta + 'from a total of ' + str(ss.run_count[bin]) +\
                                                                ' shots made' +  cc.reset)
                            ss.logger_freshs.debug(cc.c_magenta + 'Target number to make was: '+\
                                                                  str(ss.M_0_runs[bin]) +\
                                                                  cc.reset)
                            ss.logger_freshs.debug(cc.c_magenta + 'Population of start configs in bin :'+str(bin)+\
                                                                ' at time: '+str(ss.epoch)+' was: '+str(population) +\
                                                                  cc.reset)
                            return( False )
                        else:
                            self.flag_bin_complete[bin] = True
        return( True )  
          
# -------------------------------------------------------------------------------------------------
    def advance_epoch( self ):
        ss = self.server
        
        self.reset_bin_index()

        
        ss.epoch     += ss.tau    ##advance the time
        
        ##make sure we have a folder to store state, working 1 taustep ahead.
        if ss.clients_use_fs == True:
            if not os.path.exists(ss.folder_conf+str(ss.epoch+ss.tau)):
                os.makedirs(ss.folder_conf+str(ss.epoch+ss.tau))
            

        nTotal   = [0] * self.nBins
        nForward = [0] * self.nBins

        ##update the transmats
        for bin_to in range( 0, self.nBins ):
            ss.run_count[bin_to] = 0
            self.transMat1[bin_to] = {}
            for bin_from in self.transMat2[bin_to].keys():

                self.transMat1[bin_to][bin_from]  = self.transMat2[bin_to][bin_from] / float(ss.M_0_runs[bin_from])
                nTotal[bin_from] += self.transMat2[bin_to][bin_from]
                if( bin_to > bin_from ):
                    nForward[bin_from] += self.transMat2[bin_to][bin_from]
                    
                ##re-init TM2 for next epoch
                del self.transMat2[bin_to][bin_from] 
            
        
        ##update the sampling frequencies
        target_forward         = ss.configfile.getint('spres_control','target_forward')
        max_shots              = ss.configfile.getint('spres_control','max_shots_per_bin')
        for bin_from in range( 0, self.nBins - 1 ):
            if nTotal[bin_from] > 0:
                ## Update number of runs using IS
                ##   ( equation 1 from berryman & schilling JCP 2010.)
                ss.logger_freshs.debug("bin " + str(bin_from) + " had " + str(nForward[bin_from]) + " runs forward of target " + str(target_forward))
                new_runs  = math.ceil( ss.M_0_runs[bin_from] * \
                        ( 1.0 - 0.5 * (nForward[bin_from] / float(target_forward) - 1.0)))
            
                ss.M_0_runs[bin_from] = int(new_runs)
                if ss.M_0_runs[bin_from] < 1 :
                    ss.M_0_runs[bin_from] = 1 ##ceiling function still allows neg & 0 numbers through
                elif ss.M_0_runs[bin_from] > max_shots:
                    ss.M_0_runs[bin_from] = max_shots
                     
        ##save the weights of individual states, based on the prev state vector, and the transmat
        for bin_to in range( 0, self.nBins ):

            self.epoch_points_old[bin_to]={} ##clear the list of old points

            for bin_from in self.epoch_points_buf[bin_to].keys():

                ##python will do a copy-by-reference here.
                self.epoch_points_old[bin_to][bin_from] = self.epoch_points_buf[bin_to][bin_from]

                ##Setting the weight in the database is currently inefficient
                ## so don't do it if it is the same as the default of 0.0.
                weight  = self.find_weight( bin_from, bin_to )
                if weight != 0.0 :
                    ss.storepoints.save_weights_of_points_after_t(  bin_from, bin_to, ss.epoch - ss.tau, weight ) 
                                 

            
            ss.logger_freshs.debug(cc.c_green +\
              "bin: " +str(bin_to) + " received: "+\
               str(len(self.epoch_points_buf[bin_to].keys()))+\
               str(" points")+ cc.reset)

            ##clear the list of new points,
            ## python should create a new empty dict, 
            ## and garbage-collect the old one.
            self.epoch_points_buf[bin_to]={} 

        self.advance_stateVec()
  
        ##save the state vector and associated transition matrix
        self.helper.write_matrix_sparse( ss.matfile, self.transMat1, self.nBins )
        self.helper.write_statevec( ss.vecfile, self.stateVector, self.nBins )
        
        ##do the flux calculation if requested
        if ss.absorb_at_B != 0:
            kB = self.calc_flux()       
            self.helper.write_rate(ss.outfile, ss.epoch, ss.lambdas[self.nBins-1], kB)

        if ss.epoch - self.start_epoch >= ss.configfile.getint('spres_control','max_epoch'):
            ss.logger_freshs.info(cc.c_red + "Quitting: reached max epoch" + str(self.stateVector) + cc.reset )
            exit()
        else:
            ss.logger_freshs.info(cc.c_red + "Epoch moved forward."+ cc.reset )

        ##move the active DB table forward 1,
        ## (tables are indexed by time at end of run)
        if ss.storepoints.use_multDB:
            ss.storepoints.increment_active_db( ss.epoch+ss.tau )
        else:
            ss.storepoints.increment_active_table( ss.epoch+ss.tau )
         
        ##if we are saving configs separately to the metadata, then need a new directory
        if ss.clients_use_fs == True:
            if not os.path.exists(ss.folder_conf+str(ss.epoch+ss.tau)):
                os.makedirs(ss.folder_conf+str(ss.epoch+ss.tau))

# -------------------------------------------------------------------------------------------------
    def advance_stateVec( self ):

        ##update the state vector    
        weight = 0.0
        
        for bin_to in range( 0, self.nBins ):
            self.flag_bin_complete[bin_to] = False
            self.stateVector_old[bin_to]   = self.stateVector[bin_to]
            self.stateVector[bin_to]       = 0.0

        for bin_to in range( 0, self.nBins ):
            for bin_from in self.transMat1[bin_to].keys():
                self.stateVector[bin_to] +=  self.transMat1[bin_to][bin_from] * self.stateVector_old[bin_from]
            weight += self.stateVector[bin_to]
        
        weight = 1.0 / weight
        for bin_to in range( 0, self.nBins ):
            self.stateVector[bin_to]  *= weight
        

# -------------------------------------------------------------------------------------------------
##move absorbed flux back into the source bin, or as near as possible
    def calc_flux( self ):
        ss = self.server 
        qFlag    = False
        kB       = 0.0
        renorm = 1.0

        ##find the rate
        if self.stateVector[self.nBins - 1] > 0.0:
            kB = self.stateVector[self.nBins - 1]
            if self.stateVector[self.nBins - 1] >= 1.0:
                ss.logger_freshs.info(cc.c_red +\
                      "Warning!!!! All flux reached the absorbing boundary, B!" + cc.reset )
            else:
                renorm = 1.0 / (1.0 - kB)

        ##rebalance the state vector
        if ss.replace_flux_at_A:
            tmpA = 0
            for i in range(self.nBins):
                if self.stateVector[i] != 0.0:
                    break
                tmpA = tmpA + 1
            self.stateVector[tmpA] += self.stateVector[self.nBins - 1]
            self.stateVector[self.nBins - 1] = 0.0    
        else:
            for i in range(self.nBins - 1):
                self.stateVector[i] *= renorm
            self.stateVector[self.nBins - 1] = 0.0

        ##return the rate
        return( kB / float(ss.tau) )
        
        


# -------------------------------------------------------------------------------------------------
    def find_weight( self, fromRow, row ):
        ss = self.server
        
        if( ss.epoch < ss.tau ):
            return( 1.0 )
        
        ##get the per-bin transition probability
        if fromRow in self.transMat1[row].keys():
            chanceFromHere  = self.stateVector[fromRow] *  self.transMat1[row][fromRow] 
        else:
            return( 0.0 )
        
        ##if it is non-zero then it needs to be normalised
        totalWeight = 0.0
        for inWeight in self.transMat1[row].values():
            totalWeight += inWeight
        chanceFromHere /= float(totalWeight)

        #point_count      = ss.storepoints.count_points_linking_ij_after_t(fromRow, row, ss.epoch - ss.tau)
        point_count = len(self.epoch_points_buf[row][fromRow])


        chanceFromHere /= float(point_count)
        
        return( chanceFromHere )
        


# -------------------------------------------------------------------------------------------------
    def build_parent_shot_list( self, row ):


        ss    = self.server
        self.parentShots = []
        scale = 0.0
        for fromRow in self.transMat1[row].keys():
            chance =  self.stateVector_old[fromRow] * self.transMat1[row][fromRow]
            if chance > 0.0:

		    scale     += chance


                    count      = len(self.epoch_points_old[row][fromRow])
                    chance_per = chance / float(count)

                    ##sort the eligible points by seed
                    ##in order to ensure determinism
                    self.epoch_points_old[row][fromRow].sort(key=lambda x : x[1])
                    for point in self.epoch_points_old[row][fromRow]:
                        shotId = point[0]
                        self.parentShots.append( [shotId, fromRow, chance_per] ) ##list of lists

        if scale > 0.0 and scale < self.min_weight:
            ss.logger_freshs.info(cc.c_red+ "Warning! Rounded away weight of "+str(scale)+\
	    	                                                    " for bin "+str(row)+cc.reset)
            scale = 0.0
	    self.parentShots = []


        ##divide by less than about 1e-300 seems to give NaNs
        if scale <= 0.0:

            ss.logger_freshs.debug(cc.c_blue+ "Found 0 shots into row " + str(row)+cc.reset)
            ss.logger_freshs.debug(cc.c_blue+"transmat in is: "+str(self.transMat1[row])+cc.reset)
            ss.logger_freshs.debug(cc.c_blue+"shots in were: ")
            for fromRow in self.transMat1[row].keys():
                ss.logger_freshs.debug("bin: "+str(fromRow)+" had weight: "+str(self.stateVector_old[fromRow]))
                #if self.stateVector_old[fromRow] == 0.0:
                #    ss.logger_freshs.debug("stateVec: "+str(self.stateVector_old)+cc.reset)
                #    exit("Error: shot recorded from bin which had zero weight. Do the transmats, state vectors and DBs match up?")
            ss.logger_freshs.debug(cc.reset)

            return( False ) ##there are no parent shots entering this bin, as yet.
        
        scale = 1.0 / scale;
        for i in range(len(self.parentShots)):
            self.parentShots[i][2] *= scale

        self.parentShots_buf_pt   = 0


        return( True )



# -------------------------------------------------------------------------------------------------
    def select_parent_shot_evenest( self, row ):
        ss = self.server
        
        ##build the array on first calling.... needs to be
        ##deleted after the final one.
        if len(self.parentShots) == 0:
            if not self.build_parent_shot_list( row ):
                return( None, None ) ##there are no parent shots entering this bin, as yet.

            self.weightToSpend = 1.0
	    if ss.M_0_runs[ss.act_lambda] >= 1:
		self.invNumShots = 1.0 / ss.M_0_runs[ss.act_lambda]
	    else:
	        self.invNumShots = 1.0

            self.needFlip      = False

        fromRow = -1
        ##begin by sampling evenly until it becomes needful to make random sampling
        if not self.needFlip:
            for i in range(self.parentShots_buf_pt, len(self.parentShots)):
                if  self.parentShots[i][2] >= self.invNumShots:

                    parentId = self.parentShots[i][0]
                    fromRow  = self.parentShots[i][1]

                    self.weightToSpend     -= self.invNumShots
                    self.parentShots[i][2] -= self.invNumShots
                    self.parentShots_buf_pt = i

                    break


        if fromRow == -1:
            self.needFlip = True

            ##do random sampling
            flip       =  random.random() * self.weightToSpend 
            totalTrans =  0.0;  
            for i in range(len(self.parentShots)): 
                 totalTrans += self.parentShots[i][2]
                 if( totalTrans >= flip ):
                     parentId = self.parentShots[i][0]
                     fromRow  = self.parentShots[i][1]
                     break
                 
            if fromRow == -1:
		 ss.logger_freshs.info(cc.c_red+ "WARNING selecting shots to " + str(row) +\
                                cc.reset)
	         ss.logger_freshs.info(cc.c_red+ "  Total weight in row: " + str(row) + " was " +\
		                str(totalTrans)+cc.reset)
	         ss.logger_freshs.info(cc.c_red+ "  And flipped a: " + str(flip) +cc.reset)
                 ss.logger_freshs.info(cc.c_red+ "  Some kind of rounding error. Quitting." +cc.reset)
		 quit();


           
        return (fromRow, parentId)
  
# -------------------------------------------------------------------------------------------------
  
# Analyze jobtype 3 fixedtau
    def analyze_job3_success(self, client, ddata, runid):
      
        ss = self.server
        
        ##define the new lambda as the new bin boundary above the current x-coordinate of the point
        new_lambda      = ddata['newlambda'][0]
        new_lambda_bin  = int(self.get_bin_index( new_lambda ))
        
        ##read the prev lambda from the incoming message
        prev_lambda_bin = ddata['parentlambda']   
        
        ##have a go at working out how long it took
        if 'runtime' in ddata:
            runtime = ddata['runtime']
        else:
            runtime = time.time() - ss.client_runtime[str(client)]
                
        ##get the RNG seed that was used
        start_seed = ddata['seed']   
        
        ss.logger_freshs.debug(cc.c_magenta + str(int(prev_lambda_bin))+\
                                    " to "+ str(new_lambda_bin)+\
                                    " of "+ str(self.nBins) + cc.reset )

        ##save the seed to an array of dicts on runids.
        if int(prev_lambda_bin) in self.epoch_points_buf[new_lambda_bin].keys():
            self.epoch_points_buf[new_lambda_bin][prev_lambda_bin].append((runid, start_seed))
        else:
            self.epoch_points_buf[new_lambda_bin][prev_lambda_bin]=[(runid, start_seed)]

        ##save the whole point to the DB.
        ss.storepoints.add_point_ij(new_lambda_bin, \
                             ddata['points'][0],
                             ddata['origin_points'], 
                             ss.epoch + ddata['calcsteps'], 
                             ddata['ctime'], 
                             runtime, 1,
                             ss.M_0_runs[prev_lambda_bin], runid, start_seed, prev_lambda_bin, new_lambda)
        
        ##log the number of shots forward between a given pair of bins
        if prev_lambda_bin in self.transMat2[new_lambda_bin].keys():
            self.transMat2[new_lambda_bin][prev_lambda_bin] += 1.0
        else:
            self.transMat2[new_lambda_bin][prev_lambda_bin]  = 1.0

        #del ddata

                
        return    

    def try_launch_job3(self, client):

        ss=self.server

        ##if we don't need runs from any further bins at this epoch
        if ss.act_lambda >= self.nBins or (ss.absorb_at_B > 0 and ss.act_lambda >= self.nBins - 1):
            ss.logger_freshs.debug(cc.c_blue + 'waiting for end of epoch, not launching '+\
                                   str(ss.act_lambda)+" of "+ str(self.nBins)+cc.reset)
            return( False )

        launchOK = False
        while not launchOK:
            
            # if we don't still need runs from this bin
            if ss.run_count[ss.act_lambda] >= ss.M_0_runs[ss.act_lambda]:

                ss.logger_freshs.debug(cc.c_blue + 'have enough jobs in bin: '+\
                                   str(ss.act_lambda)+", "+ str(ss.run_count[ss.act_lambda]) +\
                                   " of " + str(ss.M_0_runs[ss.act_lambda])+cc.reset)

                self.increment_bin_index()

            ##if we don't need runs from any further bins at this epoch
            if ss.act_lambda >= self.nBins or (ss.absorb_at_B > 0 and ss.act_lambda >= self.nBins - 1):
                ss.logger_freshs.debug(cc.c_blue + 'waiting for end of epoch, not launching '+\
                                   str(ss.act_lambda)+" of "+ str(self.nBins)+cc.reset)
                return( False )

            # if there is an algorithmic reason we can't start any from this bin
            launchOK = client.start_job3_fixedtau()
            if not launchOK:
                ss.logger_freshs.debug(cc.c_blue + 'Could not launch: act_lambda = '+\
                                   str(ss.act_lambda)+" of "+ str(self.nBins)+cc.reset)
                self.increment_bin_index()
            else:
                return( True )
     
            ##if we don't need runs from any further bins at this epoch
            if ss.act_lambda >= self.nBins or (ss.absorb_at_B > 0 and ss.act_lambda >= self.nBins - 1):
                ss.logger_freshs.debug(cc.c_blue + 'waiting at bin: '+\
                                   str(ss.act_lambda)+" of "+ str(self.nBins)+cc.reset)
                return( False )

       

# -------------------------------------------------------------------------------------------------
    def get_bin_boundary(self, actual_lambda):
        
        ss=self.server
        
        bin_lambda = ss.lambdas[0]
        i          = 0
        while bin_lambda < actual_lambda and i <= ss.nohs + 2:
            i          = i + 1
            bin_lambda = ss.lambdas[i]
        
        return (bin_lambda)
        
# -------------------------------------------------------------------------------------------------
    def get_bin_index(self, actual_lambda):
        
        ss=self.server
        
            
        bin_lambda = ss.lambdas[0]
        i          = 0
        while bin_lambda < actual_lambda and i < ss.nohs + 1:
            i          = i + 1
            bin_lambda = ss.lambdas[i]
        
        return ( i )
     
# -------------------------------------------------------------------------------------------------

# -------------------------------------------------------------------------------------------------
    def increment_bin_index(self):
        
        self.server.act_lambda += 1
        self.parentShots        = []


# -------------------------------------------------------------------------------------------------
    def reset_bin_index(self):
        
        self.server.act_lambda  = 0
        self.parentShots        = []

     
# -------------------------------------------------------------------------------------------------
