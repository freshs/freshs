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
from harness import harness

class client_spres:
    def __init__(self, client):
        self.cli = client

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

#### JOB 3 ####
    def job3_fixed_tau(self, parameterset):
        
        
        A = parameterset['A']
        B = parameterset['B']
        tau            = parameterset['tau']
        parentlambda   = parameterset['parentlambda']
        parent_id      = parameterset['rp_id']
        currentlambda  = parameterset['currentlambda']
        absorb_at_B    = parameterset['absorb_at_B']
        seed           = parameterset['seed']
        
        print 'Doing fixed-tau run from bin-pair ' + str(currentlambda) + ' ' + str(parentlambda) + ' for time: ' + str(tau)
        points = []
        rcvals = []
        ctime  = []

        all_meta = {}

        t      = 0.0
        results   = "{\"jobtype\": 3, \"success\": False, \"currentlambda\": " + str(currentlambda) + \
                                                       ", \"parentlambda\": "  + str(parentlambda)  + \
                                                       ", \"origin_points\": " + str(parent_id)  + \
                                                       " }"
        if 'uuid' in parameterset:
            uuid = parameterset['uuid']
        else:
            uuid = ''

       
        #if absorb_at_B != 0:
        #    step=absorb_at_B
        #else:
        step=tau
        
        num_steps  = 0
        ctime_tot  = 0.0

        ##create a harness object to manage comms with the subtask.
        h = harness(self.cli.exec_name,  self.cli.harness_path+"/job_script", self )
        tmp_seed = int(seed)
        points=parameterset['random_points']
        while num_steps < tau :
                
        
            ##print "parameterset: "+str(parameterset)

            ##test if we have start coordinates or
            ##if we are reading from a file.
            twoWay = True   ##open two fifos, send and receive
            start  = h.crds_in_fifoname
            print "client: points:"+str(points)[0:128]+"..."
            if str(parameterset['rp_id']) == "0" and num_steps == 0:
                print "client: Treating input coords as NULL, loading from file."

                inpoints = points[0][0].split()
                print "client: inpoints:"+str(inpoints)[0:128]+"..."
                points[0][0]   = "f1: "+self.cli.harness_path+"/initial_config.dat"
                print "client: len(inpoints):"+str(len(inpoints))
                if len(inpoints) > 2:
                    for i in range(2,len(inpoints)):
                        points[0][0] = points[0][0]+" "+str(inpoints[i])
            else: 
                print "client: Loading from previous output data."
            


            ##Wrap the code that uses threading/subprocesses
            ##in a try-catch to clean up on interrupts, ctrl-C etc.
            try:
                print "Client: sending: "+str(points)[0:128]+"..."

                h.send( twoWay, points ) ##Assuming it is safe to send points and also write to it
                                         ##because the simulation program will finish reading before it writes.
                optionlist = "-tmpdir " + h.tmpdir + \
                             " -in_fifoname " + start + \
                             " -back_fifoname " + h.crds_back_fifoname + \
                             " -metadata_fifoname " + h.metadata_fifoname + \
                             " -seed " + str(tmp_seed) + \
                             " -halt_steps " + str(step) + \
                             " -check_rc_every " + str(absorb_at_B) + \
                             " -halt_rc_upper " + str(B) + \
                             " -halt_rc_lower " + str(0.0)

                optionlist += self.build_options(parameterset,optionlist)

                h.subthread_run_script(optionlist, twoWay)
                pp=[]
                calcsteps, ctime, rc, all_meta  = h.collect( pp, rcvals )
                print "Client: collected points: "+str(pp)[0:128]+" ... "+str(pp)[-64:-1]
                print "Client: collected metadata: "+str((calcsteps, ctime, rc))
            except e:
                print( "Client: exception while runnning harness, %s" % e )
                h.clean()
                exit( e )

                

            num_steps  = num_steps + calcsteps
            ctime_tot += ctime

            if absorb_at_B != 0 :
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
                    if twoWay == False:
                        twoWay = True
                        start  = h.crds_in_fifoname

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

        print "client returning results packet: "+str(results)[0:128]+"..."+str(results[len(results)-64:len(results)])
        return "{" + results + "}"
         
         
#####################################################
       
       
       
       
