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

# script to calculate stationary distributions when the rc histogram is stored
# in customdata, space separated.

# os-related
import sys
sys.path.append('../server/modules/ffs')
import os
import re
import numpy as np

# custom
import configpoints

# Create directory
def tmkdir(the_dir):
    try:
        os.mkdir(the_dir)
    except Exception as exc:
        print exc

def hq(q,dq,x):
    if x < (q + dq) and x >= q:
        return 1.0
    else:
        return 0.0

def extract_histo(interface,dbhandle, mult):
    histodata = []
    cudtmp = dbhandle.return_customdata(interface)
    for el in cudtmp:
        candi = re.sub('.*allrcs','', el).split()
        for el2 in candi:
            histodata.append( float(mult) * float(el2) )
    return histodata

def Nq(q,dq,interf_histo):
    Nq = 0.0
    for el in interf_histo:
        Nq += hq(q,dq,el)
    #print "Nq =", Nq
    return Nq

# piq per lambda
def piq(q,dq,interf_histo,Mi):
    piqtmpval = Nq(q,dq,interf_histo) / (dq * float(Mi))
    #print "piq:", piqtmpval
    return piqtmpval

# 1d psi(q)
def psi(p_A,Phi_esc,tau_q):
    return p_A * Phi_esc * tau_q

# calculate free energy landscape
def dG(rohq, k_B=1.0, T=1.0):
    return -k_B * T * np.log(rohq)

# calculate p_weight
def pweight(i,probabs):
    ptmp = 1.0
    for j in range(i):
        ptmp *= probabs[j]
    return ptmp

# 2d pi_q_lambda array
def pi_q_lam(lambdas, M, dbhandle, qs, dq, mult = 1.0):
    global lamvals
    
    print "Calculating pi(q,lambda)"
    piqtmp = []
    for ilam in range(len(lambdas)-1):
        the_lambda = ilam + 1
        print "Lambda", the_lambda
        print "Retrieving histogram for lambda", the_lambda
        interf_histo = extract_histo(the_lambda, dbhandle, mult)
        lamvals.append(interf_histo)
        Mi = M[ilam]
        tmpval = []
        print "Processing histogram"
        for q in qs:
            tmpval.append(piq(q,dq,interf_histo,Mi))
        print "pi(q,lambda) =", tmpval
        piqtmp.append(tmpval)
    return piqtmp


def tau_pm(piqlam,ninterfaces,probabilities):
    print "Calculating tau."
    tmpvalq = []
    #print len(piqlam[0])
    for iq in range(len(piqlam[0])):
        tmpsum = piqlam[0][iq]
        for i in range(1,ninterfaces-1):
            tmpsum += piqlam[i][iq] * pweight(i,probabilities)
        tmpvalq.append(tmpsum)
    return np.array(tmpvalq)

def build_histo(qs, dq, values):
    tmphisto = []
    for iq in range(len(qs)):
        tmphisto.append(0)
        bin_min=qs[iq]
        bin_max=qs[iq] + dq
        for el2 in values:
            for el in el2:
                if el <= bin_max and el > bin_min:
                    tmphisto[iq] += 1
    return tmphisto

   
# check usage
if len(sys.argv) < 2:
    print "Usage:", sys.argv[0], "<configpoints.sqlite>"
    exit(1)

dbfwd = sys.argv[1]

# construct timestamp out of DB filename
timestampfwd = re.sub('.*/', '', re.sub('_configpoints.*', '', dbfwd))
# configpoint handler
fcfph = configpoints.configpoints('none', dbfwd)

# Prepare directories
outdir_base = 'OUTPUT'
outdir = outdir_base + '/' + timestampfwd

tmkdir(outdir_base)
tmkdir(outdir)

# get endpoint candidates
print "Reading forward probabilities"
fprobs, fN, fnonsuccess, fM = fcfph.return_probabilities(1)
print fprobs

#ninterfaces = cfphfwd.biggest_lambda()
print "Reading forward lambdas"
flambdas = fcfph.return_lamlist()[:-1]
fninterfaces = len(flambdas)
print flambdas, fninterfaces

lamvals = []

dq = 0.2
qs = np.arange(-1.5,1.5+dq,dq)

fctime = fcfph.return_ctime()
fnop = fcfph.return_nop(0)
phi_A = float(fnop) / fctime

k_AB = phi_A * np.prod(fprobs)

print "Escape flux:", phi_A, "--- Rate k_AB:", k_AB

# forward
fallpiqs = pi_q_lam(flambdas, fM, fcfph, qs, dq)

ftau_q = tau_pm(fallpiqs,fninterfaces,fprobs)

p_A = 0.5

fpsis_q = psi(p_A,phi_A,ftau_q)
bpsis_q = fpsis_q[::-1]

roh_q = fpsis_q + bpsis_q

roh_q /= np.max(np.abs(roh_q),axis=0)

dG_q = dG(roh_q)

fout=open(outdir + '/data_dG.dat', 'w')
fout.write("# q G tau_0 psi_A psi_B roh\n")

for iel in range(len(qs)):
    #print qs[iel], dG_q[iel]
    fout.write("%f %e %e %e %e %e\n" % (qs[iel], dG_q[iel], ftau_q[iel], fpsis_q[iel], bpsis_q[iel], roh_q[iel]))

fout.close()
print "Wrote to " + outdir + "/data_dG.dat"










