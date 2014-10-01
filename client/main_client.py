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
import asyncore
import os
from   optparse import OptionParser

# Append paths
reldir = os.path.dirname(__file__)
if not reldir:
    reldir = '.'
sys.path.append(reldir + '/modules')

from client   import client

parser = OptionParser(usage="usage: %prog [options] [args]", version="%prog 1.0")

parser.add_option("-c", "--config", dest="config", help="configfile to use", metavar="configfile.conf", type="string", default='client.cfg')

parser.add_option("-s", "--startconf", dest="startconf", help="initial system config file", metavar="initial_config.dat", type="string", default='auto')

parser.add_option("-e", "--execprefix", dest="execprefix", help="prefix for the executable, e.g. mpirun -np 8", metavar="execprefix", type="string", default='none')

parser.add_option("-x", "--executable", dest="execpath", help="path to the simulation executable, e.g.: /home/boris/Espresso/bin/Espresso", metavar="execpath", type="string", default='auto')

parser.add_option("-H", "--harness", dest="harness", help="path to the simulation program harness, e.g.: /home/boris/freshs/harnesses/espresso_plain", metavar="harnesspath", type="string", default='auto')

parser.add_option("-S", "--server-host", dest="server", help="network address(:port) of the server, e.g.: localhost:1000 or www.google.com", metavar="server_address(:port)", type="string", default='auto')


(options, args) = parser.parse_args()

if os.path.isfile(options.config):
    print("Client: reading client config file: "+options.config)
else:   # if filename is not given
    print('Client: A valid client config file is required.\n'+\
          '\tCurrent value is: "'+\
      options.config +'", which is not a valid file.\n'+\
                       '\tLook at examples in the test directory.')
    exit(8)

ci = client(options.config, options.execprefix, options.execpath, options.harness, options.startconf, options.server)

asyncore.loop()

