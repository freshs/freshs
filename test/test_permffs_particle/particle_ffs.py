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

class particle_ffs:
    def __init__(self, client):
         self.cli = client


    # create particle in ensemble state A
    def init_particle(self, borderA):
        # set location to something between -A...A (symmetric basin, potential minimum at 0)
        xA = borderA * 2.0 * (random.random()-0.5)
        vA = random.random() - 0.5
        aA = self.cli.single_particle_ext_force(xA)
        return xA, vA, aA

#### JOB 1 ####
    def job1_escape_flux(self, parameterset):
        A        = parameterset['A']
        B        = parameterset['B']
        next_interface = parameterset['next_interface']
        act_lambda = parameterset['act_lambda']
        seed       = parameterset['seed']

        print('Calculating escape flux: ' + str(A) + ', ' + str(B))
        
        rcvals = []
        points = []
        q      = 0

        x, v, a = self.init_particle(A)

        t = 0.0
        comefromok = True
        calcsteps = 0
        no_point = 1
        ctime     = 0.0
        return_index = 0
        while no_point and not self.cli.abort:

            if x >= A and comefromok == True:
                points.append([x,v])
                rcvals.append(x)
                q += 1
                no_point = 0
                comefromok = False
                
            if x < A and not comefromok:
                comefromok = True
            
            if x >= B:
                x, v, a = self.init_particle(A)
                comefromok = True
                
            
            t += self.cli.dt
            calcsteps += 1
            x, v, a = self.cli.single_particle_perform_step(x, v, a, \
                                                            self.cli.dt,\
                                                            self.cli.dt2,\
                                                            self.cli.T)   
        ctime = t-self.cli.dt
        

        results = "{\"jobtype\": 1, \"success\": True, \"ctime\": "       + str(ctime)      +\
                                                    ", \"seed\":  "       + str(seed)       + \
                                                    ", \"points\": "      + str(points[0])     +\
                                                    ", \"act_lambda\": "  + str(act_lambda) +\
                                                    ", \"calcsteps\": "   + str(calcsteps)  + " }"
        return results

    
#### JOB 2 ####
    def job2_probabilities(self, parameterset):
        
        A = parameterset['A']
        next_interface = parameterset['next_interface']
        act_lambda     = parameterset['act_lambda']
        seed           = parameterset['seed']
        parent_id      = parameterset['rp_id']
        points = []
        rcvals = []
        ctime  = 0
        calcsteps = 0
        t = 0.0
        results="{\"jobtype\": 2, \"success\": False, \"act_lambda\":"   + str(act_lambda)+\
                                               ", \"seed\":  "           + str(seed)      +\
                                               ", \"origin_points\": \"" + str(parent_id) +"\"}"
        i = 0
        
        run_in_progress = True
        print(parameterset['random_points'])
        x, v = parameterset['random_points']
        a = self.cli.single_particle_ext_force(x)
        while run_in_progress and not self.cli.abort:

            if x >= next_interface:
                points = [x,v]
                ctime = t-self.cli.dt
                results="{\"jobtype\": 2, \"success\": True, \"points\": " + str(points)    +\
                                                      ", \"act_lambda\": "     + str(act_lambda)+\
                                                      ", \"seed\":  "          + str(seed)      +\
                                                      ", \"origin_points\": \""  + str(parent_id) +"\""+ \
                                                      ", \"calcsteps\": " + str(calcsteps) +\
                                                      ", \"ctime\": " + str(ctime) + " }"
                run_in_progress = False

            if x <= A:
                run_in_progress = False
                
            calcsteps += 1
            t += self.cli.dt
            x, v, a = self.cli.single_particle_perform_step(x, v, a, self.cli.dt, self.cli.dt2, self.cli.T)
            
        i += 1
                
        print("client returning results packet: "+str(results)[0:128]+"...")
        return results



#####################################################
       
       
       
       
