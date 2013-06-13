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
import modules.concolors as cc
import ConfigParser

import math
import random

#import server

# -------------------------------------------------------------------------------------------------

#### FFS-SPECIFIC SERVER CLASS ####
class ffs_sampling_control():
  
  
    ##init, saving a backpointer to the parent "server" class which handles comms.
    def __init__(self, server):
        self.server = server
        
        self.read_config()

        # switch between real runs and exploring clients
        self.exmode = False             # exploring mode for interface placement
        # This is where the act_lam id starts. Should be larger than number of possible interfaces.
        # TODO: warn/err, if num_interfaces >= 1337       
        self.loffset = 1337
        # unique act_lam id for explorers
        self.ex_act_lambda = self.loffset
        
        self.lamconf = ConfigParser.RawConfigParser()
        
        self.escape_clients = {}

        # counter for different origin points
        self.dorigins = 0
        self.dorigins_last = 0
        self.dorigins_count = 0
        
        # dict for counting the escape skip per client
        self.escape_skip_count = {}
       
# -------------------------------------------------------------------------------------------------

    def read_config(self):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': read_config' + cc.reset)
        
        # not implemented yet
        #self.reverse_direction = self.server.configfile.getint('ffs_control', 'reverse_direction')

        if ss.configfile.has_option('ffs_control', 'require_runs'):
            self.require_runs = ss.configfile.getint('ffs_control', 'require_runs')
        else:
            self.require_runs = 1
        if ss.configfile.has_option('ffs_control', 'min_success'):
            self.min_success = ss.configfile.getint('ffs_control', 'min_success')
        else:
            self.min_success = 2
        if ss.configfile.has_option('ffs_control', 'parallel_escape'):
            self.parallel_escape = ss.configfile.getint('ffs_control', 'parallel_escape')
        else:
            self.parallel_escape = 0
        if ss.configfile.has_option('ffs_control', 'escape_steps'):
            self.escape_steps = ss.configfile.getint('ffs_control', 'escape_steps')
        else:
            self.escape_steps = 1000
        if ss.configfile.has_option('ffs_control', 'escape_skip'):
            self.escape_skip = ss.configfile.getint('ffs_control', 'escape_skip')
        else:
            self.escape_skip = 0
        if ss.configfile.has_option('ffs_control', 'max_ghosts_between'):
            self.max_ghosts_between = ss.configfile.getint('ffs_control', 'max_ghosts_between')
        else:
            self.max_ghosts_between = 3
        if ss.configfile.has_option('ffs_control', 'min_origin'):
            self.min_origin = ss.configfile.getint('ffs_control', 'min_origin')
        else:
            self.min_origin = 3
        if ss.configfile.has_option('ffs_control', 'min_origin_decay'):
            self.min_origin_decay = ss.configfile.getfloat('ffs_control', 'min_origin_decay')
            if self.min_origin_decay > 1.0:
                ss.logger_freshs.warn(cc.c_red + 'min_origin_decay is too high, cannot get more different traces than points requested! Setting to 0.3' + cc.reset)
                self.min_origin_decay = 0.3
        else:
            self.min_origin_decay = 0.3
        if ss.configfile.has_option('ffs_control', 'min_origin_increase_count'):
            self.min_origin_increase_count = ss.configfile.getint('ffs_control', 'min_origin_increase_count')
        else:
            self.min_origin_increase_count = 3


# -------------------------------------------------------------------------------------------------

    def load_from_db(self):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': load_from_db' + cc.reset)
        
        ss.act_lambda = ss.storepoints.biggest_lambda()

        if ss.auto_interfaces:
            ss.M_0_runs.append(ss.ai.auto_runs)
            try:
                # TODO: make this a config option?
                loadfromdb = True
                # read lamconf resume file anyway (because of ghosttimesave)
                self.lamconf.read(ss.lamfile)
                
                if loadfromdb:
                    # load lambdas from DB
                    tmp_lamlist = ss.storepoints.return_lamlist()
                    ilam = len(tmp_lamlist)
                    ss.lambdas = tmp_lamlist[:]
                    for i in range(ilam):
                        ss.M_0_runs.append(ss.ai.auto_runs)
                    ss.logger_freshs.info(cc.c_magenta + 'Read ' + str(ilam-1) + ' lambdas from DB' + cc.reset)
                else:
                    # load lambdas from resume config file
                    lambdaload = True
                    ilam = 1
                    while lambdaload:
                        try:
                            ss.lambdas.append(self.lamconf.getfloat('hypersurfaces', 'lambda'+str(ilam)))
                            ss.M_0_runs.append(ss.ai.auto_runs)
                            ilam += 1
                        except:
                            lambdaload = False

                    if self.lamconf.has_option('hypersurfaces', 'borderB'):
                        ss.lambdas.append(ss.B)
                        ss.M_0_runs.append(ss.ai.auto_runs)
                        ilam += 1

                    ss.logger_freshs.info(cc.c_magenta + 'Read ' + str(ilam-1) + ' lambdas from file ' + ss.lamfile + cc.reset)

                ss.logger_freshs.info(cc.c_magenta + 'Lambdas are now ' + str(ss.lambdas) + cc.reset)

                if ss.act_lambda != ilam-1 and ss.act_lambda != ilam-2:
                    ss.logger_freshs.error(cc.c_red + cc.bold + 'Number of interfaces in DB does not fit lambdas in resume load. ' + cc.reset)
                    ss.logger_freshs.error(cc.c_red + cc.bold + 'There are ' + str(ss.act_lambda+1) + ' interfaces but ' + \
                                           str(ilam) + ' lambdas loaded' + cc.reset)
                    raise SystemExit

                if ss.use_ghosts and ss.act_lambda > 0:
                    try:
                        ss.ghosttimesave = self.lamconf.getfloat('Resume_info', 'ghosttimesave')
                        ss.ghostcalcsave = self.lamconf.getfloat('Resume_info', 'ghostcalcsave')
                    except:
                        ss.logger_freshs.info(cc.c_magenta + 'No ghost time loaded from ' + ss.lamfile + cc.reset)
            except:
                ss.logger_freshs.error(cc.c_red + cc.bold + 'Could not read lambdas from file '+ ss.lamfile + cc.reset)
                raise SystemExit
        else:
            ss.fill_lambdas()
 
        if ss.act_lambda == 0:
            # read in ctime and successful runs
            ss.ctime = ss.storepoints.return_ctime()
            ncurrent_points = ss.storepoints.return_nop(ss.act_lambda)
            ss.M_0.append(ss.storepoints.return_runcount(ss.act_lambda))
            ss.run_count.append(ncurrent_points)
            if ncurrent_points >= ss.M_0_runs[ss.act_lambda]:
                ss.k_AB_part1 = ncurrent_points / ss.ctime
                ss.logger_freshs.info(cc.c_magenta + 'k_AB_part1 = ' + str(ss.k_AB_part1) + cc.reset)
                # Change interface
                self.change_interface()
                # Escape flux is finished, go to stage 2
        else:
            n_points_first = ss.storepoints.return_nop(0)
            ss.ctime = ss.storepoints.return_ctime()
            try:
                ss.k_AB_part1 = n_points_first / ss.ctime
            except:
                ss.logger_freshs.warn(cc.c_red + 'k_AB_part1 could not be calculated, setting to 1.0' + cc.reset)
                ss.k_AB_part1 = 1.0

            ss.logger_freshs.info(cc.c_magenta + 'k_AB_part1 = ' + str(ss.k_AB_part1) + cc.reset)
                
            for lmbd_tmp in range(ss.act_lambda+1):
                ss.M_0.append(ss.storepoints.return_runcount(lmbd_tmp))
                ss.run_count.append(ss.storepoints.return_nop(lmbd_tmp))
           
            ss.M_0_runs = ss.run_count[:]
            if ss.auto_interfaces:
                if ss.M_0_runs[-1] < ss.ai.auto_runs:
                    ss.M_0_runs[-1] = ss.ai.auto_runs

            ss.logger_freshs.debug(cc.c_magenta + 'Runcount: ' + str(ss.run_count) + cc.reset)
            ss.logger_freshs.debug(cc.c_magenta + 'M_0: ' + str(ss.M_0) + cc.reset)
            ss.logger_freshs.debug(cc.c_magenta + 'M_0_runs: ' + str(ss.M_0_runs) + cc.reset)
            ss.logger_freshs.debug(cc.c_magenta + 'lambdas: ' + str(ss.lambdas) + cc.reset)

            # check if calculation is ready
            if (ss.lambdas[ss.act_lambda] >= ss.B) and (ss.storepoints.return_nop(ss.act_lambda) >= ss.M_0_runs[ss.act_lambda]):
                ss.end_simulation()
            
            #self.interface_statistics_ok()
            if ss.storepoints.return_nop(ss.act_lambda) >= ss.M_0_runs[ss.act_lambda]:
                self.change_interface()
            ss.logger_freshs.info(cc.c_green + 'Current interface index: ' + str(ss.act_lambda) + cc.reset)

# -------------------------------------------------------------------------------------------------

    def launch_jobs(self):
        ss=self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': launch_jobs' + cc.reset)
        
        ## Set initial parameters
        ss.M_0_runs = []
        ss.lambdas = [ss.A]
        ss.run_count = []
        ss.M_0 = []

        ss.act_lambda = 0             # current working interface
        ss.ctime = 0.0                # calculation time for escape interface
        ss.k_AB_part1 = 0.0           # first part of the rate constant

        ss.ghosttimesave = 0.0        # time saved by the use of ghosts
        ss.ghostcalcsave = 0          # calculation steps saved by the use of ghosts 

               
        if ss.auto_interfaces and not ss.dbload:
            ss.logger_freshs.info(cc.c_green + 'Using automatic interface placement as requested.' + cc.reset)
            ss.run_count.append(0)
            ss.M_0.append(0)
            if len(ss.lambdas) > 0:
                ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderA'))
            else:
                ss.M_0_runs.append(int( max([1.5*self.get_min_success(),ss.ai.auto_runs])) )
            # Check if next lambda exists, if not, guess one
            if(ss.act_lambda >= len(ss.lambdas)):
                ss.ai.exmode_on()

        elif ss.dbload:
            self.load_from_db()          
        else:
            ss.run_count.append(0)
            ss.M_0.append(0)
            # fill lambda array
            ss.fill_lambdas()
            # fill M_0_runs array with desired number of runs
            ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderA'))
            for act_entry in range(1,ss.noi):
                ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'lambda' + str(act_entry)))
            ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderB'))
            
            ss.logger_freshs.info(cc.c_green + 'Interfaces read from file: ' + \
                                  str(ss.lambdas) + \
                                  cc.reset)


# -------------------------------------------------------------------------------------------------

    # Write to config file
    def append_to_lamconf(self,section, option, value):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': append_to_lamconf' + cc.reset)
        
        try:
            self.lamconf.read(ss.lamfile)
        except:
            ss.logger_freshs.info(cc.c_magenta + 'No lambda config file yet, will create one.' + cc.reset)

        if not self.lamconf.has_section(section):
            self.lamconf.add_section(section)
            
        self.lamconf.set(section, option, value)
        
        fc = open(ss.lamfile,'w')
        self.lamconf.write(fc)
        fc.close()
        
# -------------------------------------------------------------------------------------------------

    # Change the interface to the next one
    def change_interface(self):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': change_interface' + cc.reset)

        ss.storepoints.commit()
        ss.ghostpoints.commit()
        self.print_lambar('AB')
        ss.M_0.append(0)
        ss.run_count.append(0)
        ss.act_lambda += 1
        if ss.ai.auto_interfaces:
            if ss.lambdas[-1] >= ss.B:
                ss.M_0_runs.append(ss.configfile.getint('runs_per_interface', 'borderB'))
            else:
                ss.M_0_runs.append(int( max([1.5*self.get_min_success(),ss.ai.auto_runs])) )
            # Check if next lambda exists, if not, guess one
            if ss.act_lambda >= len(ss.lambdas) and not ss.lambdas[-1] >= ss.B:
                ss.ai.exmode_on()

# -------------------------------------------------------------------------------------------------

    # get candidates and leftover steps from escape interface
    def escape_point_candidates(self):
        ss = self.server

        cand_pts = []
        max_steps_pts = []

        # get list of escape point rp_ids
        esc_pts_ids = ss.storepoints.return_configpoints_ids(0)
        #ss.logger_freshs.debug(cc.c_magenta + "Candidate points for escape resume: " + str(esc_pts_ids) + cc.reset)
        for cl in self.escape_clients:
            # remove points, on which we calculate already
            if self.escape_clients[cl] in esc_pts_ids:
                #ss.logger_freshs.debug(cc.c_magenta + "Point " + self.escape_clients[cl] + " is calculated at the moment. Removing." + cc.reset)
                esc_pts_ids.remove(self.escape_clients[cl])
        for pt in esc_pts_ids[::-1]:
            # remove points which are origins from other points
            if ss.storepoints.id_in_origin(pt):
                #ss.logger_freshs.debug(cc.c_magenta + "Point " + pt + " is origin of another point, found existing trace! Removing." + cc.reset)
                esc_pts_ids.remove(pt)

        if len(esc_pts_ids) > 0:
            # now we have a list of last points, do traceback
            for pt in esc_pts_ids:
                steps_until_point = ss.storepoints.traceback_escape_point(pt)
                # if steps are left to calculate
                if steps_until_point < self.escape_steps:
                    cand_pts.append(pt)
                    max_steps_pts.append(steps_until_point)

        ss.logger_freshs.debug(cc.c_magenta + "Found " + str(cand_pts) + " with " + str(max_steps_pts) + " steps in total up to the particular point." + cc.reset)
        return cand_pts, max_steps_pts

# -------------------------------------------------------------------------------------------------

    def check_run_required(self,ilam):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': check_run_required' + cc.reset)

        if self.require_runs:
            ncheck = ss.storepoints.return_nop(ilam)
        else:
            ncheck = ss.run_count[ilam] - ss.active_clients() + 1

        ss.logger_freshs.debug(cc.c_magenta + 'run_count: ' + str(ss.run_count) + cc.reset)
        ss.logger_freshs.debug(cc.c_magenta + 'M_0_runs: ' + str(ss.M_0_runs) + cc.reset)
        ss.logger_freshs.debug(cc.c_magenta + 'lambda: ' + str(ilam) + cc.reset)

        # number of escape clients running
        
        nescape = len(self.escape_clients)

        if ilam == 0 and self.parallel_escape == 0:
            if nescape > 0:
                return False

        if ss.run_count[ilam] < ss.M_0_runs[ilam] and ncheck < ss.M_0_runs[ilam]:
            self.print_lambar('inter',ncheck,ss.M_0_runs[ilam])
            return True

        if ilam == 0 and self.parallel_escape == 1:
            if len(self.escape_point_candidates()[0]) - nescape > 0:
                ss.logger_freshs.debug(cc.c_magenta + 'At least one escape trace still needs calculation steps.' + cc.reset)
                return True
 #           elif ncheck >= ss.M_0_runs[ilam] and len(self.escape_point_candidates()[0]) > 0:
                # calculation steps are left over on first interface

#                return True
  
        if ncheck >= ss.M_0_runs[ilam]:
            # This interface is ready, switch to the next one
            # Make sure that we have not reached B yet
            
            ncurrent_points = ss.storepoints.return_nop(ilam)
            if ncurrent_points < self.min_success:
                ss.logger_freshs.warn(cc.c_red + 'Number of points collected is too low, increasing number of trials!' + cc.reset)
                ss.M_0_runs[ilam] += 1
                # check again
                return self.check_run_required(ilam)
                    
            if ss.lambdas[ilam] < ss.B:

                if ilam == 0:
                    ss.k_AB_part1 = ncurrent_points / ss.ctime
                    ss.logger_freshs.info(cc.c_magenta + 'k_AB_part1 = ' + str(ss.k_AB_part1) + cc.reset)

                if self.interface_statistics_ok():
                    # Everything seems to be alright, change interface
                    self.change_interface()
                else:
                    ss.logger_freshs.info(cc.c_green + 'All traces originate from less than ' + str(self.get_min_success()) + ' points, increasing number of trials!' + cc.reset)
                    if ss.auto_interfaces:
                        min_req = int( 1.5*(self.get_min_success() - self.dorigins) )
                        if min_req > ss.ai.auto_trials:
                            ss.M_0_runs[ilam] += min_req
                        else:
                            ss.M_0_runs[ilam] += ss.ai.auto_trials
                    else:
                        ss.M_0_runs[ilam] += int(ss.configfile.getint('runs_per_interface', 'lambda' + str(ss.act_lambda)) / 2.0 + 1)
                    # check again
                    return self.check_run_required(ilam)
                
                ss.logger_freshs.info(cc.c_magenta + cc.bold + 'Last interface was ' + \
                                      str(ss.act_lambda-1) + ', now calculating on interface ' + \
                                      str(ss.act_lambda) + cc.reset)
                
                # start all clients on new interface
                #for cur_client in ss.clients:
                #    ss.check_for_job(cur_client)

                # Alternative: Start only this client and idle clients on new 
                # interface, let ghost jobs run (-> less load on interface change, could 
                # crash or slow down server if too many clients)

                ss.start_idle_clients()

            else:
                # Arrived in B
                ss.end_simulation()

        return False

# -------------------------------------------------------------------------------------------------

    def start_job(self, client):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': start_job' + cc.reset)
        
        lamtmp = ss.act_lambda
        if lamtmp == 0 and len(ss.lambdas) > 0:
            if self.check_run_required(lamtmp):
                client.start_job1()
                return True
        elif lamtmp >= 1 and len(ss.lambdas) > lamtmp:
            if ss.lambdas[lamtmp] <= ss.B and self.check_run_required(lamtmp):
                client.start_job2()
                return True

        # interface could have changed! Recursion.
        if lamtmp < ss.act_lambda:
            return self.start_job(client)

        return False

# -------------------------------------------------------------------------------------------------

    def get_min_success(self):
        ss = self.server
        if self.min_origin > 0:
            origins = int(round(ss.M_0_runs[0] * pow(self.min_origin_decay,ss.act_lambda)))
            if origins < self.min_origin:
                return self.min_origin
            else:
                return origins
        else:
            return 0


# -------------------------------------------------------------------------------------------------

    def interface_statistics_ok(self):
        ss = self.server
        if ss.act_lambda == 0:
            return True
        else:
            if self.min_origin > 1 and self.dorigins_count < self.min_origin_increase_count:
                self.dorigins = len(ss.storepoints.interface_statistics_backtrace(ss.act_lambda))
                if self.dorigins == self.dorigins_last:
                    self.dorigins_count += 1
                else:
                    self.dorigins_count = 0
                    self.dorigins_last = self.dorigins
                if self.dorigins < self.get_min_success():
                    ss.logger_freshs.debug(cc.c_magenta + 'Number of origin points is ' + str(self.dorigins) + '.' + cc.reset)
                    return False
                else:
                    return True
            elif self.dorigins_count >= 2:
                self.dorigins_count = 0
                ss.logger_freshs.warn(cc.c_red + 'Could not reach desired increase of origin trajectories after 3 loops, continuing.' + cc.reset)
                return True
            else:
                return True


# -------------------------------------------------------------------------------------------------

    def print_lambar(self,mode='none',ndone=1,ndesired=1):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': print_lambar' + cc.reset)
        
        subdiv = 50
        percent = ''
        
        if mode == 'AB':
            scale = ss.B / float(subdiv)
            margin = int(ss.lambdas[ss.act_lambda] / scale)
            
        else:
            scale = float(ndesired) / float(subdiv)
            margin = int(float(ndone) / scale)

            if ss.act_lambda == 0:
                il = 'A'
            else:
                il = str(ss.act_lambda - 1)
            if len(ss.lambdas) > 0:
                if ss.lambdas[ss.act_lambda] == ss.B:
                    ir = 'B'
                else:
                    ir = str(ss.act_lambda)
            else:
                ir = str(ss.act_lambda)
            
        for i in range(subdiv):
            if(i < margin):
                percent += '='
            elif i == margin:
                percent += '>'
            else:
                percent += ' '

        if mode == 'AB':
            ss.logger_freshs.info(cc.c_magenta + cc.bold + '[A|' + percent + '|B]' + cc.reset)
        else:
            ss.logger_freshs.info(cc.c_green + cc.bold + '[' + il + '|' + percent + \
                                  '|' + ir + '] (' + str(ndone) + '/' + str(ndesired) + ')' + \
                                  cc.reset)


# -------------------------------------------------------------------------------------------------
# Parse received result
# -------------------------------------------------------------------------------------------------
    def parse_message(self, data, ddata, client, runid):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': parse_message' + cc.reset)

        if "\"success\": True" in data:
            ss.logger_freshs.debug(cc.c_blue + client.name + ' was successful.' + cc.reset)
            self.analyze_job_success(client, ddata, runid)

        elif "\"success\": False" in data:
            ss.logger_freshs.debug(cc.c_blue + client.name + ' was not successful.' + cc.reset)
            self.analyze_job_nosuccess(client, ddata, runid)

        elif "\"omit\": True" in data:
            ss.logger_freshs.info(cc.c_magenta + client.name + ' requested to omit data.' + cc.reset)


# -------------------------------------------------------------------------------------------------
# Analyze job success
# -------------------------------------------------------------------------------------------------

    def analyze_job_success(self, client, ddata, runid):
        ss = self.server
        
        # clients are allowed to request no new job, because they are still calculating and delivering
        # points, e.g. on the first interface
        newjob = True
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': analyze_job_success' + cc.reset)
        
        deactivated = 0
        
        if len(ddata['points']) < 1:
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive a configuration set from client.' + cc.reset)

        the_jobs_lambda = ddata['act_lambda']
        
        client.remove_from_escape()
        
        if the_jobs_lambda == 0:

            if self.escape_skip > 1:
                if client in self.escape_skip_count:
                    self.escape_skip_count[client] += 1
                else:
                    self.escape_skip_count[client] = self.escape_skip
                
                if not (self.escape_skip_count[client] % self.escape_skip) == 0:
                    ss.logger_freshs.info(cc.c_green + 'Storing point as DEACTIVATED point because of escape skip.' + cc.reset)
                    deactivated = 1
        
        # get and save runtime
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

        if 'customdata' in ddata:
            customdata = ddata['customdata']
        else:
            customdata = ''

        # get the RNG seed that was used
        try:
            start_seed = ddata['seed']
        except:
            start_seed = 0
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive seed from client, setting to zero.' + \
                                  cc.reset)

        try:
            origin_point = ddata['origin_points']
        except:
            origin_point = 'escape'


        if 'no_new_job' in ddata:
            if ddata['no_new_job'] == True:
                ss.logger_freshs.debug(cc.c_magenta + 'Client requested not to bother him with a new job.' + \
                                  cc.reset)
                newjob = False

        ctime = ddata['ctime']

        # only use point, if lambda is alright, but save all escape jobs
        if the_jobs_lambda == ss.act_lambda or the_jobs_lambda == 0:
                    
            ss.logger_freshs.debug(cc.c_green + 'Run on ' + client.name + \
                                       ' succeeded.' + cc.reset)
                        #ss.logger_freshs.debug(cc.c_green + 'Saving point with ' + cc.bold + 'lambda ' + \
                        #                      str(the_jobs_lambda) + ' (' + str(cur_nop + 1) + '/'+ \
                        #                      str(ss.M_0_runs[ss.act_lambda]) + ')' + \
                        #                      cc.reset)

            if the_jobs_lambda == 0:
               ss.ctime += ctime
               ss.logger_freshs.debug(cc.c_magenta + 'Added ctime ' + str(ctime) + ', overall ctime is now ' + \
                                          str(ss.ctime) + cc.reset)

            ss.storepoints.add_point(the_jobs_lambda, \
                                         ddata['points'], \
                                         origin_point, \
                                         ddata['calcsteps'], \
                                         ctime, \
                                         runtime, \
                                         ss.M_0[the_jobs_lambda], \
                                         runid, \
                                         start_seed, \
                                         rcval, \
                                         ss.lambdas[the_jobs_lambda], \
                                         0, \
                                         deactivated, \
                                         uuid, \
                                         customdata \
                                         )

            ss.storepoints.update_usecount_by_myid(origin_point)

        else:
            ss.logger_freshs.warn(cc.c_red + 'Not using point of ' + client.name + ' because of wrong lambda (' + \
                                      str(the_jobs_lambda) + ') instead of (' + str(ss.act_lambda) + ')' + cc.reset)

            ss.logger_freshs.debug(cc.c_magenta + 'Data was ' + str(ddata) + cc.reset)

                # Server is assuming, that client calculates on current interface. Decrease runcount
            client.decr_runcount(ss.act_lambda)


        if newjob:
            ss.check_for_job(client)
        
        if ss.act_lambda == 0:
            ss.start_idle_clients()




# -------------------------------------------------------------------------------------------------
# Analyze job nosuccess
# -------------------------------------------------------------------------------------------------

    def analyze_job_nosuccess(self, client, ddata, runid):
        ss = self.server

        newjob = True

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': analyze_job_nosuccess' + cc.reset)

        if 'runtime' in ddata:
            runtime = ddata['runtime']
        else:
            runtime = time.time() - ss.client_runtime[str(client)]
            
        if 'calcsteps' in ddata:
            calcsteps = ddata['calcsteps']
        else:
            calcsteps = 0

        try:
            origin_point = ddata['origin_points']
        except:
            origin_point = 'escape'

        the_jobs_lambda = ddata['act_lambda']
 
        if 'no_new_job' in ddata:
           if ddata['no_new_job'] == True:
                ss.logger_freshs.debug(cc.c_magenta + 'Client requested not to bother him with a new job.' + \
                                  cc.reset)
                newjob = False
        
        client.remove_from_escape()
        
        if the_jobs_lambda == ss.act_lambda or the_jobs_lambda == 0:
            
            # if client has no success on first interface
            # (this should only happen, if max_steps is set)
            if the_jobs_lambda == 0:
                ctime = ddata['ctime']
                
                # count ctime in parallel run.
                if self.parallel_escape == 1:
                    ss.ctime += ctime
                    # write leftover steps to DB
                    if origin_point == 'escape':
                        ss.logger_freshs.warn(cc.c_red + 'Tried to add ctime ' + str(ctime) + ' to escape point with ID = escape. This is ambiguous and cannot be done. ' + \
                                              'Please use more escape_steps to have at least 2 points in an escape trajectory!' + cc.reset)
                    else:
                        ss.storepoints.add_ctime_steps(origin_point, ctime, calcsteps)
                    # add it to the server variable
                        ss.logger_freshs.debug(cc.c_magenta + 'Added ctime ' + str(ctime) + ' to last escape point. Server ctime is now ' + \
                                           str(ss.ctime) + cc.reset)
            
            ss.logger_freshs.debug(cc.c_green + \
                                   'Run was not successful, not incrementing counter.' + \
                                   cc.reset)
            if 'origin_points' in ddata:
                ss.storepoints.update_usecount_by_myid(ddata['origin_points'])
            else:
                ss.logger_freshs.warn(cc.c_red + 'No origin point in data of ' + client.name + \
                                        ', not incrementing use-count' + cc.reset)
                  
            # we need one more run because this one was not successful if we are not in require_runs mode
            if self.require_runs:
                client.decr_runcount(the_jobs_lambda)
        else:
            ss.logger_freshs.warn(cc.c_red + 'Not using info of ' + client.name + ' because of wrong lambda (' + \
                                  str(the_jobs_lambda) + ') instead of (' + str(ss.act_lambda) + ')' + cc.reset)

            ss.logger_freshs.debug(cc.c_magenta + 'Data was ' + str(ddata) + cc.reset)

            # Server is assuming, that client calculates on current interface.
            client.decr_runcount(ss.act_lambda)

        if newjob:
            ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------
# Arrived in B: calculate final rate and do a little bit of analysis
# -------------------------------------------------------------------------------------------------
    def arrived_in_B(self):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': arrived_in_B' + cc.reset)
        
        # commit data in database
        ss.storepoints.commit()
        ss.ghostpoints.commit()

        # get values from database
        lambda_max = ss.storepoints.biggest_lambda()
        sum_calcsteps = ss.storepoints.return_sum_calcsteps()
        ctime_db = ss.storepoints.return_ctime()
        
        if abs(ctime_db - ss.ctime) > 1e-5:
            ss.logger_freshs.warn(cc.c_red + 'Calculation time from server (' + str(ss.ctime) + \
            ') and from DB (' + str(ctime_db) + ') differ!' + cc.reset)
        
        # Probability list
        probi = [ss.k_AB_part1]
        interpoints = [ss.storepoints.return_nop(0)]
        
        for i_ind in range(1,lambda_max+1):
            interpoints.append(ss.storepoints.return_nop(i_ind))
            probi.append(float(interpoints[i_ind])/float(ss.M_0[i_ind]))
        
        rel_variance = 0.0
        
        for i_ind in range(len(ss.lambdas)):
            qi = 1.0 - probi[i_ind]
            ki = float(ss.M_0[i_ind]) / float(interpoints[0])
            rel_variance += (qi / (probi[i_ind]) * ki)

        efficiency = 1.0 / (sum_calcsteps * rel_variance)

        k_AB_part2 = 0.0
        k_AB_i = []

        # Calculate rate
        for c_ind in range(1,lambda_max+1):
            P_i = math.log(float(interpoints[c_ind])/float(ss.M_0[c_ind]))
            k_AB_i.append(P_i)
            k_AB_part2 += P_i
        the_rate = ss.k_AB_part1 * math.exp(k_AB_part2)
        ss.logger_freshs.info(cc.c_red + '# k_AB')
        ss.logger_freshs.info(str(the_rate) + cc.reset)

        # Calculate flux function
        denum = math.log(ss.k_AB_part1) + k_AB_part2
        interf=[]
        pj = [math.log(ss.k_AB_part1)]
        pj += k_AB_i
        for k_ind in range(lambda_max+1):
            num = 0.0
            for j_ind in range(k_ind):
                num += pj[j_ind]
            interf.append(num/denum)
        
        # Write calculations to outfile
        h_f = open(ss.outfile,'w')
        h_f.write('# Transition rate from A to B: %.4e\n' % the_rate)
        h_f.write('# Simulation time on lambda_0: %f\n' % ss.ctime)
        h_f.write('# Calculation steps performed: %d\n' % sum_calcsteps)
        h_f.write('# Relative variance of rate  : %f\n' % rel_variance)
        h_f.write('# Computational efficiency   : %.4e\n' % efficiency)
        if ss.use_ghosts:
            h_f.write('# Time saved using ghosts    : %fs\n' % ss.ghosttimesave )
            h_f.write('# Calcsteps saved with ghosts: %d\n' % ss.ghostcalcsave )
        h_f.write('#\n')
        h_f.write('# Interface information in detail:\n')
        h_f.write('# i lambda points trials P_i f i/n\n')

        for i_ind in range(lambda_max+1):
            idn = float(i_ind)/float(lambda_max)
            h_f.write('%d %f %d %d %f %f %f\n' % \
                     (i_ind, ss.lambdas[i_ind], interpoints[i_ind], ss.M_0[i_ind], probi[i_ind], interf[i_ind], idn))
                     
        ss.logger_freshs.info(cc.c_magenta + 'Simulation details have been written to output file ' + \
                              str(ss.outfile) + cc.reset)

        h_f.close()
        
       
        self.print_lambar('AB')       





