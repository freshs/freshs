#!/usr/bin/python
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

# os-related
import sys
sys.path.append('../server/modules')

# custom
import configpoints


if len(sys.argv) < 2:
    print "Usage:", sys.argv[0], "<../server/DB/DB-file>"
    exit(1)

cfph = configpoints.configpoints('none', sys.argv[1])
print "Lambdas from lpos column in DB are:", cfph.return_lamlist()
print "Summary:"
print cfph.show_summary()

