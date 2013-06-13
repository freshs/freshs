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

# Formatting
import concolors as cc

# Time measurements
import time

# To generate RNG seeds for individual client jobs
import random

# UUID
import uuid

#### CLASS FOR HANDLING THE CLIENTS ####
class ClientHandler(asyncore.dispatcher):
  
## Init ##
    def __init__(self, server, sock, addr, name, received_count=0):
        asyncore.dispatcher.__init__(self, sock=sock)
        self.name = name
        self.sock = sock
        self.addr = addr
        self.ghostcount = 0

        # send name to client
        self.long_send(name + 'PKT_SEP\n')
        self.server = server

        #self.server.registerClient(self)
        self.msg            = []
        self.save_bytes     = ""
        self.received_count = received_count

        #
        self.timeout_warned = False

        return

## Socket handling ##
    def handle_write(self):
        data=self.msg.pop()

        self.long_send(data)

    def handle_read(self):
        
        ##get some data from the socket 
        self.save_bytes = self.save_bytes + self.recv(262144) 

        while len(self.save_bytes) != 0 :

            ##left-over bytes after the seperator are saved to save_bytes.
            [line, sep, self.save_bytes] = self.save_bytes.partition('PKT_SEP')
 
            ##if there was a seperator, then process the line 
            if len(sep) != 0:
                [line, sep, self.save_bytes] = line.partition('WARN_TIMEOUT') 
                if len(sep) != 0:
                    self.timeout_warned = True

                self.received_count = self.received_count + 1
                runid               = self.name + "_" + str(self.received_count)

                self.server.logger_freshs.debug(cc.c_green + 'Incoming data packet: ' +\
                                                          str(runid) +\
                                                          cc.reset)

                self.server.analyze_recv( line.strip(), self, runid ) 
            else:
                ##otherwise, the packet fragment stays in self.save_bytes
                ##for next time
                self.save_bytes = line
                return


    def handle_close(self):
        self.server.deregisterClient(self)
        self.close()
        
 
    def writable(self):
        response = bool(self.msg)
        return response

## Client functions ##

    def add_as_idle(self):
        ss = self.server
        #ss.logger_freshs.debug(cc.c_magenta + __name__ + ': add_as_idle' + cc.reset)
        if self not in ss.idle_clients:
            ss.idle_clients.append(self)
            ss.idlenames.append(self.name)
        self.remove_from_ghost()

    def add_as_ghost(self, ghostpoint):
        ss = self.server
        if self not in ss.ghost_clients:
            ss.ghost_clients[self] = ghostpoint
            if self.name not in ss.ghostnames:
                ss.ghostnames.append(self.name)
        self.remove_from_idle()

    def add_as_escape(self, escapepoint):
        ss = self.server
        ss.ffs_control.escape_clients[self] = escapepoint

    def remove_from_idle(self):
        ss = self.server
        if self in ss.idle_clients:
            ss.idle_clients.remove(self)
            ss.idlenames.remove(self.name)

    def remove_from_ghost(self):
        ss = self.server
        if self in ss.ghost_clients:
            ss.ghost_clients.pop(self)
            ss.ghostnames.remove(self.name)
            
    def remove_from_explorer(self):
        ss = self.server
        if self in ss.explorer_clients:
            ss.explorer_clients.pop(self)

    def remove_from_escape(self):
        ss = self.server
        if self in ss.ffs_control.escape_clients:
            ss.ffs_control.escape_clients.pop(self)
          
#    def find_client_by_key(self,key):
#        for client in self.server.clients:
#            if str(client) == key:
#                return client


    # Increase run_count and counter of launched runs
    def incr_runcount(self,lam):
        ss = self.server
        ss.M_0[lam] += 1

        if ss.storepoints.return_nop(lam) > 0:
            ss.storepoints.update_M_0(1)
        ss.run_count[lam] += 1

        ss.logger_freshs.debug(cc.c_magenta + self.name + ': Increasing runcount, lambda ' + str(lam) + cc.reset)
        ss.logger_freshs.debug(cc.c_magenta + 'Runcount: ' + str(ss.run_count) + cc.reset)

    def decr_runcount(self,lam):
        ss = self.server
        if ss.run_count[lam] >= 1:
            ss.run_count[lam] -= 1
            ss.logger_freshs.debug(cc.c_magenta + self.name + ': Decreasing runcount, lambda ' + str(lam) + cc.reset)
        ss.logger_freshs.debug(cc.c_magenta + 'Runcount: ' + str(ss.run_count) + cc.reset)


    # Return the composed message string consisting of system and user messages
    def compose_message(self, sysmsg):
        ss = self.server
        abort = False
        if ss.user_msg != '':
        # check system message keys against ss.user_msg_dict
            for tk in ss.user_msg_dict:
                if str(tk) in sysmsg:
                    abort = True
                    ss.logger_freshs.warn(cc.c_red + 'A key of usr_msg is already in the system message! Not appending.' + cc.reset)
                    
            if not abort:
                sysmsg += ", " + ss.user_msg

        # if key is not in string, add the message
        return "{" + sysmsg + "}PKT_SEP\n"

    # return uuid
    def get_uuid(self):
        return str(uuid.uuid4())

    def point_in_escape(self, point):
        ss = self.server
        for el in ss.ffs_control.escape_clients:
            if ss.ffs_control.escape_clients[el] == point:
                return True
        return False


# --------------------------------------------------------------------------
# FFS Escape flux
# --------------------------------------------------------------------------
    def start_job1(self, ex_ind=-1):
    
        ss = self.server
        
        self.remove_from_idle()
        self.remove_from_ghost()

        max_steps = 0

        newtrace = True

        rp_id = 'escape'

        last_escape_point = 'None'

        # choose a seed for the client RNG, using the server RNG
        client_seed = random.randint(0, self.server.myRandMax)

        if ex_ind == -1:
            # Normal case.
            next_interface = ss.lambdas[ss.act_lambda]
            current_lambda = ss.act_lambda
            
            ncpoints = ss.storepoints.return_nop(ss.act_lambda)
            
            # serial escape
            if ss.ffs_control.parallel_escape == 0:
                if ncpoints > 0:
                    last_escape_point, rp_id, rcval = ss.storepoints.return_most_recent_escape_point()
                    ss.logger_freshs.info(cc.c_green + 'Resuming job 1 on ' + str(self.name) + '.' + cc.reset)
                    self.add_as_escape(rp_id)
                    newtrace = False
                else:
                    ss.logger_freshs.info(cc.c_green + 'Starting job1 on ' + str(self.name) + cc.reset)
                    self.add_as_escape(rp_id)

            # parallel escape
            elif ss.ffs_control.parallel_escape == 1:
                if ncpoints > 0:

                    cand_pts, max_steps_pts = ss.ffs_control.escape_point_candidates()

                    # decide whether to proceed or start new job
                    if len(cand_pts) > 0:
                        pt_sel = random.randint(0,len(cand_pts)-1)
                        res_point_id = cand_pts[pt_sel]
                        # leftover steps from this point on as max_steps
                        max_steps = ss.ffs_control.escape_steps - max_steps_pts[pt_sel]
                            
                        # get point and start run
                        last_escape_point, rp_id, rcval = ss.storepoints.return_escape_point_by_id(res_point_id)
                        self.add_as_escape(rp_id)
                        newtrace = False
                        ss.logger_freshs.info(cc.c_green + 'Resuming job 1 on ' + str(self.name) + '. ' + str(max_steps) + ' steps left.' + cc.reset)
                    else:
                        #start new run, all escape traces are complete
                        max_steps = ss.ffs_control.escape_steps
                        ss.logger_freshs.info(cc.c_green + 'Starting job1 on ' + str(self.name) + ' with ' + str(max_steps) + ' steps.' + cc.reset)


                else:
                    max_steps = ss.ffs_control.escape_steps
                    ss.logger_freshs.info(cc.c_green + 'Starting job1 on ' + str(self.name) + ' with ' + str(max_steps) + ' steps.' + cc.reset)


            self.incr_runcount(current_lambda)
            self.remove_from_explorer()
        else:
            # explorers
            ai = self.server.ai
            next_interface = ai.ex_lambdas[ex_ind]
            current_lambda = ai.citeml(ex_ind)
            ss.explorer_clients[self] = current_lambda
            if ai.auto_max_steps != 0:
                max_steps = ai.auto_max_steps
            # increment M_0 counter
            ss.logger_freshs.info(cc.c_cyan + 'Starting explorer job1 on ' + str(self.name) + \
                                  cc.reset)

        job_string = "\"jobtype\": 1" + \
                    ", \"A\": " + str(self.server.A) + \
                    ", \"B\": " + str(self.server.B) + \
                    ", \"seed\": "           + str(client_seed) + \
                    ", \"rp_id\": \""        + str(rp_id) + "\"" + \
                    ", \"next_interface\": " + str(next_interface) + \
                    ", \"act_lambda\": " + str(current_lambda) + \
                    ", \"max_steps\": " + str(max_steps) + \
                    ", \"clientname\": \"" + self.name + "\"" + \
                    ", \"timestamp\": \"" + ss.timestamp + "\"" + \
                    ", \"uuid\": \"" + self.get_uuid() + "\""

        if last_escape_point != 'None':
            job_string += ", \"random_points\": " + str(last_escape_point) + ", \"random_points\": " + str(last_escape_point)

        if not newtrace:
            job_string += ", \"last_rc\": " + str(rcval)

        job_string_complete = self.compose_message(job_string)

        ss.logger_freshs.debug(cc.c_magenta + 'Sending job_string ' + job_string_complete + \
                                  cc.reset)

        # Send job string
        ss.client_runtime[str(self)] = time.time()
        self.long_send( job_string_complete )

# --------------------------------------------------------------------------
# FFS Probabilities, monster task
# --------------------------------------------------------------------------
    def start_job2(self, ex_ind=-1):

        ss = self.server
        self.remove_from_idle()
        # ghosts are started separately
        self.remove_from_ghost()

        max_steps = 0
        
        # choose a seed for the client RNG, using the server RNG
        client_seed = random.randint(0, ss.myRandMax)
        
        # only use the following if not in exploration mode
        if ex_ind == -1:
        
            next_interface = ss.lambdas[ss.act_lambda]
            current_lambda = ss.act_lambda
            rp_lambda = current_lambda-1
            
            self.remove_from_explorer()
            
            # Get potential calculation point
            random_point, rp_id = ss.storepoints.return_random_point(rp_lambda)
        
            self.incr_runcount(current_lambda)
    
            # Check if this point is in ghost database.
            indatabase = ss.ghostpoints.origin_point_in_database_and_active(rp_id)
            
        else:
            ai = self.server.ai
            indatabase = False
            next_interface = ai.ex_lambdas[ex_ind]
            current_lambda = ai.citeml(ex_ind)
            ss.explorer_clients[self] = current_lambda
            if ai.auto_max_steps != 0 and ai.auto_histo:
                max_steps = ai.auto_max_steps
            # Get calculation point
            if len(ss.lambdas) == ss.act_lambda:
                random_point, rp_id = ss.storepoints.return_random_point(ss.act_lambda-1)
            else:
                random_point, rp_id = ss.storepoints.return_random_point(ss.act_lambda)

        ss.logger_freshs.debug(cc.c_magenta + 'Indatabase: ' + str(indatabase) + ', ghostcount = ' + str(self.ghostcount) + cc.reset)

        if indatabase and self.ghostcount < ss.ffs_control.max_ghosts_between:
            # Ghost run is available! Get it.
            ghostline = ss.ghostpoints.get_line_origin_point(rp_id)

            self.ghostcount += 1

            self.remove_from_ghost()
            
            # Check if ghostrun was successful
            if int(ghostline[6]) == 1:
                data = "\"jobtype\": 2, \"success\": True, \"points\": " + str(ghostline[1])
                ss.logger_freshs.info(cc.c_magenta + 'Wohooo! This was a ghost (' + str(self.name) + ', success=1).' + cc.reset)
            else:
                data = "\"jobtype\": 2, \"success\": False"
                ss.logger_freshs.info(cc.c_magenta + 'Wohooo! This was a ghost (' + str(self.name) + ', success=0).' + cc.reset)

            data += ", \"act_lambda\":" + str(ghostline[0]) + \
                    ", \"origin_points\": \"" + str(ghostline[2]) + "\"" + \
                    ", \"calcsteps\": "+ str(ghostline[3]) + \
                    ", \"ctime\": " + str(ghostline[4]) + \
                    ", \"runtime\": " + str(ghostline[5]) + \
                    ", \"seed\": " + str(ghostline[9]) + \
                    ", \"rcval\": " + str(ghostline[12]) + \
                    ", \"uuid\": \"" + str(ghostline[16]) + "\"" + \
                    ", \"customdata\": \"" + str(ghostline[17]) + "\"" 

            data = "{" + data + "}"
            
            ss.ghostpoints.update_usecount_by_myid(str(ghostline[8]))

            ss.ghosttimesave += float(ghostline[5])
            ss.ghostcalcsave += int(ghostline[3])

            # TODO: Do this somewhere else!
            try:            
                ss.ffs_control.append_to_lamconf('Resume_info', 'ghosttimesave', str(ss.ghosttimesave))
                ss.ffs_control.append_to_lamconf('Resume_info', 'ghostcalcsave', str(ss.ghostcalcsave))
            except:
                ss.logger_freshs.warn(cc.c_magenta + 'Could not write ghost benefits to config file.' + cc.reset)

            # call analyzation routine with ghost data
            self.received_count = self.received_count + 1
            runid               = self.name + "_" + str(self.received_count)
            ss.analyze_recv(data, self, runid)
            

        else:
            # random point not in ghost database

            self.ghostcount = 0

            # check if ghost client is calculating this point at the moment
            if rp_id in ss.ghost_clients.values():
                done = 0
                # point is at the moment calculated, find key (client) for value
                for key in ss.ghost_clients.keys()[::-1]:
                    if not done:
                        if ss.ghost_clients[key] == rp_id:
                            # entry found. Convert ghost to real client
                            ss.logger_freshs.info(cc.c_magenta + 'Converted ' + str(self.name) + \
                                                           ' from ghost to real.' + cc.reset)
                            # started run on random point, remove from lists
                            random_point = []
                            ss.ghost_clients.pop(key)
                            #try:
                            #ss.ghostnames.remove(self.find_client_by_key(key).name)
                            ss.ghostnames.remove(key.name)
                            #except:
                            #    ss.logger_freshs.warn(cc.c_red + \
                            #                                   'Could not remove ghost from name array.' + \
                            #                                   cc.reset)
                            # set done because we use only one client which calculates on this point
                            done = 1                    
            
            self.remove_from_ghost()
            
            # Is there a random point left?
            if len(random_point) > 0:
                # Start normal job2
                
                if ex_ind == -1:
                    ss.logger_freshs.info(cc.c_green + 'Starting job2 on ' + str(self.name) + \
                            ', run ' + str(ss.M_0[current_lambda]) + \
                            cc.reset)
                else:
                    ss.logger_freshs.info(cc.c_cyan + 'Starting explorer job2 on ' + str(self.name) + \
                                          cc.reset)
                    ss.logger_freshs.debug(cc.c_magenta + 'Explorer index is ' + str(current_lambda) + ', max_steps = ' + str(max_steps) + \
                                          cc.reset)

                job_string = "\"jobtype\": 2 , \"A\": "     + str(self.server.A)    + \
                                   ", \"B\": "              + str(self.server.B) + \
                                   ", \"random_points\": "  + str(random_point)  + \
                                   ", \"rp_id\": \""        + str(rp_id) + "\""     + \
                                   ", \"seed\": "           + str(client_seed)      + \
                                   ", \"next_interface\": " + str(next_interface) + \
                                   ", \"act_lambda\": "     + str(current_lambda) + \
                                   ", \"max_steps\": "      + str(max_steps) + \
                                   ", \"clientname\": \""   + self.name + "\"" + \
                                   ", \"timestamp\": \""    + ss.timestamp +"\"" + \
                                   ", \"uuid\": \""         + self.get_uuid() + "\""

                job_string_complete = self.compose_message(job_string)

                #ss.logger_freshs.debug(cc.c_magenta + 'Sending job_string ' + job_string_complete + \
                #                  cc.reset)

                ss.client_runtime[str(self)] = time.time()
                
                # Send job string
                self.long_send( job_string_complete )
                
            else:
                # No random point is left. Check if another run is necessary, if yes, recall this routine recursively
                
                # Are there currently enough runs launched?
                ss.check_for_job(self)
                
# --------------------------------------------------------------------------                
# FFS Ghost run for probabilities
# --------------------------------------------------------------------------
    def start_ghost_job2(self, ex_ind=-1):
        ss = self.server
        
        self.remove_from_explorer()
        self.remove_from_idle()

        # choose a seed for the client RNG, using the server RNG
        client_seed = random.randint(0, ss.myRandMax)
            
        if ex_ind == -1:
            gp_lambda = ss.act_lambda
            next_lambda = ss.act_lambda + 1
            next_interface = ss.lambdas[next_lambda]
        else:
            print "Ghostpoint required! Not implemented yet. Implementation of exploring ghosts is braindeath."
            raise SystemExit
            ai = self.server.ai
            next_lambda = ai.ex_lambdas[ex_ind]
            next_interface = ai.citeml(ex_ind)
            
        selected_point, rp_id = ss.storepoints.select_ghost_point(gp_lambda)
        
        self.add_as_ghost(rp_id)
            
        # Send job string
        ss.logger_freshs.info(cc.c_magenta + 'Starting ghost job2 on ' + str(self.name) + \
                              ', ' + str(gp_lambda) + ' to ' + str(next_lambda) + \
                              cc.reset)
        
        ss.client_runtime[str(self)] = time.time()
        
        job_string = "\"jobtype\": 2 , \"A\": " + str(ss.A) + \
                    ", \"B\": "              + str(self.server.B) + \
                    ", \"random_points\": "  + str(selected_point)   + \
                    ", \"rp_id\": \""        + str(rp_id) + "\""     + \
                    ", \"seed\": "           + str(client_seed)      + \
                    ", \"next_interface\": " + str(next_interface) + \
                    ", \"clientname\": \"" + self.name + "\"" + \
                    ", \"timestamp\": \"" + ss.timestamp + "\"" + \
                    ", \"act_lambda\":"      + str(next_lambda) + \
                    ", \"uuid\": \"" + self.get_uuid() + "\""

        job_string_complete = self.compose_message(job_string)

        #ss.logger_freshs.debug(cc.c_magenta + 'Sending job_string ' + job_string_complete + \
        #                       cc.reset)
        
        self.long_send( job_string_complete )


# --------------------------------------------------------------------------
# SPRES fixed-tau run
# --------------------------------------------------------------------------
    def start_job3_fixedtau(self):
        
        ss=self.server

        ##choose the bin-pair that this shot must have in its recent history
        row           = ss.act_lambda

        ##(fromRow, rp_id) = ss.spres_control.select_parent_shot_id( row )
        (fromRow, rp_id) = ss.spres_control.select_parent_shot_evenest( row )
        if fromRow == None:
            self.server.logger_freshs.info(cc.c_blue + 'Could not select path entering row:'+str(row)+cc.reset)
            return False

        ###Logically we only need to search by id, but searching by t as well
        ###  gives SQLITE a chance to take advantage of indexes on the database.
        #random_point = self.server.storepoints.return_point_by_id( rp_id )
        
        random_point = self.server.storepoints.return_point_by_id_t( rp_id, ss.epoch )
        if random_point == "[0.0, 0.0]":
                random_point = [["0"]]    

        if random_point != None:
        
            # choose a seed for the client RNG, using the server RNG
            client_seed = random.randint(0,ss.myRandMax)

            ##will this run be monitored for boundary-crossing?
            abs_at_B = 0
            if ss.absorb_at_B > 0 and ss.test_absorb_at_B_after_bin <= row:
                abs_at_B = ss.absorb_at_B

            # Send job string
            self.server.client_runtime[str(self)] = time.time()

            
            job_string = "\"jobtype\": 3, \"parentlambda\": "  + str(fromRow) + \
                                 " , \"currentlambda\": " + str(row)+\
                                 " , \"rp_id\": \""       + str(rp_id) + "\""+\
                                 " , \"halt_steps\": "    + str(ss.tau) + \
                                 " , \"seed\": "          + str(client_seed) + \
                                 " , \"random_points\": " + str(random_point) + \
                                 " , \"uuid\": \"" + self.get_uuid() + "\""
            if abs_at_B:
                job_string +=   " , \"halt_rc_upper\": " + str(ss.B) + \
                                " , \"check_rc_every\": "+ str(1) + \
                                " , \"absorb_at_B\": "   + str(abs_at_B)
                
            if ss.clients_use_fs:
                config_folder = ss.folder_conf+str(ss.epoch+ss.tau)
                job_string   += " , \"save_configs\": \"" + config_folder +"\"" 
                


            job_string_complete = self.compose_message(job_string)

            ss.logger_freshs.debug(cc.c_magenta + 'Sending job_string ' +\
                                   job_string_complete[0:256] + " [...]" + \
                                   cc.reset)
                               
            self.long_send( job_string_complete )
            ss.run_count[row] += 1

            self.remove_from_idle()

            ss.logger_freshs.debug(cc.c_magenta + 'Sent it.' + cc.reset)

            return True
        else:
            self.server.logger_freshs.info(cc.c_red + 'ERROR! Could not start job between ' +\
                                            str(fromRow) + " and "+\
                                            str(row)     + " at " + str(ss.epoch) + cc.reset)
            exit( "Error finding configs." )
            return False


# --------------------------------------------------------------------------                    
# SPRES fixed-tau run
# --------------------------------------------------------------------------
    def start_job(self, config, config_id, branch_tau, check_rc_every, branch_rc_upper, branch_rc_lower ):
        
        ss=self.server

        # choose a seed for the client RNG, using the server RNG
        client_seed = random.randint(0,ss.myRandMax)


        # Send job string
        self.server.logger_freshs.info(cc.c_blue + 'Starting job from ' +\
                                        config_id + cc.reset)
        self.server.logger_freshs.info(cc.c_green + 'Starting job on ' + str(self.name) +\
                                                         ' seed ' + str(client_seed) + ', ' + \
                                                         ' rp id ' + str(config_id) + ', ' + \
                                                         ", \"tau\": " + str(branch_tau) + \
                                                         ", \"A\": "   + str(branch_rc_lower) + \
                                                         ", \"B\": "   + str(branch_rc_upper) + \
                                                         ", \"abs at B? " + str(check_rc_every) + ', ' +\
                                                         str(config[0])[0:90] + '...' + \
                                                         cc.reset)


        self.server.client_runtime[str(self)] = time.time()


        job_string = "\"jobtype\": 3, \"parentlambda\": "  + str(0) + \
                                 ", \"currentlambda\": " + str(0) + \
                                 ", \"rp_id\": \""       + str(config_id) + "\""+\
                                 ", \"tau\": " + str(branch_tau) + \
                                 ", \"A\": "   + str(branch_rc_lower) + \
                                 ", \"B\": "   + str(branch_rc_upper) + \
                                 ", \"absorb_at_B\": "   + str(check_rc_every) + \
                                 ", \"seed\": "          + str(client_seed) + \
                                 ", \"random_points\": " + str(config[0])
        
        job_string_complete = self.compose_message(job_string)

        ss.logger_freshs.debug(cc.c_magenta + 'Sending job_string ' + job_string_complete + \
                               cc.reset)
                               
        self.long_send( job_string_complete )
        
        self.remove_from_idle()

        return True
        


# --------------------------------------------------------------------------
# Let the client wait for a new job
# --------------------------------------------------------------------------
    def start_job_wait(self):
        self.add_as_idle()


        self.server.logger_freshs.info(cc.c_green + 'Setting ' + str(self.name) + \
                                       ' into wait mode.' + cc.reset)
        
        waits=[]
        for cli in self.server.idle_clients:
            waits.append(str(cli.name))
        waits.sort()
        self.server.logger_freshs.debug(cc.c_blue + 'Clients: ' + str(waits) + ' waiting.' + cc.reset)



        self.long_send("{\"jobtype\": 0 }PKT_SEP\n")


    # Send exit job to client
    def send_quit(self):
        self.server.logger_freshs.info(cc.c_blue + 'Sending quit to ' + str(self.name) + cc.reset)
        self.long_send("{\"jobtype\": -1 }PKT_SEP\n")
        
    # answer, that we are alive
    def answer_alive(self):
        self.long_send("server_is_alivePKT_SEP\n")

    # request alive signal from client
    def request_alive(self):
        self.long_send("alive_requestPKT_SEP\n")

    # helper function for handling large packets
    def long_send(self, data):
        packet_len = len(data)
        count      = 0
        while count < packet_len:
            count += self.send( data[count:packet_len] )


