# -*- coding: utf-8 -*-
# Copyright (c) 2012 Josh Berryman, University of Luxembourg
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

import os, tempfile
import shutil
import subprocess
import threading
import ast
from   listener import listener
from   feeder   import scriptThread, feeder

############
#
# The harness class serves to start up some MD program and pass
# input data to it through named FIFOS.
#
# The purpose of using the FIFOS and not the filesystem
# is to minimise the latency, which becomes high when disc writes are used.
#
# Some filesystems will also have problems whenever large numbers of files are 
# open.
#
#

class harness:
    def __init__(self, exec_path, job_script, client ):
        
        self.client = client
        
        ##clear some OS flags for fifo-i/o
        os.umask(0)
            
        ##save some useful stuff
        self.sim_exec    = exec_path
        self.job_script  = job_script
        self.childproc   = 0

        ###create pipes to transfer MD coords into/read them back from
        try:
            self.tmpdir             = tempfile.mkdtemp(prefix='freshs')
        except e:
            print("Client: Failed to create tmp dir %s" % e)
            
        self.crds_in_fifoname   = os.path.join(self.tmpdir, 'crds_in')
        self.control_fifoname   = os.path.join(self.tmpdir, 'cont_in')
        self.crds_back_fifoname = os.path.join(self.tmpdir, 'crds_bac')
        self.metadata_fifoname  = os.path.join(self.tmpdir, 'meta_bac')
        try:
            os.mkfifo(self.crds_in_fifoname)
            os.mkfifo(self.crds_back_fifoname)
            os.mkfifo(self.control_fifoname)
            os.mkfifo(self.metadata_fifoname)
                
        except OSError, e:
            print("Client: Failed to create FIFO: %s" % e)
        
        self.save_bytes=''

    def build_argList(self,parameterset):
        argList = []
        if self.client.cli.execprefix != 'none':
            argList += self.client.cli.execprefix.split(' ') + [self.sim_exec]
        elif self.client.cli.nice_job > 0:
            argList += ['nice','-n',str(self.client.cli.nice_job),self.sim_exec]
        else:
            argList.append(self.sim_exec)
        argList.append(self.job_script)
        for parm in parameterset.split():
            argList.append(parm)
        return argList

   
    def fork_run_script(self, parameterset):
        
        ##start a child process
        self.childproc = os.fork()        
        if  self.childproc == 0: ##in child process
            argList = self.build_argList(parameterset)
            print("Client: Calling the following: " + ' '.join(argList))
            outstatus=subprocess.call(argList)
            print("Client: Simulation program returned, status: " + str(outstatus) + " . Closing fork.")
            exit(0)
        else:
            return
            
    def subthread_run_script(self, parameterset):
        
        ##start a child process    
        argList = self.build_argList(parameterset)
        print("Client: Calling the following: " + ' '.join(argList))
        
        self.sT = scriptThread(argList)
        self.sT.daemon = True
        self.sT.run()
       
            
            
    def send( self, send_coords, get_coords, get_meta, act_point ):

            self.send_coords =  send_coords
            self.get_coords  =  get_coords
            self.get_meta    =  get_meta
            
            run_in_progress = True
            self.pp = []    
            self.mp = [] 
            
        ##loop over multiple start points that we may have been sent?? Should only be 1.
        ##Is neccesary to pass in a list, however, or python will not pass-by-reference?
        #for act_point in act_points:
   

            ##send the config to the MD process
            if send_coords == True :
                print("Client: Starting coords writer subthread")
                self.ocFeeder = feeder(self.crds_in_fifoname, act_point, self.client)

            if get_coords == True :
                print("Client: Starting coords listener subthread")
                self.ocListener = listener(self.crds_back_fifoname, self.pp)

            if get_meta == True :
                print("Client: Starting metadata listener subthread")
                self.omListener = listener(self.metadata_fifoname, self.mp)
               
            
    def collect( self, points, rcvals ):
    
            ##Blocking wait for listener threads to finish.
            ##No point waiting for the feeder.
            if self.get_coords == True:
                # Tricking: setting timeout to a week, otherwise CTRL-C does not work
                self.ocListener.lT.join(604800)
                print("Client: Coords read thread closed")
                
                ##collect the return data from the coords thread
                points.append(self.pp)
            
            ##parse the return data from the metadata thread
            if self.get_meta == True :
                self.omListener.lT.join()
                print("Client: Metadata read thread closed")

                line      = self.mp[0]
                metadata  = ast.literal_eval(line[0])
            
                this_rc   = metadata['rc']
                rcvals.append(this_rc)
                calcsteps = metadata['steps']
                ctime     = metadata['time']
            
                #print("Client: set metadata: "+str(metadata)

            return( calcsteps, ctime, this_rc, metadata )
            
############################ Helper functions:            
              
    def clean(self):
        
        print("Client: Cleaning...")

        ##try and kill any threads that are waiting
        try:
            for t in threading.enumerate():
                    if t.daemon:
                        print("Client: Stopping thread: _"+str(t))
                        t.stop_event.set() 
        except e:
            print("Client Warning: Could not set stop flags for harness threads: %s", e)
            

        ##wait with a timeout of 1 second for each thread to 
        ##act on its "stop_event".
        try:
            for t in threading.enumerate():
                    if t.daemon:
                        print("Client: Cleaning thread: _"+str(t))
                        t.join(1.0)
        except e:
            print("Client Warning: harness threads may not have died cleanly: %s", e)
        
        ##make sure that the childproc exits cleanly
        ##os.kill(self.childproc, os.SIGKILL)
        if self.childproc != 0 :
            print("Client: Cleaning process "+str(self.childproc))
            #os.kill(self.childproc, os.SIGKILL)
            os.waitpid(0, 0) ##this call has the effect to clear up any "defunct" processes.
   
        ##clean up the filesystem
        for fname in [self.crds_in_fifoname, self.crds_back_fifoname, self.control_fifoname, self.metadata_fifoname]:
            try:
                #os.remove(fname)
		shutil.rmtree(fname)
            except:
                print("Client Warning: Could not delete named fifo in tmpdir: " + fname)
                    
        try:
            os.rmdir(self.tmpdir)
        except:
            print("Client Warning: Could not delete tmpdir: " + self.tmpdir)
                
        
        print("Client: Cleaned.")
   
   

#####################################################
       
       
       
       
