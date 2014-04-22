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

import sys
import subprocess
import time
import os

# Append paths
reldir = os.path.dirname(__file__)
if not reldir:
    reldir = '.'
#sys.path.append(reldir + '/modules')
sys.path.append(reldir + '/ffs')
sys.path.append(reldir + '/spres')

# Network Comms
import asyncore
import socket

# if your system environment does not support config parsing,
# replace the variables in read_config() by your values and comment
# everything
import ConfigParser

# time provides a sleep command for testing trivial clients
import time

# parsing
import ast
import re

# import wrappers for simulation programs
from  client_ffs   import client_ffs
from  client_spres import client_spres

class client(asyncore.dispatcher):
    def __init__(self, configfile, execprefix, execpath, harness, startconfig, server_address):

        if configfile == 'auto':
            configfile = 'client-sample.conf'

        print 'Client initialising'
        sys.stdout.flush()

        self.read_configfile(configfile)

        ##Allow CL arguments to overwrite the config file
        self.execprefix = execprefix
        if execpath != 'auto':
           self.exec_name = execpath
        if harness != 'auto':
           self.harness_path = harness
        if startconfig != 'auto':
           self.initial_config_path = startconfig
        else:
           self.initial_config_path = self.harness_path+"/initial_config.dat"
        if server_address != 'auto':
           self.host = server_address.split(':')[0]
           if len(server_address.split(':')) > 1:
                self.port = int(server_address.split(':')[1])



        self.received_data = []
        self.save_bytes=""
        self.send_bytes=""
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)

        if self.ssh_tunnel > 0:
            self.create_ssh_tunnel()

        self.connect((self.host, self.port))

        self.msg=["ffs client v1"+'PKT_SEP']
        self.abort = False


        # setup timeout stuff
        start_time      = time.time()
        if self.timeout != 0.0:
            self.stop_after    = start_time + (self.timeout * 60 * 60) ##time to stop at, in seconds.
        else:
            self.timeout = 0

        # init handlers for both sampling algorithms: these classes are near-stateless
        # so there is little overhead for this.
        self.ffs       = client_ffs(self)
        self.spres     = client_spres(self)
        
        print 'client initted to run scripts in: ' +  self.harness_path +\
              ' using executable: ' + self.exec_name    
        sys.stdout.flush()

    # read the config file
    def read_configfile(self, tcfg):
        self.configfile = ConfigParser.RawConfigParser()
        self.configfile.read(tcfg)

        if self.configfile.has_option('general', 'host'):
            self.host = str(self.configfile.get('general', 'host'))
        else:
            self.host = 'localhost'
        if self.configfile.has_option('general', 'port'):
            self.port = self.configfile.getint('general', 'port')
        else:
            self.port = 10000
        if self.configfile.has_option('general', 'ssh_tunnel'):
            self.ssh_tunnel = self.configfile.getint('general', 'ssh_tunnel')
        else:
            self.ssh_tunnel = 0
        if self.ssh_tunnel > 0 and self.configfile.has_option('general', 'ssh_tunnelcommand'):
            self.ssh_tunnelcommand = str(self.configfile.get('general', 'ssh_tunnelcommand'))
        else:
            self.ssh_tunnelcommand = ''
        if self.configfile.has_option('general', 'timeout'):
            self.timeout = self.configfile.getfloat('general', 'timeout')
        else:
            self.timeout = 0.0
        if self.configfile.has_option('general', 'nlines_in'):
            self.nlines_in = self.configfile.getint('general', 'nlines_in')
        else:
            self.nlines_in = 0
        
        if self.configfile.has_option('general', 'nice_job'):
            self.nice_job = self.configfile.getint('general', 'nice_job')
        else:
            self.nice_job = 0



        ##########these option moved from server.cfg
        # do we hit the filesystem or not?
        #if self.configfile.has_option('general', 'clients_use_filesystem'):
        #    self.clients_use_fs = self.configfile.getboolean('general', 'clients_use_filesystem')
        #else:
        #    self.clients_use_fs = False

        # if we are hitting the filesystem, where do we put the files?
        #self.config_folder = "CONF"
        #if self.configfile.has_option('general', 'config_folder'):
        #    self.config_folder = self.configfile.getboolean('general', 'config_folder')

        

        # FFS specific
        if self.configfile.has_option('ffs_control', 'checking_script'):
            self.checking_script = self.configfile.getint('ffs_control', 'checking_script')
        else:
            self.checking_script = 0

        # these options are required either on CL or in config
        if self.configfile.has_option('general', 'executable'):
            self.exec_name = str(self.configfile.get('general', 'executable'))
            
        if self.configfile.has_option('general', 'harness'):
            self.harness_path = str(self.configfile.get('general', 'harness'))
           
        # if this option is null, harness_path+"/initial_config.dat" will be searched
        if self.configfile.has_option('general', 'initial_config_path'):
            self.initial_config_path = str(self.configfile.get('general', 'initial_config_path'))
        else:
            self.initial_config_path = "None"

    # Create ssh tunnel if it does not exist already
    def create_ssh_tunnel(self):
        ntunnels = int(re.sub('\n','',subprocess.check_output('ps -ef | grep "' + self.ssh_tunnelcommand + '" | grep -v grep | wc -l',shell=True)))
        if ntunnels > 0:
            print "At least 1 ssh tunnel command is already running, not creating a new one."
        else:
            tcmd = self.ssh_tunnelcommand.split(' ')
            print "Opening tunnel with", self.ssh_tunnelcommand
            subprocess.Popen(tcmd)
            time.sleep(2)
            
    # define some functions for comms/book-keeping.
    def handle_error(self):
        if hasattr(self, "in_exception"): return
        pass
        
    def handle_connect(self):
        print 'Trying to connect...'
    
    def handle_close(self):
        print 'Closed. Server not running or disconnected.'
        self.close()
        exit(0)
        return
    
    def handle_write(self):
        data=self.msg.pop()
        self.send(data)

    def writable(self):
        return bool(self.msg)

    def process_packet(self, data):

        if "\"jobtype\":" in data:

            try:
                parameterset=ast.literal_eval(data+"\n")
            except:
                print('Client: Warning! Could not parse data packet: ' + data) 
                print('Client: Warning! Dropping packet.') 
                return

            ##handle jobs sent in order.
            if parameterset["jobtype"] == 1:
                        print 'Starting job1: Escape flux.'
                        result = self.ffs.job1_escape_flux(parameterset)
            elif parameterset["jobtype"] == 2:
                        if "only_escape" in parameterset:
                            print "Exiting because only escape run was desired!"
                            raise SystemExit
                        print 'Starting job2: Probabilities.'
                        result = self.ffs.job2_probabilities(parameterset)
            elif parameterset["jobtype"] == 3:
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
  
            # test if we should timeout at this point
            last_job = False
            if self.timeout != 0:
                t = time.time()
                if self.stop_after <= t:
                    print "TIMEOUT: client attempting to exit gracefully."
                    result = result + 'WARN_TIMEOUT'
                    last_job = True
                else:
                    print "Future uptime at least " + str(self.stop_after - t) + " seconds."


            result = result + 'PKT_SEP\n'
            packet_len = len(result)
            count      = 0
            while count < packet_len:
                count += self.send( result[count:packet_len] )
                
            print "sent data, size:" + str(len(result))
            if len(result) > 256:
                print "data:" + result[0:64] + "..."
                print "..." + result[len(result)-64:len(result)]
            
            if last_job == True:
                self.close()
                exit('TIMEOUT')
                

        else:
            print "received additional data: " + data
            

    def handle_read(self):

        data            = self.recv(262144)
        self.abort      = False
        
        # print "raw read of:"+data+":end raw"

        self.save_bytes = self.save_bytes + data
        
        while len(self.save_bytes) != 0 :

            # left-over bytes after the seperator are saved to save_bytes.
            [data, sep, self.save_bytes] = self.save_bytes.partition('PKT_SEP')
 
            # if there was a seperator, then process the line 
            if len(sep) != 0:
                self.process_packet(data.lstrip('\n')) ##the separator card may also include a newline.
            else:
                # otherwise, the packet fragment stays in self.save_bytes
                # for next time
                self.save_bytes = data 
                return
       
       
       
