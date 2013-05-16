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


# Calculation
import random
import math
##import numpy as np

# Network Comms
import asyncore
import socket

# more comms
import os

# Parsing
import re

##time provides a sleep command for testing trivial clients
import time

##import wrappers for simulation programs
from  particle_ffs   import particle_ffs
from  particle_spres import particle_spres

class particle(asyncore.dispatcher):
    def __init__(self,host,port,barrier,timeout):
        self.received_data = []
        self.save_bytes=""
        self.send_bytes=""
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((host, port))
        self.msg=["ffs client v1"+'PKT_SEP']
        self.dt = 0.001
        self.dt2 = self.dt * self.dt
        self.T = 1.0
        self.gamma = 1.0
        self.barrier = barrier
        self.c_pot = math.pi
        self.abort = False

        ##setup timeout stuff
        start_time      = time.time()
        if timeout != 0:
            self.timeout       = timeout
            self.stop_after    = start_time + (timeout * 60 * 60) ##time to stop at, in seconds.
        else:
            self.timeout       = 0

        ##init handlers for both sampling algorithms: these classes are near-stateless
        ##so there is little overhead for this.
        self.ffs       = particle_ffs(self)
        self.spres     = particle_spres(self)
        
    ###define some functions for comms/book-keeping.
    def handle_error(self):
        if hasattr(self, "in_exception"): return
        pass
        
    def handle_connect(self):
        print 'Trying to connect...'
    
    def handle_close(self):
        print 'Closed. Server not running or disconnected.'
        self.close()
        return
    
    def handle_write(self):
        data=self.msg.pop()
        self.send(data)

    def writable(self):
        return bool(self.msg)

    def process_packet(self, data):

        if "\"jobtype\":" in data:

            try:
                parameterset=eval(data+"\n")
            except:
                print('Warning! Could not parse data packet: ' + data[0:49] + '...') 
                print('Warning! Dropping packet.') 
                return

            ##handle jobs sent in order.
            if parameterset["jobtype"]==1:
                        print 'Starting job1: Escape flux.'
                        result = self.ffs.job1_escape_flux(parameterset)
            elif parameterset["jobtype"]==2:
                        print 'Starting job2: Probabilities.'
                        result = self.ffs.job2_probabilities(parameterset)
            elif parameterset["jobtype"]==3:
                        print 'Starting job3: Fixed tau.'
                        result = self.spres.job3_fixed_tau(parameterset)
            elif parameterset["jobtype"] >  3:
                        print 'Job type not recognised: ' + str(parameterset["jobtype"])
                        print 'Ignoring.'
                        result = ""
            elif parameterset["jobtype"] <= 0:
                        print 'Waiting for new job.'
                        self.abort = True   
                        return
  
            ##test if we should timeout at this point
            last_job = False
            if self.timeout != 0:
                t = time.time()
                if self.stop_after <= t:
                    print "TIMEOUT: client attempting to exit gracefully."
                    result = result + 'WARN_TIMEOUT'
                    last_job = True
                else:
                    print "Future uptime at least "+str(self.stop_after - t)+" seconds."


            result = result + 'PKT_SEP\n'
            packet_len = len(result)
            count      = 0
            while count < packet_len:
                count += self.send( result[count:packet_len] )
                
            print "sent data, size:"+str(len(result))
            if len(result) > 256:
                print "data:"+result[0:64]+"..."
                print "..."+result[len(result)-64:len(result)]
            
            if last_job == True:
                self.close()
                exit('TIMEOUT')
                

        else:
            print "received unknown data:"+data+":end, ignoring"
            



    def handle_read(self):

        data            = self.recv(262144)
        self.abort      = False
        
        #print "raw read of:"+data+":end raw"

        self.save_bytes = self.save_bytes + data
        
        while len(self.save_bytes) != 0 :

            ##left-over bytes after the seperator are saved to save_bytes.
            [data, sep, self.save_bytes] = self.save_bytes.partition('PKT_SEP')
 
            ##if there was a seperator, then process the line 
            if len(sep) != 0:
                self.process_packet(data.lstrip('\n')) ##the separator card may also include a newline.
            else:
                ##otherwise, the packet fragment stays in self.save_bytes
                ##for next time
                self.save_bytes = data 
                return
                    

#####################################################
# Single Particle Functions
#####################################################

#### EXTERNAL FORCE ####
    # sinusoidal with repulsive well outside
    def single_particle_ext_force(self, x):

        ##on [-inf,-1) : E(x) = 5x^2 + 10x + E(-1)
        if x < -1.0 :
            return -10.0*x - 10.0
        else:
        ##on [-1,inf]   : F(x) = -0.5bc  * sin(x c )
        ##             : E(x) =  -0.5b   * cos(x c ) 
            return self.barrier * (-0.5*math.sin(x*self.c_pot)*self.c_pot)

#### PERFORM SIMULATION STEP ####
    def single_particle_perform_step(self,x, v, a, dt, dt2, T):
        rand_gauss = random.gauss(0.0, 1.0)
        x = x + v*dt + 0.5*a*dt**2
        a_new = self.single_particle_ext_force(x) - self.gamma * v + math.sqrt(2.0 * self.gamma * T / dt) * rand_gauss
        v = v + 0.5 * dt * ( a + a_new )
        a = a_new

        return x, v, a_new



#####################################################
       
       
       
       
