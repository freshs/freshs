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


# This file is a fake test for the FFS algorithm.
# It calculates the transition rate itself for the comparison against the FFS simulation
import os
import time

import asyncore
import fffs

# how many clients should attach?
numclients = 1
# the fake simulation timestep
dt=0.01
# probability for success
p_success = 0.7
# delay for not flooding the server (a real simulation needs time to calculate, too...)
report_delay = 0.0
# Server config to check
srv_conf = 'server-fake-ffs.conf'


# start the server
os.system('python ../../server/main_server.py -c ' + srv_conf + ' &')

time.sleep(5)

# --------------------------------------------

fake_ffs = fffs.fffs(numclients,dt,p_success,report_delay,srv_conf)

for client in fake_ffs.clients:
    client.join()

asyncore.loop()

print("The transition rate should be", fake_ffs.get_k_AB())
