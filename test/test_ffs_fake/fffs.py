# -*- coding: utf-8 -*-
# Copyright (c) 2012 Kai Kratzer, Universität Stuttgart, ICP,
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

import random
import math
import time

import ConfigParser

import fclient

# Fake FFS module.
class fffs:
    def __init__(self,numclients,dt,p_success,report_delay,srv_conf):

        self.numclients = numclients
        self.dt = dt
        self.p_success = p_success
        self.report_delay = report_delay

        self.clients = []

        self.ctime = 0.0
        self.q_esc = 0
        self.sum_calcsteps = 0

        self.launched2 = []
        self.success2 = []
        self.ill = []

        self.load_srv_conf(srv_conf)

        self.launch_clients()
        random.seed(13371337)


    def load_srv_conf(self,srv_conf):
        configfile = ConfigParser.RawConfigParser()
        configfile.read(srv_conf)
        lambdaload = True
        A = configfile.getfloat('hypersurfaces', 'borderA')  # starting region
        B = configfile.getfloat('hypersurfaces', 'borderB')  # target region
        self.lambdas = [A]
        # number of interfaces
        self.noi = 1
        while lambdaload:
            try:
                self.lambdas.append(configfile.getfloat('hypersurfaces', 'lambda'+str(self.noi)))
                self.noi += 1
                self.launched2.append(0)
                self.success2.append(0)
            except:
                lambdaload = False
        self.lambdas.append(B)
        self.launched2.append(0)
        self.success2.append(0)

        # number of runs per interface
        self.M_0_runs = [configfile.getint('runs_per_interface', 'borderA')]
        for act_entry in range(1,self.noi):
            self.M_0_runs.append(configfile.getint('runs_per_interface', 'lambda' + str(act_entry)))
        self.M_0_runs.append(configfile.getint('runs_per_interface', 'borderB'))
        print self.M_0_runs, self.lambdas, self.launched2
        
        
    def launch_clients(self):
        for i in range(self.numclients):
            cl_name = 'client' + str(i)
            print "Launching", cl_name
            the_client = fclient.fclient(self, 'localhost', 10000, 99999, self.report_delay, cl_name)
            self.clients.append(the_client)
            the_client.start()
            time.sleep(self.report_delay)

    # Job 1
    def job1_escape_flux(self,client, parameterset):
        print client.name, "is asking for escape job parameters."
        act_lambda = parameterset['act_lambda']
        seed       = parameterset['seed']
        if parameterset['next_interface'] not in self.ill:
            self.ill.append(parameterset['next_interface'])
        tmp_calcsteps = self.get_calcsteps()
        tmp_time = self.get_time(tmp_calcsteps)
        tmp_point = self.get_point(client,act_lambda)
        #tmp_realtime = self.get_realtime()
        self.ctime += tmp_time
        self.q_esc += 1
        
        self.sum_calcsteps += tmp_calcsteps
        
        results = "{\"jobtype\": 1, \"success\": True, \"ctime\": "       + str(tmp_time)      +\
                                                    ", \"seed\":  "       + str(seed)       + \
                                                    ", \"points\": "      + str(tmp_point)     +\
                                                    ", \"act_lambda\": "  + str(act_lambda) +\
                                                    ", \"calcsteps\": "   + str(tmp_calcsteps)  + " }"
        #print str(results)
        return results

    # Job 2    
    def job2_probabilities(self,client, parameterset):
        print client.name, "is asking for job2 parameters."
        act_lambda     = parameterset['act_lambda']
        seed           = parameterset['seed']
        parent_id      = parameterset['rp_id']
        if parameterset['next_interface'] not in self.ill:
            self.ill.append(parameterset['next_interface'])
        tmp_calcsteps = self.get_calcsteps()
        tmp_time = self.get_time(tmp_calcsteps)
        #tmp_realtime = self.get_realtime()
        tmp_success = self.have_success()
        tmp_point = self.get_point(client,act_lambda)
        tmp_max_lam = self.get_max_lam(parameterset['A'],parameterset['next_interface'])
        self.sum_calcsteps += tmp_calcsteps

        print tmp_success, self.launched2, self.success2
        if act_lambda < 1337:
            self.launched2[act_lambda-1] += 1
       
        if tmp_success:
            if act_lambda < 1337:
                self.success2[act_lambda-1] += 1
            results="{\"jobtype\": 2, \"success\": True, \"points\": " + str(tmp_point)    +\
                                                  ", \"act_lambda\": "     + str(act_lambda)+\
                                                  ", \"seed\":  "          + str(seed)      +\
                                                  ", \"origin_points\": \""  + str(parent_id) +"\""+ \
                                                  ", \"calcsteps\": " + str(tmp_calcsteps) +\
                                                  ", \"max_lam\": " + str(tmp_max_lam) +\
                                                  ", \"ctime\": " + str(tmp_time) + " }"
        else:
            results="{\"jobtype\": 2, \"success\": False, \"act_lambda\":"   + str(act_lambda)+\
                                                   ", \"seed\":  "           + str(seed)      +\
                                                   ", \"max_lam\": " + str(tmp_max_lam) +\
                                                   ", \"origin_points\": \"" + str(parent_id) +"\"}"
        return results


    # Return a fake point
    def get_point(self, client, act_lambda):
        print "returning point"
        return [str(act_lambda) + '_' + client.name + '_' + str(time.time())]

    # Return a calcstep value
    def get_calcsteps(self):
        print "returning calcsteps"
        return int(10000.0*random.random())
        
    # Helper function for simulation time
    def get_time(self, steps):
        print "returning time"
        return float(steps)*self.dt
        
    # Return a value for the real execution time in [s]
    def get_realtime(self):
        print "returning realtime"
        return int(86000.0*random.random())

    def get_max_lam(self,A,B):
        print "returning max_lam"
        return random.uniform(A,B)
        
    # decide, if simulation run should have success
    def have_success(self):
        print "returning successval"
        testval = random.random()
        if testval < self.p_success:
            return True
        else:
            return False
            

    def check_runs(self):
        if not self.q_esc == self.M_0_runs[0]:
            print "WARNING: n_escape_points is", self.q_esc, "and should be",  self.M_0_runs[0]
        for i in range(len(self.success2)):
            if not self.M_0_runs[i+1] == self.success2[i]:
                print "WARNING: n_points on lambda", i+1, "is", self.success2[i], "and should be",  self.M_0_runs[i+1]
        print "M_0_runs :", self.M_0_runs
        print "success2 :", self.success2
        print "launched2:", self.launched2
    
    def get_k_AB(self):
        print "Interfaces were:", self.ill
        self.check_runs()

        k_AB_part2 = 0.0

        phi = float(self.q_esc) / self.ctime
        k_AB_part1 = math.log(phi)
        print "k_AB_part1 is", phi


        for i in range(len(self.success2)):
            if self.launched2[i] > 0:
                p_part = float(self.success2[i])/float(self.launched2[i])
                k_AB_part2 += math.log(p_part)
                print "Added p = ",p_part,"for interface",i+1

        #p_part = float(self.success2[-1])/float(self.launched2[-1])
        #k_AB_part2 += math.log(p_part)
        return math.exp( k_AB_part1 + k_AB_part2 )
        
        
        
     
        
        
        
        

            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
            
