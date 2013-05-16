# -*- coding: utf-8 -*-
# Copyright (c) 2013 Kai Kratzer, Universität Stuttgart, ICP,
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

# Formatting
import modules.concolors
import ConfigParser

import math

import modules.server
# -------------------------------------------------------------------------------------------------

#### NSFFS-SPECIFIC SERVER CLASS ####
class nsffs_sampling_control():
  
    ##init, saving a backpointer to the parent "server" class which handles comms.
    def __init__(self, my_server):
        self.server     = my_server
        ss              = self.server ##alias to save on typing

        self.branch_tau    = ss.configfile.getboolean('Nsffs_control', 'branch_tau') 
        self.branch_lambda = ss.configfile.getboolean('Nsffs_control', 'branch_lambda')     
        
        ##init the 2D crossings histogram
        self.Histogram = []
        self.taupoint  = []
        for i in range( ss.configfile.getint('hypersurfaces', 'taucount') ):
            self.Histogram.append([0.0] * (ss.configfile.getint('hypersurfaces', 'lambdacount') + 2))  
            self.taupoint.append(ss.configfile.getint('hypersurfaces', 'tau'+str(i+1)))

        ##init the tree counter
        self.treecount_S      = 0

        ##init the queue of pending runs
        self.pendingRuns_G    = []

# --------------------------------------
        
    def launch_jobs(self):
        ss=self.server

        ## No jobs are *actually* launched until a client connects,
        ## see the clienthandler.py functions.
        self.pendingRuns_G.append(0)


# -------------------------------------------------------------------------------------------------

    # Analyze jobtype success
    def analyze_job(self, client, ddata, runid):
        
        ss = self.server
        
        # store retrieved config points and increment counter
        the_jobs_lambda = ddata['act_lambda']
 
        ##get the RNG seed that was used
        try:
            start_seed = ddata['seed']   
        except:
            start_seed = 0
            ss.logger_freshs.warn(concolors.c_red +\
                        'WARNING! Did not receive seed from client, setting to zero.' + concolors.reset)

        # check if client has its runtime in data. If not, use own runtime counter
        if 'runtime' in ddata:
            runtime = ddata['runtime']
        else:
            runtime = time.time() - ss.client_runtime[str(client)]

        ##save the job.
        ss.storepoints.add_point(the_jobs_lambda, \
                                             ddata['points'], \
                                             ddata['origin_points'], \
                                             ddata['calcsteps'], \
                                             ddata['ctime'], \
                                             runtime, \
                                             ss.M_0[the_jobs_lambda-2], \
                                             runid, \
                                             start_seed)
                    #ss.print_status()
              
       
        ##save the id of the datapoint in the "pending" queue
        if ddata['ctime'] <= self.taupoint[-1] : ##pythonism: "-1" indexes the last item of the list.
            self.pendingRuns_G.append(runid)
              
        ss.start_idle_clients()
                
            

# -------------------------------------------------------------------------------------------------

    def try_launch_job(self, client):

        ss=self.server

        if len(self.pendingRuns_G) > 0 :
            
            #select a start config id. 
            config_id = self.pendingRuns_G.pop()

            if str(config_id) != str(0):
                ##append the start config itself onto an empty list.
                config=[]
                tau, rc_index = ss.storepoints.return_point_by_id( config_id, config )
                if len(config) == 0:
                    self.server.logger_freshs.info(concolors.c_red + 'ERROR! Could not start job from config ' +\
                                                str(configId) + concolors.reset)
                    exit( "Error finding configs." )
                if config[0] == None:
                    self.server.logger_freshs.info(concolors.c_red + 'ERROR! Could not start job from config ' +\
                                                str(configId) + concolors.reset)
                    exit( "Error finding configs." )
            else:
                tau      = 0
                rc_index = 0
                config   = ['escape']

            #define job exit conditions
            if self.branch_tau :
                nextTau    = self.get_nextTau(tau)
                if nextTau != False:
                    deltaTau  = nextTau - taupoint
                else:
                    exit( "Error finding tau." )
            else:
                deltaTau = 0

            #check if branching on lambda
            if self.branch_lambda :
                if rc_index > 0:
                    branch_rc_lower = ss.lambdas[rc_index - 1]   
                else:
                    branch_rc_lower = ss.lambdas[0] ##unclear what to send as a null value
                
                if rc_index < len(ss.lambdas):
                    branch_rc_upper = ss.lambdas[rc_index]
                else:
                    branch_rc_upper = ss.lambdas[rc_index - 1] ##unclear what to send as a null value

                test_rc_every = ss.test_rc_every
            else:
                test_rc_every = 0

            # start the job
            client.start_job( config,         \
                              config_id,      \
                              deltaTau,       \
                              test_rc_every,  \
                              branch_rc_upper,\
                              branch_rc_lower )

            return True
        else:
            return False

# -------------------------------------------------------------------------------------------------
    ##look up tau index
    def get_nextTau( self, tau ):
        if tau > 0:
            tauIndex = self.taupoint.index(tau)
            if tauIndex < len(self.taupoint):
                return self.taupoint[tauIndex + 1]
            else:
                return False
        else:
            return self.taupoint[0]

