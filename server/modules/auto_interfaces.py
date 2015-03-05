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

import concolors as cc
import random
import time

class auto_interfaces():
    def __init__(self, server):
        self.server = server

        # switch between real runs and exploring clients
        self.exmode       = False      # exploring mode for interface placement
        self.arrived_in_B = False

        if not self.read_config():
            return

        # This is where the act_lam id starts. Should be larger than number of possible interfaces.        
        self.loffset = 1337
        
        # unique act_lam id for explorers
        self.ex_act_lambda = self.loffset
        
        # move unit        
        self.munit = (self.server.B-self.server.A) * self.auto_moveunit / 100.0

        # max move is then given by munit * self.auto_max_move_fac (only for moving the thing to the right)
        self.auto_max_move_fac = 20
        
# -------------------------------------------------------------------------------------------------
    # check if option is in configfile
    def option_in_configile(self,option):
        ss = self.server
        if ss.configfile.has_option('auto_interfaces', option):
            return True
        return False

# -------------------------------------------------------------------------------------------------
    # check if section is in configfile
    def  section_in_configile(self,option):
        ss = self.server
        if ss.configfile.has_section(option):
            return True
        return False

# ------------------------------------------------------------------------------------------------
    # read the configuration file for this module
    def read_config(self):
        ss = self.server

        # Check that this section is even present
        if not self.section_in_configile('auto_interfaces'):
            self.auto_interfaces = 0
            return False
            
        # Auto Interface switch
        if self.option_in_configile('auto_interfaces'):
            self.auto_interfaces = ss.configfile.getint('auto_interfaces', 'auto_interfaces')
        else:
            self.auto_interfaces = 0

        if self.auto_interfaces == 0:
            return False


        try:
            # number of trials
            self.auto_trials = ss.configfile.getint('auto_interfaces', 'auto_trials')
            # number of runs, which will be performed, if interface position is determined
            self.auto_runs = ss.configfile.getint('auto_interfaces', 'auto_runs')
            # min flux which is accepted. Be careful, this is only for the estimation! Don't be too strict.
            self.auto_flux_min = ss.configfile.getfloat('auto_interfaces', 'auto_flux_min')
            # max flux which is accepted. Be careful, this is only for the estimation! Don't be too strict.
            self.auto_flux_max = ss.configfile.getfloat('auto_interfaces', 'auto_flux_max')
            self.auto_moveunit = ss.configfile.getfloat('auto_interfaces', 'auto_moveunit')
            self.auto_mindist = ss.configfile.getfloat('auto_interfaces', 'auto_mindist')
            self.auto_mindist_orig = self.auto_mindist
            # order parameter can be considered as int (e.g. number of particles with property x)
            self.auto_lambda_is_int = ss.configfile.getint('auto_interfaces', 'auto_lambda_is_int')
            # set max steps for exploring client. Client must support this.
            self.auto_max_steps = ss.configfile.getint('auto_interfaces', 'auto_max_steps')
            self.auto_histo     = ss.configfile.getint('auto_interfaces', 'auto_histo')
            #self.auto_histo_thresh = ss.configfile.getfloat('auto_interfaces', 'auto_histo_thresh')
            self.auto_min_points = ss.configfile.getfloat('auto_interfaces', 'auto_min_points')
             
        except Exception as e:
            ss.logger_freshs.error(cc.c_red + "Auto_interfaces is turned on, but problem while reading auto_interfaces config, exception: "+str(e)+cc.reset)
            exit(1)
        
        if self.option_in_configile('auto_min_explorer_steps'):
            self.auto_min_explorer_steps = ss.configfile.getint('auto_interfaces', 'auto_min_explorer_steps')
        else:
            self.auto_min_explorer_steps = 0

        if self.option_in_configile('auto_mindist_detect'):
            self.auto_mindist_detect = ss.configfile.getint('auto_interfaces', 'auto_mindist_detect')
        else:
            self.auto_mindist_detect = 0

        return True

# -------------------------------------------------------------------------------------------------    
    # change the exploring mode interface
    def change_ex_interface(self):
        self.ex_launched.append(0)
        self.ex_success.append(0)
        self.ex_ctime.append(0.0)
        self.ex_returned.append(0)
        self.max_lams.append([])
        self.ex_act_lambda += 1

# -------------------------------------------------------------------------------------------------  

    def get_mindist(self,interface):
        ss = self.server

        mindist = self.auto_mindist_orig
        
        if self.auto_mindist_detect == 0:
            return mindist

        ## idea: get maximum stepwidth of runs from customdata
        #import re
        #import numpy as np
        ## 2d array, 1 element corresponds to one trajectory
        #cudtmp = ss.storepoints.return_customdata(interface)
        ## loop over trajectories
        #for el in cudtmp:
        #    histodata = []
        #    # extract rcs after label 'allrcs'
        #    candi = re.sub('.*allrcs','', el).split()
        #    histodata = np.array(candi).astype(np.float)
        #    if len(histodata) > 1:
        #        curmax = np.max(np.diff(histodata))
        #    else:
        #        # "only 1 val:", histodata
        #        curmax = 0
        #    if curmax > mindist:
        #        mindist = curmax

        ## maximum rcval - last known interface
        mindist = ss.storepoints.return_max_rc(interface) - ss.lambdas[-1]
        if self.auto_lambda_is_int > 0:
            # add 1, if int
            mindist += 1
        else:
            # add fraction of original mindist
            mindist += self.auto_mindist_orig / 10.

        # reset if not valid or smaller than original mindist
        if mindist < 0 or self.auto_mindist_orig > mindist:
            mindist = self.auto_mindist_orig

        return mindist
        
# -------------------------------------------------------------------------------------------------
    # set initial values for the exploring mode
    def init_variables(self):
        ss = self.server
        self.ex_launched = [0]      # launched runs
        self.ex_success  = [0]      # successcount
        self.ex_ctime    = [0.0]    # ctime
        self.ex_returned = [0]      # returned runs
        self.isset_lhigh = False
        self.isset_llow = False
        self.last_placed = 'low'
        self.ex_deactivated = []    # array for deactivating exploring interfaces
        self.ex_priority = []       # array for priority exploring runs
        self.ex_ghost_cand = []     # array for storing virtual explored points, they are transferred into ghost_db at success    
        self.max_lams = [[]]
        self.ex_lambdas = []
        # obtain minimal interface distance
        self.auto_mindist = self.get_mindist( ss.storepoints.biggest_lambda() )
        ss.logger_freshs.info(cc.c_green + "Minimal interface distance is " + str(self.auto_mindist) + cc.reset)
        
# -------------------------------------------------------------------------------------------------
    # turn on exploring mode
    def exmode_on(self):
        ss = self.server
        
        if self.exmode == False and ss.auto_interfaces:
            self.exmode = True
            self.init_variables()

            if self.auto_histo:
                # set the lambda to B, because this is the max_value for lambda to be returned
                self.ex_lambdas = [ss.B]
            else:
                try:
                    last_lam = ss.lambdas[-1]
                except:
                    ss.logger_freshs.warn(cc.c_red + 'No borderA given. Guessing first interface somewhere right of A and tuning Escape Flux!'  + \
                                          cc.reset)
                    last_lam = ss.A

                self.ex_lambdas = [ self.guess_lambda(last_lam, 0) ]

                ss.logger_freshs.info(cc.c_magenta + 'Lambda candidates: ' + str(self.ex_lambdas) + \
                                      cc.reset)

# -------------------------------------------------------------------------------------------------

    def exmode_off(self):
        ss = self.server
        fsc = self.server.ffs_control
        if self.exmode == True:
            self.exmode = False
            # append new lambda
            ss.lambdas.append(self.ex_lambda)
            ss.logger_freshs.info(cc.c_green + cc.bold + 'Found lambda: '  + str(self.ex_lambda) + cc.reset)
            if ss.use_ghosts and ss.act_lambda > 0 and not self.auto_histo:
                # use explorer runs as ghosts on this interface if possible
                self.explored2ghost()
            if self.ex_lambda < ss.B and ss.act_lambda == 0:
                fsc.append_to_lamconf('hypersurfaces','borderA', str(ss.lambdas[ss.act_lambda]))
            elif self.ex_lambda < ss.B:
                fsc.append_to_lamconf('hypersurfaces','lambda' + str(ss.act_lambda), str(ss.lambdas[ss.act_lambda]))
                ss.start_idle_clients()
            else:
                fsc.append_to_lamconf('hypersurfaces','borderB', str(ss.B))
                self.arrived_in_B = True
                ss.start_idle_clients()
                
            self.loffset = self.ex_act_lambda + 1

            # Do this only if clients are able to abort jobs!
            #self.convert_explorers()

# -------------------------------------------------------------------------------------------------

    def convert_explorers(self):
        ss = self.server
        tmp_clients = []
        
        for client in ss.explorer_clients:
            tmp_clients.append(client)
            
        for client in tmp_clients:
            ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------

    def explorer_possible(self, i):
        if (not self.is_deactivated_ex_lambda(i)) and ( self.ex_launched[i] < self.auto_trials ):
            return True
        return False

# -------------------------------------------------------------------------------------------------

    def start_explorer(self, client):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': start_explorer' + cc.reset)
        
        if client in ss.explorer_clients:
            ss.logger_freshs.debug(cc.c_magenta + __name__ + ': client is already explorer! Not starting again.' + cc.reset)
            return False

        if self.arrived_in_B:
            ss.logger_freshs.debug(cc.c_magenta + __name__ + ': No need for an explorer job.' + cc.reset)
            return False
        
        if self.auto_histo:
            if len(ss.lambdas) == 0:
                for i in range(len(self.ex_launched)):
                    if self.ex_launched[i] < self.auto_trials:
                        self.ex_launched[i] += 1
                        ss.logger_freshs.debug(cc.c_magenta + str(client) + ': starting job1' + cc.reset)
                        client.start_job1(0)
                        return True
            else:
                if len(ss.lambdas) == ss.act_lambda:
                    lamget = ss.act_lambda - 1
                else:
                    lamget = ss.act_lambda

                # check if there are enough points to start
                npoints = ss.storepoints.return_nop(lamget)
                ndesired = int(round(self.auto_min_points * ss.M_0_runs[lamget]))
                if npoints >= ndesired:
                    for i in range(len(self.ex_launched)):
                        if self.ex_launched[i] < self.auto_trials:
                            self.ex_launched[i] += 1
                            ss.logger_freshs.debug(cc.c_magenta + str(client) + ': starting job2' + cc.reset)
                            client.start_job2(0)
                            ss.start_idle_clients()
                            return True
                else:
                    ss.logger_freshs.debug(cc.c_magenta + 'Not enough points on last interface to start explorer (' + \
                                          str(npoints) + '/' + str(ndesired) + ')' + cc.reset)
                    return False

        else:
            # check for priority run
            for i in self.ex_priority:
                if self.explorer_possible(i):
                    ss.logger_freshs.debug(cc.c_magenta + 'Starting high-priority explorer' + cc.reset)
                    self.ex_launched[i] += 1
                    if len(ss.lambdas) == 0:
                        client.start_job1(i)
                    else:
                        client.start_job2(i)
                    return True
                    
            # check for normal run
            for i in range(len(self.ex_launched)):
                if self.explorer_possible(i):
                    ss.logger_freshs.debug(cc.c_magenta + 'Starting low-priority explorer' + cc.reset)
                    self.ex_launched[i] += 1
                    if len(ss.lambdas) == 0:
                        client.start_job1(i)
                    else:
                        client.start_job2(i)
                    return True

        ss.logger_freshs.debug(cc.c_magenta + 'Failed to start explorer' + cc.reset)
        return False


# -------------------------------------------------------------------------------------------------
    # transfer explored points to ghost_db
    def explored2ghost(self):
        ss = self.server

        snum = 0
        for gp in self.ex_ghost_cand:
            if gp[0] == self.ex_placed_index:

                if len(ss.lambdas) == ss.act_lambda + 2:
                    ghostlam = ss.act_lambda + 1
                else:
                    ghostlam = ss.act_lambda

                ss.logger_freshs.debug(cc.c_magenta + 'Using lambda=' + str(ghostlam) + ' for explorer2ghost runs.' + \
                                       cc.reset)                    
                ss.ghostpoints.add_point( ghostlam, gp[1], gp[2], gp[3], gp[4], gp[5], gp[6], gp[7], gp[8], gp[9], ss.lambdas[ghostlam], 0, 0, gp[10] )
                snum += 1

        ss.logger_freshs.info(cc.c_magenta + 'Saved ' + str(snum) + ' exploring runs (index ' + str(self.ex_placed_index) + \
                              ') as ghostpoints on this interface.' + \
                              cc.reset)

                
        ss.ghostpoints.commit()
        

# -------------------------------------------------------------------------------------------------
    # deactivate lambdas because better values --> no more runs will be performed on these interfaces
    def deactivate_ex_lambdas(self):
        ss = self.server
        self.ex_deactivated = []
        for i in range(len(self.ex_lambdas)):
            if self.isset_lhigh:
                if self.ex_lambdas[i] < self.ex_lam_high:
                    self.ex_deactivated.append(i)
            if self.isset_llow:
                if self.ex_lambdas[i] > self.ex_lam_low:
                    self.ex_deactivated.append(i)

        # check if clients calculate on deactivated lambda
        for client in ss.explorer_clients:
            if self.cemlti(ss.explorer_clients[client]) in self.ex_deactivated:
                ss.check_for_job(client)
        
# -------------------------------------------------------------------------------------------------
    # check if lambda_index is deactivated
    def is_deactivated_ex_lambda(self,i_lam):
        if i_lam in self.ex_deactivated:
            return True
            
        return False
    
# -------------------------------------------------------------------------------------------------

    def get_weight(self,hilo,flux):
        if hilo == 'high':
            ffac = self.auto_max_move_fac / (1.0 - self.auto_flux_max)
            dflux = (flux - self.auto_flux_max)
            # linear move
            th = ffac * dflux
            if th <= 0:
                th = 1
            return th
        else:
            ffac = self.auto_max_move_fac / (2.0 * self.auto_flux_min)
            dflux = (flux - self.auto_flux_min)
            th = ffac * dflux
            if th >= 0:
                th = -1
            return th

# -------------------------------------------------------------------------------------------------
    def check_flux(self, flux, lam, lam_id):
        ss = self.server
        # was flux in range?
        if flux >= self.auto_flux_min and flux <= self.auto_flux_max:
            self.ex_lambda = self.ex_lambdas[lam]
            self.ex_placed_index = lam_id
            self.exmode_off()
            
        elif flux > self.auto_flux_max:
            # Flux was too high
            th = self.get_weight('high', flux)
            ex_next_lambda = self.guess_lambda(self.ex_lambdas[lam], th, 'fluxcheck')
            self.ex_lambdas.append(ex_next_lambda)
            if ex_next_lambda >= ss.B:
                ss.logger_freshs.debug(cc.c_cyan + 'Flux is too high and next lambda would be >= B, setting to B.' + \
                                       cc.reset)
                self.ex_lambda = ss.B
                self.exmode_off()
            else:
                self.change_ex_interface()
                #self.ex_priority.append(self.cemlti(self.ex_act_lambda))
                
        else:
            # Flux was too small
            th = self.get_weight('low', flux)
            self.ex_lambdas.append(self.guess_lambda(self.ex_lambdas[lam], th, 'fluxcheck'))
            self.change_ex_interface()
            #self.ex_priority.append(self.cemlti(self.ex_act_lambda))
                  
# -------------------------------------------------------------------------------------------------
    def check_returned_explorers(self, lam, lam_id, client):
        ss = self.server
        ss.logger_freshs.debug(cc.c_cyan + 'Explorer ' + client.name + ' returned on lambda ' + str(lam) + \
                              cc.reset)

        #self.in_act_lamrange(lam_id)
        if self.exmode and lam_id >= self.loffset:
            ss.logger_freshs.debug(cc.c_cyan + 'Launched: ' + str(self.ex_launched)+ cc.reset)
            ss.logger_freshs.debug(cc.c_cyan + 'Returned: ' + str(self.ex_returned)+ cc.reset)
            ss.logger_freshs.debug(cc.c_cyan + 'Success : ' + str(self.ex_success) + cc.reset)
            ss.logger_freshs.debug(cc.c_cyan + 'Deactivated : ' + str(self.ex_deactivated) + cc.reset)
            ss.logger_freshs.debug(cc.c_cyan + 'Priority : ' + str(self.ex_priority) + cc.reset)
            
            if self.ex_returned[lam] >= self.auto_trials:
            
                # histogram method
                if self.auto_histo:
                    # if all clients arrive in B, they have success and therefore we return B
                    if self.ex_success[lam] < self.ex_returned[lam]:
                        lhp = len(self.max_lams[lam])
                        
                        # sort Maximum lambda array
                        self.max_lams[lam].sort()
                        ss.logger_freshs.debug(cc.c_cyan + 'Array of maximum lambdas is ' + str(self.max_lams[lam]) + cc.reset)
                        
                        # we do not know exactly, if our estimated flux will be reached by the clients
                        #target_flux = self.auto_flux_min
                        target_flux = self.auto_flux_max
                        #target_flux = 0.5 * (self.auto_flux_max + self.auto_flux_min)

                        foundl = False
                        foundh = False
                        
                        i_low = 0
                        i_high = 0
                        
                        # estimating flux depending on location of the interface
                        if lhp != 0:
                            for ttl in range(lhp):
                                # flux is inverse to array index
                                flux = (float(lhp) - float(ttl)) / float(lhp)
                                # we start at a high flux and go down
                                if not foundl and flux < self.auto_flux_min:
                                    foundl = True
                                    # one before would have been ok
                                    i_low = ttl - 1
                                # the first flux in range is the highest flux
                                if not foundh and flux <= self.auto_flux_max:
                                    foundh = True
                                    i_high = ttl
                            
                                # we have both, the high and the low flux index, break for loop
                                if foundh and foundl:
                                    break
                            
                            
                            if foundh and foundl:
                                #lambda_cand = self.int_float( 0.5*(self.max_lams[lam][i_low] + self.max_lams[lam][i_high]) )
                                lambda_cand = self.int_float( self.max_lams[lam][int(round(0.5*(i_high+i_low)))] )
                            elif foundh:
                                lambda_cand = self.int_float( self.max_lams[lam][i_high] )
                            elif foundl:
                                lambda_cand = self.int_float( self.max_lams[lam][i_low] )
                            else:
                                # No lambda found. Returning first entry of array
                                lambda_cand = self.int_float( self.max_lams[lam][0] )
                        else:
                            lambda_cand = self.int_float(ss.lambdas[-1] + self.auto_mindist)
                        
                        if lambda_cand < ss.lambdas[-1] + self.auto_mindist:
                            lambda_cand = self.int_float(ss.lambdas[-1] + self.auto_mindist)

                        # if we are 99 % in B, use B as the next (and thus, last) interface
                        if lambda_cand >= ss.A + 0.99 * (ss.B - ss.A):
                            self.ex_lambda = ss.B
                            self.exmode_off()
                            return

                        if self.check_lam(lambda_cand):
                            self.ex_lambda = lambda_cand
                            self.exmode_off()
                        else:
                            ss.logger_freshs.warn(cc.c_red + 'Lambda is not in range. Waiting for more explorers.' + \
                                                  cc.reset)
                            # restart
                            self.exmode = False
                            self.exmode_on()
                            return
                        
                    else:
                        self.ex_lambda = ss.B
                        self.exmode_off()
                    

                # interface placement mode
                else:
                    if len(ss.lambdas) == 0:
                        try:
                            flux = float(self.ex_success[lam]) / self.ex_ctime[lam]
                        except:
                            flux = 0.0
                        ss.logger_freshs.info(cc.c_magenta + 'Estimated flux: ' + str(flux) + cc.reset)
                        self.check_flux(flux, lam, lam_id)
                    else:
                        if self.ex_success[lam] <= self.ex_launched[lam]:
                            flux = float(self.ex_success[lam]) / float(self.ex_launched[lam])
                            ss.logger_freshs.info(cc.c_magenta + 'Estimated flux: ' + str(flux) + cc.reset)
                            self.check_flux(flux, lam, lam_id)
                        else:
                            ss.logger_freshs.warn(cc.c_red + 'Flux is too big. Dang! '  + \
                                                  'Look at the source code in ffs_sampling_control.py to fix this ' + cc.reset)
        else:
            ss.logger_freshs.info(cc.c_magenta + 'Omitting exploring run of ' + client.name + \
                                  ', because exploring mode is '  + \
                                  'already finished on ex_interface ' + \
                                  str(lam_id) + \
                                  cc.reset)

# -------------------------------------------------------------------------------------------------
    # if many clients and lambda not found yet, another virtual interface is added and explored
    def add_parallel_lambda(self):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': add_parallel_lambda' + cc.reset)
        
        if len(ss.lambdas) == ss.act_lambda:
            lamget = ss.act_lambda - 1
        else:
            lamget = ss.act_lambda

        # check if there are enough points to start
        ndesired = int(round(self.auto_min_points * ss.M_0_runs[ss.act_lambda]))
        if ss.storepoints.return_nop(lamget) < ndesired:
            return False
        
        if not self.auto_histo:
            last_lam_index = len(self.ex_lambdas) - 1
            last_lam = self.ex_lambdas[last_lam_index]
            # check if more than threshold runs have returned
            if self.ex_returned[last_lam_index] > float(self.auto_trials) / 2.0:
                try:
                    if len(ss.lambdas) == 0:
                            flux = float(self.ex_success[last_lam_index]) / self.ex_ctime[last_lam_index]
                    else:
                        flux = float(self.ex_success[last_lam_index]) / float(self.ex_returned[last_lam_index])
                
                    if flux > self.auto_flux_max:
                        # Flux too high
                        th = self.get_weight(self,'high',flux)
                        ex_next_lambda = self.guess_lambda(self.ex_lambdas[lam], th,'add_parallel')

                    else:
                        # Flux too small
                        th = self.get_weight(self,'low',flux)
                        
                    ex_next_lambda = self.guess_lambda(last_lam, th,'add_parallel')        
                except:
                    ex_next_lambda = self.guess_lambda(last_lam, 0)
            else:
                ex_next_lambda = self.guess_lambda(last_lam, 0)
            
            ss.logger_freshs.info(cc.c_magenta + \
                                  'Added parallel lambda: ' + str(ex_next_lambda)+ \
                                  cc.reset)
            self.ex_lambdas.append(ex_next_lambda)

        self.change_ex_interface()
        return True

# -------------------------------------------------------------------------------------------------
    # convert exploring mode lambda to index
    def cemlti(self,lam):
        cand = lam - self.loffset
        if cand < 0:
            ss=self.server
            ss.logger_freshs.warn(cc.c_red + 'Client returned wrong exploring mode index, cannot convert.' + cc.reset)
            return lam
        return cand

# -------------------------------------------------------------------------------------------------
    # convert index to exploring mode lambda
    def citeml(self,ind):
        cand = ind + self.loffset
        return cand
        
# -------------------------------------------------------------------------------------------------

    # check if lambda is in current exploration range -> avoid wrong reporting of 
    # clients which are still calculating around
#    def in_act_lamrange(self,lam_id):
#        ss = self.server
#        if lam_id in self.ex_lams[ss.act_lambda]:
#            return True

#        return False

# -------------------------------------------------------------------------------------------------

    # Check if lambda is in range
    def check_lam(self, lam):
        ss = self.server

        #if lam in self.ex_lambdas:
        #    ss.logger_freshs.debug(cc.c_cyan + 'Lambda ' + str(lam) + ' is already explored, array is ' + \
        #                           str(self.ex_lambdas) + cc.reset)
        #    return 0
        if lam > ss.A and lam <= ss.B:
            try:
                if lam >= (max(ss.lambdas) + self.auto_mindist):
                    ss.logger_freshs.debug(cc.c_cyan + 'Lambda ' + str(lam) + ' is ok, array is ' + \
                                           str(self.ex_lambdas) + cc.reset)

                    return 1
            except:
                if lam >= (ss.A + self.auto_mindist):
                    ss.logger_freshs.debug(cc.c_cyan + 'Lambda ' + str(lam) + ' is ok, array is ' + \
                                           str(self.ex_lambdas) + cc.reset)

                    return 1
                else:
                    ss.logger_freshs.debug(cc.c_cyan + 'Lambda ' + str(lam) + ' is too close to last interface, array is ' + \
                                           str(self.ex_lambdas) + cc.reset)

                    return 0
        else:
            ss.logger_freshs.debug(cc.c_cyan + 'Lambda ' + str(lam) + ' is not in valid range between A and B.' + cc.reset)
            return 0

        return 0

# -------------------------------------------------------------------------------------------------

    def int_float(self,lam):
        ss = self.server
        if self.auto_lambda_is_int:
            # returning rounded lambda (not int) because of compatibility
            round_lam = round(lam)
            if len(ss.lambdas) == 0:
                if round_lam > ss.A:
                    return round_lam
                else:
                    return round_lam + 1.0
            else:
                if round_lam > max(ss.lambdas):
                    return round_lam
                else:
                    return round_lam + 1.0
        return lam

# -------------------------------------------------------------------------------------------------

    def guess_whatever(self):
        ss = self.server
        ss.logger_freshs.debug(cc.c_cyan + 'Returning random moved lambda.' + cc.reset)
        fit = False

        move_span = 3.0

        max_iter = 100
        tries = 0

        while not fit:
            retval = self.int_float( max(ss.lambdas) + random.random() * move_span * self.munit )
            tries += 1
            if self.check_lam(retval):
               return retval

            if tries >= max_iter:
                tries = 0
                move_span += 1.0
            
# -------------------------------------------------------------------------------------------------        

    # Guess the next lambda from various criteria, good luck understanding the logic.
    def guess_lambda(self, last_lam, th=0.0, mode='default'):
        ss = self.server

        if self.isset_lhigh and self.isset_llow:
            # if borders are unreasonable, reset them.
            borderdist = self.ex_lam_low - self.ex_lam_high
            if borderdist < self.auto_mindist:
                ss.logger_freshs.debug(cc.c_cyan + 'Resetting lambda borders, because of a distance of ' + \
                                       str(borderdist) + cc.reset)
                self.isset_lhigh = False
                self.isset_llow = False
                #self.deactivate_ex_lambdas()

        if th > 0.0:
            ss.logger_freshs.debug(cc.c_cyan + 'Last probability was too high, moving interface to the right (th=' + str(th) + ').' + cc.reset)
            # Now we know a lambda where the flux was too high. Other lambdas should be placed right of that value
            if self.isset_lhigh:
                if last_lam > self.ex_lam_high and mode == 'fluxcheck':
                    self.ex_lam_high = last_lam   
                    ss.logger_freshs.debug(cc.c_cyan + 'Lower bound of lambda is: ' + \
                                           str(self.ex_lam_high) + cc.reset)     
            elif mode == 'fluxcheck':
                self.ex_lam_high = last_lam
                self.isset_lhigh = True

            retval = self.int_float( last_lam + (float(th) * self.munit) )
            if self.check_lam(retval):
                ss.logger_freshs.info(cc.c_magenta + 'Trying interface: ' + str(retval) + \
                                      cc.reset)
                # deactivate interfaces, if lambda was far off
                #if th > self.auto_max_move_fac * 2.0 / 3.0:
                #    self.deactivate_ex_lambdas()
                return retval
            else:
                ss.logger_freshs.info(cc.c_magenta + 'Arrived in B'  + \
                                      cc.reset)
                return ss.B

        elif th < 0.0:
            ss.logger_freshs.debug(cc.c_cyan + 'Last probability was too low, moving interface to the left (th=' + str(th) + ').' + cc.reset)
            # now we know a lambda, were the flux was too low
            if self.isset_llow:
                if last_lam < self.ex_lam_low and mode == 'fluxcheck':
                    self.ex_lam_low = last_lam       
                ss.logger_freshs.debug(cc.c_cyan + 'Higher bound of lambda is: ' + \
                                       str(self.ex_lam_low) + cc.reset)
            elif mode == 'fluxcheck':
                self.ex_lam_low = last_lam
                self.isset_llow = True
                
            # last probability was too low, move interface to the left. If interface is too close to last one, refine steps
            for finefac in range(1000):
                retval = self.int_float( last_lam + (float(th) * self.munit / (float(finefac) + 1.0) ) )
                if self.check_lam(retval):
                    ss.logger_freshs.info(cc.c_magenta + 'Trying interface: ' + str(retval) + \
                                          cc.reset)
                    # deactivate, if flux was far off
                    #if th < (-self.auto_max_move_fac * 2.0 / 3.0):
                    #    self.deactivate_ex_lambdas()
                    return retval
            ss.logger_freshs.warn(cc.c_red + 'Could not move interface further to the left, '  + \
                                  'placement would have been ' + str(retval) + \
                                  cc.reset)

        else:
            if last_lam == ss.A:
                # Start with a first guess
                return self.int_float( ss.A + self.munit )
            elif len(self.ex_lambdas) == 0:
                ss.logger_freshs.info(cc.c_magenta + 'Starting new placement of interface.'  + \
                                      cc.reset)
                return self.int_float( max(ss.lambdas) + self.munit )
         
            else:
                ss.logger_freshs.debug(cc.c_cyan + 'Returning lambda which is placed around last best interface.' + cc.reset)
                if self.isset_lhigh and self.isset_llow:
                    ss.logger_freshs.debug(cc.c_cyan + 'High and low are set, returning mean.' + cc.reset)
                    return self.int_float( 0.5 * (self.ex_lam_high + self.ex_lam_low))
                elif self.isset_lhigh:
                    ss.logger_freshs.debug(cc.c_cyan + 'Only high flux border is set.' + cc.reset)
                    retval = self.int_float( self.ex_lam_high + self.munit )
                    if self.check_lam(retval):
                        return retval
                    elif retval >= ss.B:
                        ss.logger_freshs.debug(cc.c_cyan + 'Was close to B, returning B.' + cc.reset)
                        return ss.B

                    return self.guess_whatever()

                elif self.isset_llow:
                    ss.logger_freshs.debug(cc.c_cyan + 'Only low flux border is set.' + cc.reset)
                    for finefac in range(100):
                        retval = self.int_float( self.ex_lam_low - ( self.munit / (float(finefac) + 1.0) ) )
                        if self.check_lam(retval):
                            return retval

                    return self.guess_whatever()
                        
                else:
                    ss.logger_freshs.debug(cc.c_cyan + 'No preknowledge of lambda. Placing around last one.' + cc.reset)
                    n_exlam = len(self.ex_lambdas)
                    if n_exlam > 0:
                        last_lam = self.ex_lambdas[n_exlam - 1]
                    not_satisfied = True
                    iter_weight = 1.0
                    while not_satisfied:
                    
                        if self.last_placed == 'high':
                            ss.logger_freshs.debug(cc.c_cyan + 'Last placed was higher. Placing lower one.' + cc.reset)
                            self.last_placed = 'low'
                            for finefac in range(100):
                                retval = self.int_float( last_lam - ( self.munit / (float(finefac) + 1.0) ) )
                                if self.check_lam(retval):
                                    return retval
                        else:
                            self.last_placed = 'high'
                            ss.logger_freshs.debug(cc.c_cyan + 'Last placed was lower. Placing higher one.' + cc.reset)
                            retval = self.int_float( last_lam + self.munit )
                            if self.check_lam(retval):
                                return retval
                            elif retval >= ss.B:
                                ss.logger_freshs.debug(cc.c_cyan + 'Was close to B, returning B.' + cc.reset)
                                return ss.B
                        
                        retval = self.int_float( last_lam + ((random.random()-0.5) * self.munit * iter_weight) )
                        
                        if self.check_lam(retval):
                            return retval
                            
                        iter_weight += self.munit / 100.0
                        
                        if iter_weight >= self.munit * 100.0:
                            ss.logger_freshs.warn(cc.c_red + 'Placing another lambda was impossible. Giving up.'  + \
                                                  cc.reset)

                            return self.guess_whatever()
                

        ss.logger_freshs.info(cc.c_magenta + 'Starting new placement of interface.'  + \
                              cc.reset)
        #self.ex_inter_new += 1
        try:
            return self.int_float( max(ss.lambdas) + random.random() * 3.0 * self.munit )
        except:
            return self.int_float( ss.A + random.random() * 3.0 * self.munit )
        
        
# -------------------------------------------------------------------------------------------------
    def append_histo_lambda(self, lam, lam_id):
        ss = self.server
        ss.logger_freshs.info(cc.c_cyan + 'Adding max_lambda ' + str(lam) + ' to max_lam array.' + cc.reset)
        self.max_lams[lam_id].append(lam)

# -------------------------------------------------------------------------------------------------
# Parse received result
# -------------------------------------------------------------------------------------------------
    def parse_message(self, data, ddata, client, runid):
        ss = self.server

        if "\"omit\": True" in data:
            ss.logger_freshs.info(cc.c_magenta + client.name + ' requested to omit data.' + cc.reset)
            return

        ss.explorer_clients.pop(client)

        if not self.exmode:
            ss.logger_freshs.info(cc.c_green + 'Exploremode is over, starting new job on '+ client.name + cc.reset)
            ss.check_for_job(client)
            return

        if self.auto_histo:
            if self.auto_min_explorer_steps > 0:
                try:
                    if ddata['calcsteps'] < self.auto_min_explorer_steps:
                        ss.logger_freshs.info(cc.c_green + 'Client '+ client.name + ' has not performed enough steps, giving new job.' + cc.reset)
                        ss.check_for_job(client)
                        return
                except Exception as e:
                    ss.logger_freshs.warn(cc.c_red + str(e) + cc.reset)

        if "\"success\": True" in data:
            self.analyze_job_success(client, ddata, runid)

        elif "\"success\": False" in data:
            self.analyze_job_nosuccess(client, ddata, runid)

        else:
            ss.logger_freshs.warn(cc.c_red + 'Omitting data from ' + client.name + \
                                  ' because of invalid conditions.' + cc.reset)
            #ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------
# Analyze job success
# -------------------------------------------------------------------------------------------------

    def analyze_job_success(self, client, ddata, runid):
        ss = self.server
        
        if len(ddata['points']) < 1:
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive an array of configuration sets.' + cc.reset)
        
        ##get and save runtime
        if 'runtime' in ddata:
                runtime = ddata['runtime']
        else:
                runtime = time.time() - ss.client_runtime[str(client)]

        if 'rcval' in ddata:
            rcval = ddata['rcval']
        else:
            rcval = 0.0

        if 'uuid' in ddata:
            uuid = ddata['uuid']
        else:
            uuid = ''

        ##get the RNG seed that was used
        try:
            start_seed = ddata['seed']
        except:
            start_seed = 0
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive seed from client, setting to zero.' + \
                                  cc.reset)
      
        the_jobs_lambda = ddata['act_lambda']

        if self.auto_histo:
            try:
                self.append_histo_lambda(ddata['max_lam'],self.cemlti(the_jobs_lambda))
            except:
                ss.logger_freshs.warn(cc.c_red + client.name + ' maximum lambda information could not be added!' + cc.reset)
                ss.logger_freshs.warn(cc.c_magenta + 'Data was: ' + str(ddata) + ', job_lambda ' + str(the_jobs_lambda) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'max_lam: '+str(ddata['max_lam']) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'histo state: '+str(self.max_lams) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'histo index: '+str(self.cemlti(the_jobs_lambda)) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'Exception was: ' + str(e) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + client.name + ' Sending QUIT to client!' + cc.reset)
                client.send_quit()

        if the_jobs_lambda >= self.loffset:
            ex_lam = self.cemlti(the_jobs_lambda)
            self.ex_ctime[ex_lam] += ddata['ctime']
            self.ex_success[ex_lam] += 1
            self.ex_returned[ex_lam] += 1
            if ss.act_lambda > 0 and ss.use_ghosts and not self.auto_histo:
                try:
                    self.ex_ghost_cand.append([ the_jobs_lambda, ddata['points'], ddata['origin_points'], ddata['calcsteps'], \
                                                ddata['ctime'], runtime, 0, runid, start_seed, rcval, uuid ])
                except:
                    ss.logger_freshs.warn(cc.c_red + 'Not enough information to add successful explorer to ghost array' + \
                                          cc.reset)

            self.check_returned_explorers(ex_lam, the_jobs_lambda, client)

       
        ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------
# Analyze job nosuccess
# -------------------------------------------------------------------------------------------------

    def analyze_job_nosuccess(self, client, ddata, runid):
        ss = self.server
        # client has aborted run (e.g. max_steps reached)
        the_jobs_lambda = ddata['act_lambda']

        if 'rcval' in ddata:
            rcval = ddata['rcval']
        else:
            rcval = 0.0

        if 'uuid' in ddata:
            uuid = ddata['uuid']
        else:
            uuid = ''

        ##get and save runtime
        if 'runtime' in ddata:
                runtime = ddata['runtime']
        else:
                runtime = time.time() - ss.client_runtime[str(client)]
        
        if self.auto_histo:
            try:
                self.append_histo_lambda(ddata['max_lam'],self.cemlti(the_jobs_lambda))
            except Exception as e:
                ss.logger_freshs.warn(cc.c_red + client.name + ' maximum lambda information could not be added.' + cc.reset)
                ss.logger_freshs.warn(cc.c_magenta + 'Data was: ' + str(ddata) + ', job_lambda ' + str(the_jobs_lambda) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'max_lam: '+str(ddata['max_lam']) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'histo index: '+str(self.cemlti(the_jobs_lambda)) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'histo state: '+str(self.max_lams) + cc.reset)
                ss.logger_freshs.warn(cc.c_red + 'Exception was: ' + str(e) + cc.reset)
                client.send_quit()
                
        if the_jobs_lambda >= self.loffset:
            ex_lam = self.cemlti(the_jobs_lambda)
            self.ex_returned[ex_lam] += 1
            if ss.act_lambda > 0 and ss.use_ghosts and not self.auto_histo:
                try:
                    self.ex_ghost_cand.append( [ the_jobs_lambda, '', ddata['origin_points'], ddata['calcsteps'], \
                                                 0.0, runtime, 0, 0, 0, rcval, uuid ] )
                except:
                    ss.logger_freshs.warn(cc.c_red + 'Not enough information to add nonsuccesful explorer to ghost array' + \
                                          cc.reset)

            self.check_returned_explorers(ex_lam, the_jobs_lambda,client)
                        
        ss.check_for_job(client)










       

