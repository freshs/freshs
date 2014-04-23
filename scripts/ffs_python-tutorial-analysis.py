#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2014 Kai Kratzer, Universität Stuttgart, ICP,
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

# writes each percolating trace to traceX.dat and creates a plotscript for all traces (trace.gnuplot)
# writes the information for reproducing to traceX.rep

# os-related
import sys
sys.path.append('../server/modules/ffs')
sys.setrecursionlimit(999999)
import os
import glob
import re

# custom
import configpoints

datadir_base = 'OUTPUT'
n_differentbacktracks = 10
store_only_different = True

# Create directory and do not complain
def tmkdir(the_dir):
    try:
        os.mkdir(the_dir)
    except:
        pass

def remove_brackets(rmstring):
    return re.sub('\]','',re.sub('\[','',rmstring))

def remove_trailing_slash(rmstring):
    return re.sub('/$','',rmstring)

# visit a configpoint and determine origin (recursive procedure)
def visit(cfp):
    global tr_line
    global rc_line
    global rep_line
    global last_processed

    op = cfph.return_origin_point_by_id(cfp[2])
    print "origin point of", cfp[8], "is", op[8]

    tr_line.append([ cfp[0],cfp[13],cfp[12],cfp[3],cfp[4],cfp[5],cfp[9] ])
    rc_line.append(cfp[17].strip().split())
    rep_line.append( [ remove_brackets(cfp[2]), cfp[3], cfp[9],remove_brackets(cfp[1]) ] )
    if not 'escape' in op[2]:
        visit(op)
    else:
        last_processed = op[8]

# check usage
if len(sys.argv) < 2:
    print "Usage:", sys.argv[0], "<configpoint-DB-file.sqlite>"
    exit(1)

# construct timestamp out of DB filename
timestamp = re.sub('.*/', '', re.sub('_configpoints.*', '', sys.argv[1]))

datadir = remove_trailing_slash(datadir_base) + '/' + timestamp

# configpoint handler
cfph = configpoints.configpoints('none', sys.argv[1])

# Prepare directories
outdir_base = 'OUTPUT'
outdir = outdir_base + '/' + timestamp

# backtrace plotfile
plotfile_trace = outdir + '/tree_success.gnuplot'

tmkdir(outdir_base)
tmkdir(outdir)


# ----------------------------------------------------------------------------
# Backtrace successful trajectories
# ----------------------------------------------------------------------------

fhtp = open(plotfile_trace,'w')
fhtp.write('set xlabel "steps"\n')
fhtp.write('set ylabel "{/Symbol l}"\n')
fhtp.write('plot \\\n')

# get endpoint candidates
cfpcand = cfph.return_points_on_last_interface()

tracecount = 0
ndiffops = 0
dops = []
maxtr = len(cfpcand)
for cfp in cfpcand:
    # trace line array
    tr_line = []
    rc_line = []
    # line for reproducing a cfp trace
    rep_line = []
    # Visit this endpoint and determine origins recursively, from B to A
    visit(cfp)
    
    if (not last_processed in dops) or not store_only_different:
        if not last_processed in dops:
            dops.append(last_processed)
            ndiffops += 1

        # step count
        steps_tot = 0
        tname = 'trace' + str(tracecount)
        print tname
        tracefile = tname + '.dat'
        tracepath = tname + '.path'
        repfile = tname + '.rep'
        fhtr=open( outdir + '/' + tracefile,'w')
        fhpath=open( outdir + '/' + tracepath,'w')
        fhrep=open( outdir + '/' + repfile,'w')
        
        fhrep.write('# start_point, steps, seed, cfp\n')
        fhtr.write('# ' + tname + ': steps_tot, lambda_id, lambda, rc, psteps, ctime, runtime, seed\n')

        # write reproducing information to file, from A to B
        for iline in rep_line[::-1]:
            for jline in iline:
                fhrep.write(str(jline) + ' ')        
            fhrep.write('\n')

        npoints = len(tr_line)

        # write trace to file, from A to B
        for i in range(npoints-1,-1,-1):
            iline = tr_line[i]
            steps_last = steps_tot
            steps_tot += iline[3]
            
            # number of reaction coordinates
            nrcs = len(rc_line[i])
            stepwidth = (steps_tot - steps_last)/nrcs
            stepcount = 0
            for rc in rc_line[i]:
                fhpath.write('%d %f\n' % (steps_last + stepwidth*stepcount + 1,float(rc)) )
                stepcount += 1
            
            fhtr.write(str(steps_tot) + ' ')
            for jline in iline:
                fhtr.write(str(jline) + ' ')
            fhtr.write('\n')

        fhtr.close()
        fhpath.close()
        fhrep.close()        
        

        tracecount += 1
        if ndiffops > n_differentbacktracks:
            fhtp.write('"' + tracefile + '" u 1:3 w l notitle\n') 
            break
        else:
            if tracecount < maxtr - 1:
                fhtp.write('"' + tracefile + '" u 1:3 w l notitle, \\\n')
            else:
                fhtp.write('"' + tracefile + '" u 1:3 w l notitle\n')   

fhtp.close()


print "Wrote to output folder", outdir








