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

# Network
import asyncore
import socket

# Calculation
import random

# Date and Time
import datetime as dt
import time

# Parsing
import re
import ConfigParser
import ast

# System
import os
import sys
import shutil
import threading

reldir = os.path.dirname(__file__)

if not reldir:
    reldir = '.'

# Append paths
sys.path.append(reldir + '/ffs')
sys.path.append(reldir + '/spres')
sys.path.append(reldir + '/nsffs')

# Logging
import logging

# Formatting
import concolors as cc

# FRESHS
import clienthandler
import auto_interfaces
import ghosting

####Helper class, roughly speaking an enumerator of algorithms available ####
class sampling_algorithm:
    FFS      = 0
    SPRES    = 1
    NSFFS    = 2
    NUM_ALGS = 3


#### MAIN SERVER CLASS ####
class server(asyncore.dispatcher):
    def __init__(self, timestamp = 'auto', configfile_name='auto'):
        
        # Logging        
        logging.basicConfig(level=logging.INFO)
        self.logger_freshs = logging.getLogger('freshs')

        # Set global timestamp / set dbload if timestamp is given
        self.timestamp = self.get_timestamp(timestamp)
        
       
        # Read the configfile
        self.read_config(configfile_name)

        self.logger_freshs.addHandler(logging.FileHandler(self.folder_log + self.timestamp +\
                        '_freshs.log', mode='a', encoding=None, delay=False))

        # Show message of the day
        self.show_motd()

        # create files for output
        self.create_outfiles()

        # global variables which can be used in all algorithms

        self.clients = []               # array for handling clients
        self.clientnames = []           # array for handling client names
        self.ghost_clients = {}         # dict for handling pre-runs (ghosts)
        self.ghostnames = []            # array for storing ghost names
        self.explorer_clients = {}      # dict for clients which are currently exploring the phase space
        self.idle_clients = []          # array for idle clients
        self.idlenames = []             # array for storing the names of idle clients
        self.console_clients = []       # array to handle management console clients
        self.client_runtime = {}        # dict for saving the clients' runtimes
        self.last_seen = {}             # dict for saving the timestamp when client was last seen

        # TODO: algorithmspecific ?
        self.M_0_runs=[]                # desired number of points
        self.run_count = []             # count number of runs to decide if more jobs are necessary
        self.M_0 = []                   # number of launched runs per interface

        self.disable_runs = False


        # Seed the RNG
        self.set_seed()

        # Initialize Interfaces # TODO: algorithmspecific
        self.A = self.configfile.getfloat('hypersurfaces', 'borderA')  # starting region
        self.B = self.configfile.getfloat('hypersurfaces', 'borderB')  # target region
        self.lambdas = [self.A]                             # interface variable

        self.fill_lambdas()
        
        self.nohs = self.noi - 1

# ----------------------------------------------------------------------------------------------------------------
# begin
        ###init a sampling control class to handle the actual algorithm
        if self.algo_name == 'ffs':
            from ffs_sampling_control   import ffs_sampling_control
            self.algorithm     = sampling_algorithm.FFS
            self.ffs_control   = ffs_sampling_control( self )
            self.create_dbs()

        elif self.algo_name == 'spres':
            from spres_sampling_control import spres_sampling_control
            dirList=os.listdir(self.folder_db)
            self.logger_freshs.info(cc.c_green + 'here, listing dir: ' +\
                            self.folder_db + ' gives: '+ str(dirList)+cc.reset)


            self.algorithm         = sampling_algorithm.SPRES
            self.absorb_at_B                = 0
            self.test_absorb_at_B_after_bin = 0
            self.spres_control = spres_sampling_control( self )  
            self.create_dbs()


        elif self.algo_name == 'nsffs':
            from nsffs_sampling_control import nsffs_sampling_control
            self.algorithm     = sampling_algorithm.NSFFS
            self.nsffs_control = nsffs_sampling_control( self )
            self.create_dbs()

        else:
            self.logger_freshs.info(cc.c_red + 'Error! Sampling Algorithm name not recognised: ' + algo_name + cc.reset)
            self.create_dbs()

# end
# ----------------------------------------------------------------------------------------------------------------
        
        ## some initial setup
        if self.algorithm == sampling_algorithm.SPRES:
            if not self.dbload:
                ##save a null initial configuration
                self.storepoints.add_point_ij( 0, [0.0, 0.0], ['escape'], \
                                                 0, 0, 0, 0, 0, 0, 0, 0)

                self.storepoints.commit()
                if self.configfile.getint('spres_control','use_multDB') > 0:
                    self.storepoints.increment_active_db(self.epoch + self.tau)
                else:
                    self.storepoints.increment_active_table(self.epoch + self.tau)
            else:
                self.spres_control.load_points(self.epoch)
                

        # Communication: create socket and listen on specific port
        self.open_socket()

        #self.listen(1)


        # Start sampling module
        if self.algorithm == sampling_algorithm.FFS :
            self.logger_freshs.info(cc.c_green + cc.bold + 'Loading module FFS ' + cc.reset)
            self.ai     = auto_interfaces.auto_interfaces(self)
            self.ghosts = ghosting.ghosting(self)
            self.ffs_control.launch_jobs()
            self.periodic_check()
        elif self.algorithm == sampling_algorithm.SPRES :
            self.logger_freshs.info(cc.c_green + cc.bold + 'Loading module S-PRES ' + cc.reset)
            self.spres_control.launch_jobs()
        elif self.algorithm == sampling_algorithm.NSFFS :
            self.logger_freshs.info(cc.c_green + cc.bold + 'Loading module NS-FFS ' + cc.reset)
            self.nsffs_control.launch_jobs()

        # Ready to go!
        self.logger_freshs.info(cc.c_magenta + 'Listening on port ' + str(self.port) + cc.reset)
        self.logger_freshs.info(cc.c_blue + cc.bold + 'Ready. Waiting for clients.' + cc.reset)

# -------------------------------------------------------------------------------------------------

    # create listening socket
    def open_socket(self):
        asyncore.dispatcher.__init__(self)
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        try:
            self.bind(('', self.port))
        except:
            self.logger_freshs.info(cc.c_red + 'Error! Could not open/bind to socket on port: ' + str(self.port) + cc.reset)
            self.logger_freshs.info(cc.c_red + 'Error! Port in use? ' + str(self.port) + cc.reset)
            quit()
            
        self.listen(1)

# -------------------------------------------------------------------------------------------------

    # check if timestamp was given, else return one
    def get_timestamp(self,timestamp):

        self.logger_freshs.debug(cc.c_magenta + 'timestamp: ' + timestamp + cc.reset)

        if timestamp == 'auto':
            timestamp = re.sub('\..*$','',re.sub(' ','_',re.sub(':','-',str(dt.datetime.now()))))
            self.dbload = False
        else:
            # Init from database
            self.dbload = True

        self.logger_freshs.info(cc.c_magenta + 'timestamp now: ' + timestamp + cc.reset)

        return timestamp

# -------------------------------------------------------------------------------------------------

    # create filenames for output
    def create_outfiles(self):
    
        self.outfile    = self.folder_out + self.timestamp + '_rates.dat'
        self.lamfile    = self.folder_out + self.timestamp + '_lambdas.conf'
        self.vecfile    = self.folder_out + self.timestamp + '_stateVec.dat'
        self.matfile    = self.folder_out + self.timestamp + '_transMat.dat'

        try:
            os.remove(self.folder_out + 'lambdas.conf')
            os.remove(self.folder_out + 'rates.dat')
        except:
            pass
            
        try:
            os.symlink(self.timestamp + '_lambdas.conf', self.folder_out + 'lambdas.conf')
            os.symlink(self.timestamp + '_rates.dat', self.folder_out + 'rates.dat')
        except:
            pass

# -------------------------------------------------------------------------------------------------

    # create databases for data storage
    def create_dbs(self):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': create_dbs' + cc.reset)
    
        if self.algo_name == 'ffs':

            import configpoints

            # create instance of DB for configpoint-handling / open existing DB
            confdbfile = self.timestamp + '_configpoints.sqlite'
            self.storepoints=configpoints.configpoints(self, self.folder_db + confdbfile)
            
            # create instance of DB for pre-runs:
            ghostdbfile = self.timestamp + '_ghost.sqlite'
            self.ghostpoints=configpoints.configpoints(self, self.folder_db + ghostdbfile)

            # Symlink DBs
            try:
                os.remove(self.folder_db + 'configpoints.sqlite')
                os.remove(self.folder_db + 'ghostpoints.sqlite')
            except:
                pass
            try:
                os.symlink(confdbfile, self.folder_db + 'configpoints.sqlite')
                os.symlink(ghostdbfile, self.folder_db + 'ghostpoints.sqlite')
            except:
                pass

        elif self.algo_name == 'spres':  

            ##open or create a DB with the correct timepoint
            confdbfile = self.timestamp + '_configpoints.sqlite'

            if self.configfile.getint('spres_control','use_multDB') > 0:
                import configpoints_spres_multDB
                self.storepoints=configpoints_spres_multDB.configpoints(self,  self.folder_db + confdbfile, self.epoch)

            else:
                import configpoints_spres
                self.storepoints=configpoints_spres.configpoints(self,  self.folder_db + confdbfile)


        elif self.algo_name == 'nsffs':
        
            import configpoints

            # create instance of DB for configpoint-handling / open existing DB
            confdbfile = self.timestamp + '_configpoints.sqlite'
            self.storepoints=configpoints.configpoints(self, self.folder_db + confdbfile)


# -------------------------------------------------------------------------------------------------

    # read the server's config file
    def read_config(self,configfile_name):

        self.logger_freshs.debug(cc.c_magenta + __name__ + ': read_config' + cc.reset)

        cfgcpflag = 'nop'

        # read server's config file, make timestamp backup
        self.configfile = ConfigParser.RawConfigParser()
	try:
	    if configfile_name == 'auto':
		configfile_name = self.timestamp + '_server.conf'
		if self.dbload:
		    self.configfile.read(configfile_name)
		else:
		    configfile_name = reldir + '/../server-sample-ffs.conf'
		    self.logger_freshs.info(cc.c_green + 'Loading the SAMPLE FFS CONFIGURATION file.' + cc.reset)
		    self.configfile.read(configfile_name)
		    cfgcpflag = 'samplecfg'
	    else:
		self.configfile.read( configfile_name )
		cfgcpflag = 'bycfgname'
	except:
	    print("Failed to read config file:"+configfile_name)
	    pass


        # FOLDERS
        if self.configfile.has_option('general', 'folder_out'):
            self.folder_out = re.sub('/$','', str(self.configfile.get('general', 'folder_out')) )
        else:
            self.folder_out = 'OUTPUT'
        if self.configfile.has_option('general', 'folder_conf'):
            self.folder_conf = re.sub('/$','', str(self.configfile.get('general', 'folder_conf')) )
        else:
            self.folder_conf = 'CONF'
        if self.configfile.has_option('general', 'folder_db'):
            self.folder_db = re.sub('/$','', str(self.configfile.get('general', 'folder_db')) )
        else:
            self.folder_db = 'DB'
        if self.configfile.has_option('general', 'folder_log'):
            self.folder_log = re.sub('/$','', str(self.configfile.get('general', 'folder_log')) )
        else:
            self.folder_log = 'LOG' 

        self.create_filestruct()

        # copy conf-file with timestamp, if not a resume run or new run
        if cfgcpflag == 'samplecfg':
            shutil.copy(reldir + '/../server-sample-ffs.conf', self.folder_conf + self.timestamp + '_server.conf')
        elif cfgcpflag == 'bycfgname':
            try:
                shutil.copy(configfile_name, self.folder_conf + self.timestamp + '_server.conf')
            except:
                self.logger_freshs.debug(cc.c_magenta + 'Not copying config, exists probably.' + cc.reset)

        # Choose the sampling algorithm
        self.logger_freshs.debug(cc.c_magenta + 'Server: repeat, Config file name is:' +\
                                                                      configfile_name + cc.reset)
        self.algo_name = self.configfile.get('general', 'algo_name').lower()

        if self.configfile.has_option('general', 'check_alive'):
            self.check_alive = self.configfile.getint('general', 'check_alive')
        else:
            self.check_alive = 0
        if self.configfile.has_option('general', 'kick_absent_clients'):
            self.kick_absent_clients = self.configfile.getint('general', 'kick_absent_clients')
        else:
            self.kick_absent_clients = 0

        self.allow_race = True
        if self.configfile.has_option('general', 'allow_race'):
            if self.configfile.getboolean('general', 'allow_race') == False:
                self.allow_race = False
                self.logger_freshs.info(cc.c_red +\
                     'Warning: allow_race is set False: Stops race conditions for determinism but may hurt speed.' +\
                 cc.reset)

        if self.configfile.has_option('general', 'test_rc_every'):
            self.test_rc_every = self.configfile.getint('general', 'test_rc_every')
        else:
            self.test_rc_every = 1
      
        self.auto_interfaces = 0 
	if self.configfile.has_section('auto_interfaces'): 
            if self.configfile.has_option('auto_interfaces', 'auto_interfaces'):
                self.auto_interfaces = self.configfile.getint('auto_interfaces', 'auto_interfaces')
    
        # use ghosts
        if self.configfile.has_option('general', 'use_ghosts'):
            self.use_ghosts = self.configfile.getint('general', 'use_ghosts')
        else:
            self.use_ghosts = 0

        if self.configfile.has_option('general', 't_infocheck'):
            self.t_infocheck = self.configfile.getfloat('general', 't_infocheck')
        else:
            self.t_infocheck = 30.0


        # do we hit the filesystem or not?
        if self.configfile.has_option('general', 'clients_use_filesystem'):
            self.clients_use_fs = self.configfile.getboolean('general', 'clients_use_filesystem')
        else:
            self.clients_use_fs = False
        
        self.port = self.configfile.getint('general', 'listenport')

        # user-defined message string
        if self.configfile.has_option('general', 'user_msg'):
            self.user_msg = str(self.configfile.get('general', 'user_msg'))
            try:
                self.user_msg_dict = eval('{ ' + self.user_msg + ' }')
            except:
                self.logger_freshs.warn(cc.c_red + 'User-defined message ' + self.user_msg + \
                                        ' in configfile has errors and will not be used.' + cc.reset)
                self.user_msg = ''
        else:
            self.user_msg = '' 

        ##Algo-specific setup
        if self.algo_name == "spres":
            self.tau               = self.configfile.getint('spres_control', 'tau')
            if self.configfile.has_option('spres_control', 'test_absorb_at_B_every'):
                self.absorb_at_B  =\
                  self.configfile.getint('spres_control', 'test_absorb_at_B_every')
            if self.configfile.has_option('spres_control', 'test_absorb_at_B_after_bin'):
                self.test_absorb_at_B_after_bin =\
                  self.configfile.getint('spres_control', 'test_absorb_at_B_after_bin')
                self.replace_flux_at_A = True
            if self.configfile.has_option('spres_control', 'replace_flux_at_A'):
                self.replace_flux_at_A =\
                   self.configfile.getboolean('spres_control', 'replace_flux_at_A')

# -------------------------------------------------------------------------------------------------

    # create folders if they do not exist.
    def create_filestruct(self):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': create_filestruct' + cc.reset)
    
        # Create directories if they do not exist
        if not os.path.exists(self.folder_out):
            os.makedirs(self.folder_out)
        if not os.path.exists(self.folder_conf):
            os.makedirs(self.folder_conf)
        if not os.path.exists(self.folder_db):
            os.makedirs(self.folder_db)
        if not os.path.exists(self.folder_log):
            os.makedirs(self.folder_log)

        self.folder_out  += '/'
        self.folder_conf += '/'
        self.folder_db   += '/'
        self.folder_log  += '/'

        self.logger_freshs.debug(cc.c_magenta + 'Found/Created folders: '+\
                                    self.folder_out + " " + self.folder_conf + " " + self.folder_db + " " + self.folder_log + cc.reset)

# -------------------------------------------------------------------------------------------------

    # Fill lambdas list. # TODO: algorithmspecific
    def fill_lambdas(self):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': fill_lambdas' + cc.reset)
    
        lambdaload = True
        self.noi = 1
        while lambdaload:
            try:
                self.lambdas.append(self.configfile.getfloat('hypersurfaces', 'lambda'+str(self.noi)))
                self.noi += 1
            except:
                lambdaload = False
                
        self.lambdas.append(self.B)

# -------------------------------------------------------------------------------------------------

    # show message of the day
    def show_motd(self):
        #os.system('clear')
        print   ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \n' + \
                '  This is the Flexible Rare Event Sampling Harness System  \n' + \
                '         ______ _____  ______  _____ _    _  _____         \n' + \
                '        |  ____|  __ \|  ____|/ ____| |  | |/ ____|        \n' + \
                '        | |__  | |__) | |__  | (___ | |__| | (___          \n' + \
                '        |  __| |  _  /|  __|  \___ \|  __  |\___ \         \n' + \
                '        | |    | | \ \| |____ ____) | |  | |____) |        \n' + \
                '        |_|    |_|  \_\______|_____/|_|  |_|_____/         \n' + \
                ' --------------------------------------------------------- \n' + \
                ' (c) 2011,2012,2013\n' + \
                ' The FRESH System\n' + \
                ' Uni Stuttgart, Uni Luxembourg\n' + \
                '\n' + \
                ' FRESHS is distributed in the hope that it will be useful, \n' + \
                ' but WITHOUT ANY WARRANTY; without even the implied warranty of, \n' + \
                ' MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.\n' + \
                ' For more information and licensing see COPYING\n' + \
                ' ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ \n' + \
                cc.reset

# -------------------------------------------------------------------------------------------------

    # This function calls itself recursively after a specific time
    def periodic_check(self):
        # WARN: DO NOT USE THE DATABASE IN THIS THREADED FUNCTION
        self.print_status()
        self.logger_freshs.debug(cc.c_magenta + 'Runcount: ' + str(self.run_count) + cc.reset)
        self.logger_freshs.debug(cc.c_magenta + 'Clients: ' + str(self.clientnames) + cc.reset)
        if self.check_alive > 0:
            # Check if clients are alive (one after another)
            # if not, send new job, if not ok, disconnect
            # copy dict, because size can change during this iteration
            last_seen_tmp = dict(self.last_seen)
            for client in last_seen_tmp:
                timespan = int(time.time() - self.last_seen[client])
                if timespan > self.check_alive:
                    self.logger_freshs.warn(cc.c_red + 'Client ' + str(client.name) + ' was last seen ' + \
                                            str(timespan) + ' seconds ago.' + cc.reset)
                    if self.kick_absent_clients > 0:
                        self.logger_freshs.warn(cc.c_red + 'Disconnecting ' + str(client.name) + ' because of not reporting something since ' + \
                                            str(timespan) + ' seconds.' + cc.reset)
                        self.deregisterClient(client)
                        client.close()

        if len(self.clients) > 0 and (len(self.ghost_clients) + len(self.idle_clients)) == len(self.clients):
           self.logger_freshs.warn(cc.c_red + 'DANG! ALL CLIENTS ARE ABSENT...' + cc.reset)
        self.periodic = threading.Timer(self.t_infocheck, self.periodic_check)
        self.periodic.daemon=True
        self.periodic.start()

# -------------------------------------------------------------------------------------------------

    # set seed for master RNG
    def set_seed(self):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': set_seed' + cc.reset)
    
        try: 
            master_seed = self.configfile.getint('general', 'rng_seed')
        except:
            master_seed = int(time.time())
            self.logger_freshs.info(cc.c_green + 'Using seed from time.' + cc.reset)

        random.seed(master_seed)
        
        self.myRandMax = pow(2,31) ##do not want to have a system-dependent RAND_MAX.
        self.logger_freshs.info(cc.c_green + 'Master RNG seed is: ' + str(master_seed)\
                           + cc.reset)
                
    ## asyncore handlers
# -------------------------------------------------------------------------------------------------

    # Accept connection from client
    def handle_accept(self):
        sock, addr = self.accept()
        # index client
        ready = 0
        i = 0
        name = ''
        while not ready:
            name_tmp = "client%04d" % i
            if name_tmp not in self.clientnames and not ready:
                self.clientnames.append(name_tmp)
                name = name_tmp
                ready = 1
            i += 1
        if name == '':
            self.logger_freshs.warn(cc.c_red + 'Failed giving name to client! Client not accepted.' + cc.reset)
        else:
            if self.algorithm == sampling_algorithm.FFS:
                last_received_count = max([self.storepoints.return_last_received_count(name), self.ghostpoints.return_last_received_count(name)])
            else:
                last_received_count = self.storepoints.return_last_received_count(name)
            self.logger_freshs.debug(cc.c_magenta + 'Last received count of ' + name + ' is ' + str(last_received_count) + cc.reset)
            clienthandler.ClientHandler(self,sock,addr,name,last_received_count)
            self.logger_freshs.info(cc.c_blue + name + ' connected.' + cc.reset)

        return

# -------------------------------------------------------------------------------------------------

    # close handle
    def handle_close(self):
        self.close()
        
# -------------------------------------------------------------------------------------------------

    # print status. This could be called by a periodic threading function
    def print_status(self):
        try:
            if self.algorithm == sampling_algorithm.FFS:
                if self.act_lambda == 0:
                    self.logger_freshs.info(cc.c_magenta + cc.bold \
                    + 'Clients: ' + str(len(self.clients)) + ', Idle: ' + str(len(self.idle_clients)) \
                    + ', Ghosts: ' + str(len(self.ghost_clients)) + ', Explorers: ' + str(len(self.explorer_clients)) \
                    + ', ctime: ' + str(self.ctime) \
                    + cc.reset)
                else:
                    self.logger_freshs.info(cc.c_magenta + cc.bold \
                    + 'Clients: ' + str(len(self.clients)) + ', Idle: ' + str(len(self.idle_clients)) \
                    + ', Ghosts: ' + str(len(self.ghost_clients)) + ', Explorers: ' + str(len(self.explorer_clients)) \
                    + ', ctime: ' + str(self.ctime) \
                    + ', run_count: ' + str(self.run_count[self.act_lambda]) \
                    + ', calc_saved: ' + str(self.ghostcalcsave) \
                    + ', time_saved [s]: ' + str(self.ghosttimesave) \
                    + cc.reset)

            elif self.algorithm == sampling_algorithm.SPRES:
                self.logger_freshs.info(cc.c_magenta + 'Clients (' + str(len(self.clientnames))+ '): ' + str(self.clientnames) \
                + ', idle (' + str(len(self.idlenames))+ '): ' + str(self.idlenames) \
                + cc.reset)

            elif self.algorithm == sampling_algorithm.NSFFS:
                self.logger_freshs.info(cc.c_magenta + 'Clients (' + str(len(self.clientnames))+ '): ' + str(self.clientnames) \
                + ', ghosts (' + str(len(self.ghostnames)) + '): ' + str(self.ghostnames) \
                + ', idle (' + str(len(self.idlenames))+ '): ' + str(self.idlenames) \
                + ', ghostruns_in_db: ' + str(self.ghostpoints.return_nop(self.act_lambda)) \
                + cc.reset)
        except:
            self.logger_freshs.warn(cc.c_red + 'Could not print status information.' + cc.reset)

# -------------------------------------------------------------------------------------------------

    # check if calculation job is available
    def check_for_job(self, client):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': check_for_job' + cc.reset)
    
        if not self.disable_runs:
            if self.algorithm == sampling_algorithm.FFS:
                fsc = self.ffs_control

                client.remove_from_ghost()
                client.remove_from_explorer()
                
                if fsc.start_job(client):
                    # starting real run was successful
                    pass
                # If exploring mode
                elif self.ai.exmode:
                    # try to start explorer                
                    if not self.ai.start_explorer(client):
                        # no exploring run on this lambda left, start parallel run
                        if self.ai.add_parallel_lambda():
                            self.check_for_job(client)
                        else:
                            if self.ghosts.ghost_possible():
                                client.start_ghost_job2()
                            else:
                                # Last possibility: let client wait
                                if client not in self.idle_clients:
                                    client.start_job_wait()

                # Start other jobs
                else:
                    # ghost check switches on exploring mode if no lambda is known
                    if self.ghosts.ghost_possible():
                        if client not in self.ghost_clients:
                            client.start_ghost_job2()
                    elif self.ai.exmode:
                        # ghost lookup could have activated exmode. Recursion.
                        self.check_for_job(client)
                    else:
                        # Last possibility: let client wait
                        if client not in self.idle_clients:
                            client.start_job_wait()

            elif self.algorithm == sampling_algorithm.SPRES:
                if False == self.spres_control.try_launch_job3(client):
                    self.logger_freshs.debug(cc.c_blue + 'asking client: '+client.name+' to wait.'+cc.reset)
                    client.start_job_wait()
            elif self.algorithm == sampling_algorithm.NSFFS:
                if False == self.nsffs_control.try_launch_job(client):
                    self.logger_freshs.debug(cc.c_blue + 'asking client: '+client.name+' to wait.'+cc.reset)
                    client.start_job_wait()
            else:
                self.logger_freshs.error(cc.c_red + 'Error, sampling algorithm not recognised' + cc.reset)


# -------------------------------------------------------------------------------------------------

    # register client and add to client array, send timestamp, check for job
    def registerClient(self, client):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': register_client' + cc.reset)
    
        self.clients.append(client)

        # Send server's timestamp to client
        client.long_send('timestamp: ' + self.timestamp + 'PKT_SEP\n')

        self.print_status()

        self.check_for_job(client)

# -------------------------------------------------------------------------------------------------

    # clean client from all arrays (e.g. on disconnect) 
    def cleanup_client(self, client):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': cleanup_client' + cc.reset)
    
        if client.name in self.clientnames:
            self.clientnames.remove(client.name)
        if client.name in self.ghostnames:
            self.ghostnames.remove(client.name)
        if client.name in self.idlenames:
            self.idlenames.remove(client.name)
        if client in self.clients:
            self.clients.remove(client)
        if client in self.last_seen:
            self.last_seen.pop(client)
        if client in self.ghost_clients:
            self.ghost_clients.pop(client)
        if client in self.idle_clients:
            self.idle_clients.remove(client)
        if client in self.console_clients:
            self.console_clients.remove(client)
        if client in self.explorer_clients:
            self.explorer_clients.pop(client)

        # algorithm specific cleanup
        if self.algorithm == sampling_algorithm.FFS:
            if client in self.ffs_control.escape_skip_count:
                self.ffs_control.escape_skip_count.pop(client)

            client.remove_from_escape()

# -------------------------------------------------------------------------------------------------

    # deregister client, check run_count etc
    def deregisterClient(self, client):

        self.logger_freshs.debug(cc.c_magenta + __name__ + ': deregisterClient' + cc.reset)
    
        was_active2 = 0

        if not self.disable_runs:

            # commit data in database
            try:
                self.storepoints.commit()
            except:
                self.logger_freshs.info(cc.c_green + 'Notice: Could not commit last state of configpoint DB during client disconnect.' + cc.reset )

            if self.algorithm == sampling_algorithm.FFS:
                try:
                    self.ghostpoints.commit()
                except:
                    self.logger_freshs.info(cc.c_green + 'Notice: Could not commit last state of ghostpoint DB during client disconnect.' + cc.reset )

            if self.is_active(client) or self.is_explorer(client):

                if self.algorithm == sampling_algorithm.SPRES:
                    self.logger_freshs.debug(cc.c_blue + 'Client ' + str(client.name) +\
                                                             ' at lambda ' + str(self.act_lambda) + cc.reset )
                    try:
                        self.run_count[self.act_lambda] -= 1
                        self.M_0[self.act_lambda] -= 1
                    except:
                        self.logger_freshs.warn(cc.c_red + 'Could not decrease run_count...' + cc.reset )
                else:
                    try:
                        self.ghostpoints.commit()
                    except:
                        self.logger_freshs.info(cc.c_green + 'Notice: Could not commit last state of ghostpoint DB during client disconnect.' + cc.reset )
                    if client not in self.explorer_clients:
                        # client was active. Need another client to resume this job
                        was_active2 = 1
                        try:
                            if self.run_count[self.act_lambda] > 0:
                                client.decr_runcount(self.act_lambda)
                                self.M_0[self.act_lambda] -= 1
                            #if self.storepoints.return_nop(self.act_lambda) > 0:
                            #    self.storepoints.update_M_0(-1)

                        except Exception as exc:
                            self.logger_freshs.warn(cc.c_red + 'Could not decrease run_count, ' + str(exc) + cc.reset )
                    else:
                        # get index on which explorer was running
                        
                        if self.ai.auto_histo:
                            self.ai.ex_launched[0] -= 1
                        else:
                            ex_ind = self.ai.cemlti( self.explorer_clients[client] )
                            try:
                                if self.ai.ex_launched[ex_ind] > 0:
                                    self.ai.ex_launched[ex_ind] -= 1
                            except:
                                self.logger_freshs.warn(cc.c_red + 'Could not decrease run_count of explorer array, index ' + \
                                                        str(ex_ind) + cc.reset )
                    
                    self.logger_freshs.info(cc.c_blue + str(client.name) + \
                                            ' deregistered, runcount adjusted.' + cc.reset)

            self.print_status()

        self.cleanup_client(client)



        # job2: start idle client replacing the disconnected client
        if was_active2 and not self.disable_runs:
            done = 0
            for client in self.clients:
                if (self.is_idle(client)) and (not done):
                    done = 1
                    self.check_for_job(client)
                else:
                    pass

# -------------------------------------------------------------------------------------------------

    def is_active(self,client):
        # if client is in self.clients, a job is running and runcount must be observed!
        if (client not in self.idle_clients) and (client not in self.ghost_clients) and \
           (client not in self.explorer_clients) and (client in self.clients):
            return True
        else:
            return False

# -------------------------------------------------------------------------------------------------
    
    def is_idle(self,client):
        if (client in self.idle_clients) and (client not in self.ghost_clients) and \
           (client not in self.explorer_clients) and (client in self.clients):
            return True
        else:
            return False

# -------------------------------------------------------------------------------------------------
    
    def is_ghost(self,client):
        if (client not in self.idle_clients) and (client not in self.explorer_clients) and \
           (client in self.ghost_clients) and (client in self.clients):
            return True
        else:
            return False

# -------------------------------------------------------------------------------------------------
            
    def is_explorer(self,client):
        if (client not in self.idle_clients) and (client in self.explorer_clients) and \
           (client not in self.ghost_clients) and (client in self.clients):
            return True
        else:
            return False

# -------------------------------------------------------------------------------------------------

    def active_clients(self):
        return len(self.clients) - len(self.idle_clients) - len(self.ghost_clients) - len(self.explorer_clients)

# -------------------------------------------------------------------------------------------------

    # Analyze the data received from a client
    def analyze_recv(self, data, client, runid):

        self.logger_freshs.debug(cc.c_magenta + __name__ + ': analyze_recv' + cc.reset)

        # remove carriage returns and line feeds
        data = data.strip()

        if (client not in self.clients) and (client not in self.console_clients):
            # check if client says 'hello'
            if "ffs client v1" in data:
                self.registerClient(client)
            elif "management client v1" in data:
                self.console_clients.append(client)
                self.logger_freshs.info(cc.c_blue + str(client.name) + ' identified as management client.' + cc.reset)
            else:
                self.logger_freshs.info(cc.c_blue + cc.bold + 'Client ' + str(client.name) + \
                'disconnected, data not accepted (wrong protocol version?).' + cc.reset)
                client.close()
            return

        # Save the time when this client was last seen
        self.last_seen[client] = time.time()
    
        if "request_alive" in data:
            self.last_seen[str(client)] = time.time()
            client.answer_alive()
            return

    
        # Check if client sent result
        if "\"jobtype\":" in data:
            try:
                # perhaps parsing would be better?.
                #ddata = eval(data,{'__builtins__':{}},{'True': True, 'False': False})
                ddata = ast.literal_eval(data)
                #ddata = eval(data)

            except:
                self.logger_freshs.info(cc.c_red + 'Server: Warning! Could not parse data packet: ' + data + cc.reset) 
                self.logger_freshs.info(cc.c_red + 'Server: Warning! Dropping packet.' + cc.reset) 
                return

            self.logger_freshs.debug(cc.c_blue + 'Server: Analysing received job, giving id:' + str(runid) + cc.reset) 

            # Analyze results
            if self.algorithm == sampling_algorithm.FFS:
                # if auto_interfaces is on, pass results to this module.
                if client in self.explorer_clients:
                    self.logger_freshs.debug(cc.c_blue + 'Sending results to explorer module.' + cc.reset) 
                    self.ai.parse_message(data, ddata, client, runid)
                elif client in self.ghost_clients:
                    self.logger_freshs.debug(cc.c_blue + 'Sending results to ghost module.' + cc.reset) 
                    self.ghosts.parse_message(data, ddata, client, runid)
                else:
                    self.logger_freshs.debug(cc.c_blue + 'Sending results to ffs module.' + cc.reset) 
                    self.ffs_control.parse_message(data, ddata, client, runid)
                                
            else:
                ## Result 3: Fixed tau
                if ddata['jobtype'] == 3:
                    
                    ssc = self.spres_control
                    
                    ##process the incoming info
                    ssc.analyze_job3_success(client, ddata, runid)
                    ##del ddata 
                    ##del data

                    ##client should be ready for another job
                    if client.timeout_warned == False:
                        while ssc.try_launch_job3( client ) == False:
                            if ssc.test_epoch_complete():
                                self.logger_freshs.info(cc.c_red + 'advancing epoch'+cc.reset)
                                ssc.advance_epoch() 

                                self.logger_freshs.debug(cc.c_blue + 'Epoch up, waiters are: '+cc.reset)
                                for idle_client in self.idle_clients:
                                    self.logger_freshs.info(cc.c_magenta+ idle_client.name + cc.reset )

                                self.start_idle_clients()
                            else:
                                self.logger_freshs.debug(cc.c_blue + 'blocking wait for epoch'+cc.reset)
                                self.logger_freshs.debug(cc.c_blue + 'asking client: '+client.name+' to wait.'+cc.reset)
                                client.start_job_wait()
                                return
                    else:
                        self.logger_freshs.info(cc.c_red + \
                             'Client has announced that it is retiring.'+cc.reset)
                        self.deregisterClient( client )
                        self.logger_freshs.info(cc.c_red + \
                             'Have: '+str(len(self.clients)) + ' remaining.' + cc.reset)
                    
# -------------------------------------------------------------------------------------------------

    # Start idle clients
    def start_idle_clients(self):

        self.logger_freshs.debug(cc.c_magenta + __name__ + ': start_idle_clients' + cc.reset)

        ##loop backwards over a list if you are deleting values
        ##...otherwise the position of list items changes durig the iteration 
        ##...and python misses some of them.
        for idle_client in self.idle_clients[::-1]:

            if self.algorithm == sampling_algorithm.FFS:

                self.check_for_job(idle_client)

            elif self.algorithm == sampling_algorithm.SPRES:
                
                if not self.spres_control.try_launch_job3( idle_client ):
                    self.logger_freshs.info(cc.c_red +\
                           'Could not launch job on idle client:' +\
                            idle_client.name + cc.reset)
                else:
                    self.logger_freshs.info(cc.c_red +\
                           'Launched job on idle client:' +\
                            idle_client.name + cc.reset)
                
                    
# -------------------------------------------------------------------------------------------------

    # End of simulation. Here the results are vacuumed and shampooed. Then the server exits.
    def end_simulation(self):
    
        self.logger_freshs.debug(cc.c_magenta + __name__ + ': end_simulation' + cc.reset)
    
        self.disable_runs = True
        # commit data in database
        self.storepoints.commit()
        self.ghostpoints.commit()
        
        if self.algorithm == sampling_algorithm.FFS:
            self.ffs_control.arrived_in_B()
        
        # Disable timer
        try:
            self.periodic.cancel()
        except:
            pass
        # Quit clients
        for client in self.clients:
            client.handle_close()
        # Quit server
        self.handle_close()
        asyncore.dispatcher.close(self)
        self.print_status()
        exit(0)

# -------------------------------------------------------------------------------------------------

 
