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

import asyncore
import sys
import os
import signal

def handle_sigint(signum, frame):
    print "Please wait while the database is updated."

reldir = os.path.dirname(__file__)
if not reldir:
    reldir = '.'
# Append paths
sys.path.append(reldir + '/modules')
sys.path.append(reldir + '/modules/ffs')
sys.path.append(reldir + '/modules/nsffs')
sys.path.append(reldir + '/modules/spres')

#print "Python path is:"+str(sys.path)

# "Testing a few dependencies:"

try:
    import numpy
except Exception as e:
    print 'IMPORT ERROR: ' +str(e)
    exit(8)

try:
    import math
except Exception as e:
    print 'IMPORT ERROR: ' +str(e)
    exit(8)



from modules  import server as ss
from optparse import OptionParser

parser = OptionParser(usage="usage: %prog [options] [args]", version="%prog 1.0")

parser.add_option("-r", "--restart", dest="timestamp", help="timestamp of run to restart", metavar="timestamp", type="string", default='auto')
parser.add_option("-c", "--config", dest="config", help="configfile", metavar="configfile", type="string", default='auto')
parser.add_option("-d", "--debug", dest="debug", help="enable debug mode", metavar="debugmode", type=int, default=0)

(options, args) = parser.parse_args()

##Args will hold positional arguments... 
##if there is any argument without a flag, assume that it is a control file:
if len(args) > 0:
    if options.config == 'auto':
        options.config = str(args[0])
    else:
        print "server: Warning! Un-parsed option(s): args:"+str(args)+"\n"
    if len(args) > 1:
         print "server: Warning! Un-parsed option(s): args:"+str(args[1:])+"\n"

##Minimal argument checking
if os.path.isfile(options.config):
    print "Server: reading server config file: "+options.config
else:   # if filename is not given
    print('Server: A valid server config file is required.\n'+\
          '\tCurrent value is: "'+\
      options.config +'", which is not a valid file.\n'+\
                       '\tLook at examples in the test directory.')
    exit(8)


##Call the server
    print "Server: reading server config file: "+options.config
try:
    a = ss.server( timestamp = options.timestamp, configfile_name = options.config, debugmode = options.debug  )
    asyncore.loop()
except Exception as e:
    signal.signal(signal.SIGINT, handle_sigint)
    a.storepoints.commit()
    a.ghostpoints.commit()
    print "\nServer caught exception: "+str(e)+" and shut down safely."
    sys.exit(0)
finally:
    print "\nQuitting."
    sys.exit(0)


