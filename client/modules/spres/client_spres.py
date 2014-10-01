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

##import wrappers for simulation programs
from   harness import harness
import os

import sys


class client_spres:
    def __init__(self, client):
        self.cli       = client
        self.prinlevel = 0

    # build flexible option string
    def build_options(self,paramdict,exclude):
        optionstring = ''
        for el in paramdict:
            if el != 'random_points' and el not in exclude:
                optionstring += ' -' + str(el) + ' ' + str(paramdict[el])
        return optionstring

    def build_custominfo(self, basis, paramdict):
        for el in paramdict:
            if el not in basis:
                basis += ", \"" + el + "\": " + str(paramdict[el])
        return basis

    def safeAssign( self, parameterset, myKey ):
    
     try:
         return(parameterset[myKey])
     except KeyError:
         return None


#### JOB 3 ####
    def job3_fixed_tau(self, parameterset):
        
        if self.prinlevel > 0:
              print("parameters:")
	      sys.stdout.flush()
              print(str(parameterset)[0:128]+"...")
              sys.stdout.flush()

        ##expected parameters for this job type
        tau              = self.safeAssign(parameterset, 'halt_steps')
        seed             = self.safeAssign(parameterset, 'seed')
        currentLambda    = self.safeAssign(parameterset, 'seed')
        parent_id        = self.safeAssign(parameterset, 'rp_id')
        seed             = self.safeAssign(parameterset, 'seed')
        currentlambda    = self.safeAssign(parameterset, 'currentlambda') 
        parentlambda     = self.safeAssign(parameterset, 'parentlambda')
        uuid             = self.safeAssign(parameterset, 'uuid')

        check_rc_every   = self.safeAssign(parameterset, 'check_rc_every') 
        if check_rc_every is None:
            check_rc_every = "0"

        save_configs     = self.safeAssign(parameterset, 'save_configs') 
        if save_configs is None:
            save_configs = "0"

        rcvals    = []
        ctime     = []
        all_meta  = {}
        t         = 0.0
        num_steps = 0
        ctime_tot = 0.0
        step      = tau
        results   = "{\"jobtype\": 3, \"success\": False, \"currentlambda\": " + str(currentlambda) + \
                                                       ", \"parentlambda\": "  + str(parentlambda)  + \
                                                       ", \"origin_points\": " + str(parent_id)  + \
                                                       " }"
       
        ##create a harness object to manage comms with the subtask.
        h = harness(self.cli.exec_name,  self.cli.harness_path+"/job_script", self )
        tmp_seed = int(seed)
        points=parameterset['random_points']
        while num_steps < tau :
                
            print("Using temp dir: "+str(h.tmpdir))
            

            optionlist = ""
            if parent_id == "0" and num_steps == 0:
                start_config = self.cli.initial_config_path
                in_fifo      = "None"
                get_coords   = True
                send_coords  = False
                if os.path.isfile(start_config):
                    print("client: Found file at: "+start_config)
                    print("client: Treating input coords as NULL, loading from file.")
                else:
                    print("client: Treating input coords as NULL:\n"+\
                          "client:    could not find input file: "+str(start_config)+"\n"\
                          "client:    hoping that the harness will generate one!")
                    start_config = "None"
            else: 


                ##assume that saving to file means reading from a file
                if save_configs != "0":
                    start_config = points[0][0]
                    get_coords   = True   ##only open a read fifo, to get the filename of the crds
                    send_coords  = False
                    in_fifo      = "None"
                else:
                    start_config = "None"
                    get_coords   = True   ##open two fifos, send and receive
                    send_coords  = True
                    in_fifo      = h.crds_in_fifoname

                    
            optionlist = " -tmpdir " + h.tmpdir + \
                             " -in_fifoname " + in_fifo + \
                             " -initial_config "+ start_config + \
                             " -back_fifoname " + h.crds_back_fifoname + \
                             " -metadata_fifoname " + h.metadata_fifoname + \
                             " -seed " + str(tmp_seed)



            if check_rc_every == "0":
                optionlist +=  " -check_rc_every 0 "  

                ##pass the remaining options from the parameterset straight through
                ##....but with some exclusions.
                optionlist += self.build_options(parameterset,\
                                               ["jobtype","halt_rc_upper", "halt_rc_lower", "save_configs"])
            else:
                ##pass the remaining options from the parameterset straight through
                ##....but with some exclusions.
                optionlist += self.build_options(parameterset, ["jobtype"])

            ##are we just saving state locally and sending a path back to the server?
            if save_configs != "0":
                optionlist += " -coords_to_file "+save_configs+"/"+uuid
            

            print("client: optionlist: "+str(optionlist)[0:128]+"...")

            ##Wrap the code that uses threading/subprocesses
            ##in a try-catch to clean up on interrupts, ctrl-C etc.
            try:
                h.send( send_coords, get_coords, True, points ) 
                h.subthread_run_script(optionlist)

                pp=[]
                calcsteps, ctime, rc, all_meta  = h.collect( pp, rcvals )
            except e:
                print( "Client: exception while runnning harness, %s" % e )
                h.clean()
                exit( e )

                
            num_steps  = num_steps + calcsteps
            ctime_tot += ctime

            if str(check_rc_every) != "0" :
                #tmp_seed += 1
                if rc >= B:
                    print( "Client: ending run, rc: "+str(rc) + " reached B: "+str(B))
                    rcvals    = [rc]
                    break
                elif num_steps >= tau:
                    print( "Client: ending run, steps " + str(num_steps) + " reached tau: " + str(tau) )
                    rcvals    = [rc]
                    break
                else:
                    if send_coords == False:
                        send_coords = True
                        start       = h.crds_in_fifoname

                    ##recycle the input points
                    points = pp[0]
                   

        ##clean up the fifos.
        h.clean()

        ##build the return packet        
        results="\"jobtype\": 3, \"success\": True"                                 + \
                                         ", \"seed\": "+ str(seed)                   + \
                                         ", \"parentlambda\": " + str(currentlambda) + \
                                         ", \"newlambda\": " + str(rcvals)           + \
                                         ", \"origin_points\": \""  + str(parent_id) +"\""+ \
                                         ", \"calcsteps\": " + str(num_steps)        + \
                                         ", \"ctime\": " + str(ctime_tot)            + \
                                         ", \"points\": " + str(pp)           + \
                                         ", \"uuid\": \""            + uuid + "\""
                                         

        results = self.build_custominfo(results, all_meta)

        print("client returning results packet: "+str(results)[0:128]+"..."+str(results[len(results)-64:len(results)]))
        return "{" + results + "}"
         
         
#####################################################
       
       
       
       
