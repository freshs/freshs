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

########################################################################
# This small program calls the harness script with the right parameters
# This is necessary, because lammps can be used in many ways (e.g. as
# a python or C/C++ library or as executable with the call 
# ./lammps < simuscript.in
# There is a job_scripts which cover the library cases.
# For the use with a C/C++ library proceed in the same way like
# with the python lib example with the difference that the job_script 
# must be your compiled program which writes the metadata in the end
# For calling lammps with ./lammps < simuscript.in you have to write
# your own harness script, which prepares the environment, makes the
# call, calculates the reaction coordinate and returns the data.
# refer to the 'ell' job_script in this case
########################################################################

import sys
import subprocess

subprocess.call(sys.argv[1:])
