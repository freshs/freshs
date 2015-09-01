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
import os

reldir = os.path.dirname(__file__)
if not reldir:
    reldir = '.'
else:
    # Append paths
    sys.path.append(reldir)

from optparse import OptionParser
from particle import particle

parser = OptionParser()
parser.add_option("-p", "--port", dest="port", help="port to connect on", metavar="port", type=int, default=10000)
parser.add_option("-e", "--ebarrier", dest="ebarrier", help="energy barrier height", metavar="ebarrier", type=float, default=5.0)
parser.add_option("-s", "--server", dest="server", help="server to connect to", metavar="server", type="string", default="localhost")
parser.add_option("-t", "--timeout", dest="timeout", help="refuse to accept new jobs after t=timeout(hours)", metavar="timeout", type=float, default=0.0)

(options, args) = parser.parse_args()

print('Launching particle client, port: ', options.port, ' server: ', options.server, ' timeout: ', options.timeout)

# ffs(A,B,n)
sp = particle(options.server, options.port, options.ebarrier, options.timeout)

asyncore.loop()

