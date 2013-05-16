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
import os
import re

# custom
import configpoints

def tmkdir(the_dir):
    try:
        os.mkdir(the_dir)
    except:
        pass

def mkhisto(data,bins):
    lx = [0]
    ly = [0]
    vmin = min(data)
    vmax = max(data)
    spacing = (vmax-vmin)/float(bins)
    for k in range(bins):
        lbin = float(k) * spacing + vmin
        rbin = (float(k) + 1.0)*spacing + vmin
        lx.append(lbin + 0.5 * (rbin - lbin))
        ly.append(0)
        for el in data:
            if el <= rbin and el > lbin:
                ly[-1] += 1
    return lx, ly
        

if len(sys.argv) < 2:
    print "Usage:", sys.argv[0], "<../server/DB/configpoint-DB-file>"
    exit(1)

bins = 20

timestamp = re.sub('.*/', '', re.sub('_configpoints.*', '', sys.argv[1]))

cfph = configpoints.configpoints('none', sys.argv[1])

outdir_base = 'OUTPUT'
outdir = outdir_base + '/' + timestamp

tmkdir(outdir_base)
tmkdir(outdir)

rplotfile = outdir + '/histo_runtime.gnuplot'
cplotfile = outdir + '/histo_calcsteps.gnuplot'

rfh = open(rplotfile,'w')
cfh = open(cplotfile,'w')

rfh.write('plot \\\n')
cfh.write('plot \\\n')

maxlam = cfph.biggest_lambda()
for i in range(maxlam+1):
    runtimes = cfph.return_runtime_list(i)
    calcsteps = cfph.return_calcsteps_list(i)
    rlx, rly = mkhisto(runtimes,bins)
    clx, cly = mkhisto(calcsteps,bins)

    outfile = outdir + '/lambda' + str(i) + '.dat'
    rhistofile = outdir + '/histo_runtime' + str(i) + '.dat'
    chistofile = outdir + '/histo_calcsteps' + str(i) + '.dat'

    fh = open(outfile,'w')
    fh.write('# i runtime calcsteps\n')
    for j in range(len(runtimes)):
        fh.write(str(i) + ' ' + str(runtimes[j]) + ' ' + str(calcsteps[j]) + '\n')
    fh.close()

    fh = open(rhistofile,'w')
    fh.write('# bin count\n')
    for j in range(len(rlx)):
        fh.write(str(rlx[j]) + ' ' + str(rly[j]) + '\n')
    fh.close()

    fh = open(chistofile,'w')
    fh.write('# bin count\n')
    for j in range(len(clx)):
        fh.write(str(clx[j]) + ' ' + str(cly[j]) + '\n')
    fh.close()
    
    rfh.write('"' + re.sub('.*/','',rhistofile) + '" u 1:2 with boxes title "to lambda' + str(i) + '", \\\n')
    cfh.write('"' + re.sub('.*/','',chistofile) + '" u 1:2 with boxes title "to lambda' + str(i) + '", \\\n')

rfh.write('0 lw 0 notitle\n')
cfh.write('0 lw 0 notitle \n')


rfh.close()
cfh.close()

for i in range(maxlam+1):
    print "Different origin_points on interface", i, ":", len(cfph.interface_statistics(i))

print "Wrote to output folder", outdir



