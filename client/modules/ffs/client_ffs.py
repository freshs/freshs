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

import time

##import wrappers for simulation programs
from harness import harness

class client_ffs:
    def __init__(self, client):
        self.cli = client

    # build flexible option string
    def build_options(self,paramdict):
        optionstring = ''
        for el in paramdict:
            if el != 'random_points':
                optionstring += ' -' + str(el) + ' ' + str(paramdict[el])
        return optionstring

    def build_custominfo(self, basis, paramdict):
        for el in paramdict:
            if el not in basis:
                basis += ", \"" + el + "\": " + str(paramdict[el])
        return basis

    #### JOB 1 ####
    def job1_escape_flux(self, parameterset):
        A        = parameterset['A']
        B        = parameterset['B']
        #next_interface = parameterset['next_interface']
        act_lambda = parameterset['act_lambda']
        seed       = parameterset['seed']
        try:
            parent_id      = parameterset['rp_id']
        except:
            parent_id = 'escape'

        if 'uuid' in parameterset:
            uuid = parameterset['uuid']
        else:
            uuid = ''

        print 'Calculating escape flux: ' + str(A) + ', ' + str(B)
        
        all_meta = {}
        
        success = False
        
        rcvals=[]
        points    = []
        q         = 0
            
        h = harness(self.cli.exec_name, self.cli.harness_path + "/job_script", self)
                    
        # Wrap the code that uses threading/subprocesses
        # in a try-catch to clean up on interrupts, ctrl-C etc.
        
        try:
            # start loading the input pipes for the MD process
            use_previous_point = False
            
            # Checking for previous points
            if 'random_points' in parameterset:
                print "Random points key in paramset"
                if not 'None' in str(parameterset['random_points']):
                    # Use previous point
                    use_previous_point = True
                
            if use_previous_point:
                # we are at least on A...
                comefromok = False
                h.send( True, parameterset['random_points'] )

                optionlist = "-tmpdir " + h.tmpdir + \
                             " -in_fifoname " + h.crds_in_fifoname + \
                             " -back_fifoname " + h.crds_back_fifoname + \
                             " -metadata_fifoname " + h.metadata_fifoname + \
                             " -halt_steps 0 " + \
                             " -check_rc_every 1" + \
                             self.build_options(parameterset)

                h.subthread_run_script(optionlist, True)

            else:
                # we assume that the simulation is set up in A if no
                # last successful point is received
                comefromok = True
                h.send( False, [[0]] )

                optionlist = "-tmpdir " + h.tmpdir + \
                             " -initial_config " + self.cli.harness_path + "/initial_config.dat" + \
                             " -back_fifoname " + h.crds_back_fifoname + \
                             " -metadata_fifoname " + h.metadata_fifoname + \
                             " -halt_steps 0 " + \
                             " -check_rc_every 1" + \
                             self.build_options(parameterset)

                h.subthread_run_script(optionlist, False)

            calcsteps = 0
            ctime     = 0
            
            while True:

                # read output from the MD subthread
                steps, time, rc, all_meta  = h.collect( points, rcvals ) 
                calcsteps += steps
                ctime     += time

                print "Client: collected " + str((steps, time, rc))

                flRc = float(rc)

                if 'step_abort' in all_meta:
                    if all_meta['step_abort']:
                        success = False
                else:
                    success = True

                if self.cli.checking_script > 0:
                    break
                else:
                    # Verify that escape conditions have been met.
                    # This is necessary for simulation tools
                    # which do not do this logic themselves

                    if flRc >= float(B):
                        print "Client: reached B, resetting"
                        break
                    elif flRc >= float(A) and comefromok:
                        print "Client: reached interface coming from A, saving point."
                        comefromok = False
                        success = True
                        break
                    elif flRc < float(A) and not comefromok:
                        print "Client: has fallen back to A"
                        comefromok = True

                    ##
                    print "Client: continuing, with rc: "+str(flRc)+" of "+str(A)+", "+str(B)


                    # Start a new sender to write out the data that we just recieved.
                    # Assuming that it is safe to both read and write from points, because all
                    # simulation programs will complete reading their input
                    # before they write their output.
                    h.send( True, points[-1] ) 


                    optionlist = "-tmpdir " + h.tmpdir + \
                                 " -in_fifoname " + h.crds_in_fifoname + \
                                 " -back_fifoname " + h.crds_back_fifoname + \
                                 " -metadata_fifoname " + h.metadata_fifoname + \
                                 " -halt_steps 0 " + \
                                 " -check_rc_every 1" + \
                                 self.build_options(parameterset)

                    # fork a subthread to run the MD, starting from the crds_in fifo.            
                    h.subthread_run_script(optionlist, False)

        except e:
            print( "Client: exception while running harness, %s" % e ) 
            h.clean()
            exit( e )
        h.clean()
        
        print "Constructing result string"

        if success:
            results_base = "\"jobtype\": 1, \"success\": True, \"points\": " + str(points[-1])
        else:
            results_base = "\"jobtype\": 1, \"success\": False"
        
        results_base += ", \"ctime\": "  + str(ctime) + \
                        ", \"seed\":  "      + str(seed) + \
                        ", \"act_lambda\": " + str(act_lambda) + \
                        ", \"calcsteps\": "  + str(calcsteps) + \
                        ", \"origin_points\": \"" + str(parent_id) + "\"" + \
                        ", \"rcval\": "      + str(flRc) + \
                        ", \"uuid\": \""      + uuid + "\""

        print "Resultstring before appending:", results_base

        results = self.build_custominfo(results_base, all_meta)

        print "Resultstring after appending:", results

        return "{" + results + "}"

    
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

        i = 0

        if 'uuid' in parameterset:
            uuid = parameterset['uuid']
        else:
            uuid = ''

        all_meta = {}

        h = harness(self.cli.exec_name,  self.cli.harness_path+"/job_script", self)
                                           
        # Wrap the code that uses threading/subprocesses
        # in a try-catch to clean up on interrupts, ctrl-C etc.
        try:     
            
            print "sending: "+str(parameterset['random_points'])[0:64]

            # start loading the input pipes for the MD process
            h.send( True, parameterset['random_points'] )
            calcsteps = 0
            ctime     = 0

            while True:

                optionlist = "-tmpdir " + h.tmpdir + \
                             " -in_fifoname " + h.crds_in_fifoname + \
                             " -back_fifoname " + h.crds_back_fifoname + \
                             " -metadata_fifoname " + h.metadata_fifoname + \
                             " -halt_steps 0 " + \
                             " -check_rc_every 1" + \
                             self.build_options(parameterset)

                # fork a subthread to run the MD
                h.subthread_run_script(optionlist, True)

                # read output from the MD subthread
                steps, time, rc, all_meta  = h.collect( points, rcvals ) 
                calcsteps += steps
                ctime     += time

                flRc = float(rc)
                
                if self.cli.checking_script > 0:
                    break
                else:
                    # Verify that the conditions have been met.
                    # This is necessary for simulation tools
                    # which do not do this logic themselves
                    if flRc <= A:
                        break
                    elif flRc >= next_interface:
                        break

                    # Start a new sender to write out the data that we just recieved.
                    # Assuming that it is safe to both read and write from points, because all
                    # simulation programs will complete reading their input
                    # before they write their output.
                    h.send( True, points[-1] )

        except e:
            print( "Cient: exception while running harness, %s" % e ) 
            h.clean()
            exit( e )
        h.clean()

        # only build a full results packet if we have a success
        if flRc >= next_interface:
            results_base = "\"jobtype\": 2, \"success\": True, \"points\": " + str(points[-1])
        else:
            results_base = "\"jobtype\": 2, \"success\": False"

        results_base += ", \"act_lambda\": "      + str(act_lambda)+ \
                        ", \"seed\":  "           + str(seed)      + \
                        ", \"origin_points\": \"" + str(parent_id) + "\"" + \
                        ", \"calcsteps\": "       + str(calcsteps) + \
                        ", \"ctime\": "           + str(ctime) + \
                        ", \"rcval\": "           + str(flRc) + \
                        ", \"uuid\": \""            + uuid + "\""
            
        
             
             
        print "Resultstring before appending:", results_base

        results = self.build_custominfo(results_base, all_meta)

        print "Resultstring after appending:", results

        return "{" + results + "}"



#####################################################
       
       
       
       
