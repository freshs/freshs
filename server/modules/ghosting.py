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
import time


class ghosting():
    def __init__(self, server):
        self.server = server
        # mean of calcsteps when the first time is asked for ghosts per interface
        self.mean_of_calcsteps = {}

# -------------------------------------------------------------------------------------------------
    def ghost_possible(self):
        ss = self.server
        
        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': testing ghost_possible' + cc.reset)
        
        # Check if next lambda exists.
        if len(ss.lambdas) >= ss.act_lambda + 2:
            if ss.use_ghosts:
                # Check if number of ghosts is limited in config file
                if ss.max_ghosts > 0 and len(ss.ghost_clients) >= ss.max_ghosts:
                    ss.logger_freshs.debug(cc.c_magenta + 'Maximum number of simultaneous ghost runs reached. Not starting more.' + cc.reset)
                    return False
                
                # check if ghosting would slow down server
                if ss.auto_ghosts > 0:
                    if not self.mean_of_calcsteps.has_key(ss.act_lambda):
                        ss.logger_freshs.debug(cc.c_magenta + 'Obtaining mean_of_calcsteps from database.' + cc.reset)
                        ms = ss.storepoints.return_mean_steps(ss.act_lambda)
                        self.mean_of_calcsteps[ss.act_lambda] = ms

                    if self.mean_of_calcsteps[ss.act_lambda] < ss.auto_ghosts:
                        ss.logger_freshs.debug(cc.c_magenta + 'Not starting ghost run because according to auto_ghosts the runs are too short.' + cc.reset)
                        return False
                
                # Check if starting configurations exist (should, if this function is called...),
                # check if not on last interface
                if (ss.storepoints.return_nop(ss.act_lambda) > 0) and (ss.lambdas[ss.act_lambda] < ss.B):
                    return True
        else:
            if ss.auto_interfaces:
                if len(ss.lambdas) == 0:
                    # turn exploration mode on
                    ss.ai.exmode_on()
                else:
                    if ss.lambdas[-1] < ss.B:
                        ss.ai.exmode_on()
            return False
            
        return False

# -------------------------------------------------------------------------------------------------
# Parse received result
# -------------------------------------------------------------------------------------------------
    def parse_message(self, data, ddata, client, runid):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': parse_message' + cc.reset)

        if "\"omit\": True" in data:
            ss.logger_freshs.info(cc.c_magenta + client.name + ' requested to omit data.' + cc.reset)
            return

        ss.ghost_clients.pop(client)
        ss.ghostnames.remove(client.name)

        if "\"success\": True" in data:
            self.analyze_job_success(client, ddata, runid)

        elif "\"success\": False" in data:
            self.analyze_job_nosuccess(client, ddata, runid)


# -------------------------------------------------------------------------------------------------
# Analyze job success
# -------------------------------------------------------------------------------------------------

    def analyze_job_success(self, client, ddata, runid):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': analyze_job_success' + cc.reset)
        
        if len(ddata['points']) < 1:
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive a configuration set from client.' + cc.reset)
        
        ##get and save runtime
        if 'runtime' in ddata:
                runtime = ddata['runtime']
        else:
                runtime = time.time() - ss.client_runtime[str(client)]

        ##get the RNG seed that was used
        try:
            start_seed = ddata['seed']
        except:
            start_seed = 0
            ss.logger_freshs.warn(cc.c_red + 'Warning: Did not receive seed from client, setting to zero.' + \
                                  cc.reset)

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

        try:
            origin_point = ddata['origin_points']
        except:
            origin_point = ['escape']

        the_jobs_lambda = ddata['act_lambda']
        
        if the_jobs_lambda >= ss.act_lambda + 1:
            
            ss.logger_freshs.info(cc.c_magenta + 'Ghost run on ' + client.name + \
                                  ' succeeded.' + cc.reset)
                
            ss.ghostpoints.add_point(the_jobs_lambda, \
                                     ddata['points'], \
                                     origin_point, \
                                     ddata['calcsteps'], \
                                     ddata['ctime'], \
                                     runtime, \
                                     0, \
                                     runid, \
                                     start_seed, \
                                     rcval, \
                                     ss.lambdas[the_jobs_lambda], \
                                     0, \
                                     0, \
                                     uuid, \
                                     customdata \
                                     )

        ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------
# Analyze job nosuccess
# -------------------------------------------------------------------------------------------------

    def analyze_job_nosuccess(self, client, ddata, runid):
        ss = self.server

        ss.logger_freshs.debug(cc.c_magenta + __name__ + ': analyze_job_nosuccess' + cc.reset)

        if 'runtime' in ddata:
            runtime = ddata['runtime']
        else:
            runtime = time.time() - ss.client_runtime[str(client)]
            
        if 'calcsteps' in ddata:
            calcsteps = ddata['calcsteps']
        else:
            calcsteps = 0

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

        try:
            start_seed = ddata['seed']
        except:
            start_seed = 0

        the_jobs_lambda = ddata['act_lambda']
        
        if the_jobs_lambda >= ss.act_lambda:

            ss.logger_freshs.debug(cc.c_magenta + client.name + ': Ghost run was not successful.' + cc.reset)

            try:
                ss.ghostpoints.add_point(the_jobs_lambda, \
                                             '', \
                                             ddata['origin_points'], \
                                             ddata['calcsteps'], \
                                             ddata['ctime'], \
                                             runtime, \
                                             0, \
                                             runid, \
                                             start_seed, \
                                             rcval, \
                                             ss.lambdas[the_jobs_lambda], \
                                             0, \
                                             0, \
                                             uuid, \
                                             customdata \
                                             )

            except:
                ss.logger_freshs.warn(cc.c_red + \
                                      'Omitting unsuccessful ghost run because of incomplete data.' + \
                                      cc.reset)
                ss.logger_freshs.debug(cc.c_red + 'Data was: ' + str(ddata) + cc.reset)

            
        ss.check_for_job(client)

# -------------------------------------------------------------------------------------------------        
        
