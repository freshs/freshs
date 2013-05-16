#!/usr/bin/python
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


import asyncore
import socket
#import sys

import threading

##time provides a sleep command for testing trivial clients
import time

##parsing
import ast

#arguments = sys.argv

#print arguments
#raise SystemExit

#
class fclient(threading.Thread,asyncore.dispatcher):
    def __init__(self, fffs, host, port, timeout, report_delay, name='default'):
        threading.Thread.__init__(self)
        asyncore.dispatcher.__init__(self)
        self.received_data = []
        self.save_bytes=""
        self.send_bytes=""
        self.name = name
        self.host = host
        self.port = port
        self.timeout = timeout
        self.fffs = fffs
        self.msg=['ffs client v1'+'PKT_SEP']
        self.abort = False
        self.report_delay = report_delay

    def run(self):
        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect((self.host, self.port))
        print self.name, "is connecting to server."

        # setup timeout stuff
        start_time      = time.time()
        if self.timeout != 0:
            self.stop_after    = start_time + (self.timeout * 60 * 60) ##time to stop at, in seconds.
        else:
            self.timeout       = 0

    # define some functions for comms/book-keeping.
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
                parameterset=ast.literal_eval(data+"\n")
            except:
                print('Warning! Could not parse data packet: ' + data[0:49] + '...') 
                print('Warning! Dropping packet.') 
                return

            ##handle jobs sent in order.
            if parameterset["jobtype"] == 1:
                        print 'Starting job1: Escape flux with parameterset', parameterset
                        time.sleep(self.report_delay)
                        result = self.fffs.job1_escape_flux(self, parameterset)
            elif parameterset["jobtype"] == 2:
                        print 'Starting job2: Probabilities with parameterset', parameterset
                        time.sleep(self.report_delay)
                        result = self.fffs.job2_probabilities(self, parameterset)
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
            print "received unknown data:" + data + ":end, ignoring"
            

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
       
       
       
