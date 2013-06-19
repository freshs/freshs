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

# database
import sqlite3

# point selection: SQlite RNG is not high quality; and cannot be seeded.
import random

# Logging
import logging

# Formatting
import modules.concolors as cc

# Parsing
import ast
import re

#### CLASS FOR HANDLING CONFIG POINTS ON HYPERSURFACES ####
class configpoints:
    def __init__(self, server, dbfile):
    
        self.server = server
        
        # create sqlite table
        self.dbfile = dbfile
        self.con, self.cur = self.connect()
        self.init_table()
        self.have_pair_ij = 0
        # if you have problems with the database which cannot be written to disk, error: "database or disk is full"
        #self.cur.execute('PRAGMA temp_store = 2')
        
    # Connect to database
    def connect(self):
        try:
            self.server.logger_freshs.info(cc.c_green + 'Connecting to DB: ' + self.dbfile + cc.reset)
        except:
            pass
        con = sqlite3.connect(self.dbfile)
        cur = con.cursor()
        return con, cur

    # Close database connection
    def close(self):
        self.con.close()

    def commit(self):
        self.con.commit()

    # Create table layout
    def init_table(self):
        try:
            self.cur.execute('''create table configpoints (lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, myid text, seed int, lambda_old int, weight real, rcval real, lpos real, usecount int, deactivated int, uuid text, customdata text)''')
            self.con.commit()

            ##This ensures that SQL knows to look at the end of the table for newer entries.
            self.cur.execute('''create index timeindex on configpoints ( calcsteps )''')
            self.con.commit()

        except:
            #print "Not creating table, already exists."
            pass


    # Add config point to database
    def add_point(self,interface, newpoint, originpoint, calcsteps, ctime, runtime, runcount,pointid=0, seed=0, rcval=0.0, lpos=0.0, usecount=0, deactivated=0,uuid='',customdata=''):
        entries = []
        # Create table entry
        success = 0
        # check for success (important for ghost table)
        if newpoint != '':
            success = 1
        entries.append((interface, str(newpoint), str(originpoint), calcsteps, ctime, runtime, success, runcount, pointid, seed, 0, 0.0, rcval, lpos, usecount, deactivated, uuid, customdata))
            
        for t in entries:
            # TODO: error handling, if database is locked or so
            maxretry = 3
            attempt = 0
            writeok = 0
            while (not writeok) and (attempt < maxretry):
                try:
                    self.cur.execute('insert into configpoints values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)', t)
                    self.con.commit()
                    writeok = 1
                except:
                    attempt += 1
                    self.server.logger_freshs.warn(cc.c_red + 'Could not write data to DB, retrying ' + str(maxretry) + ' times: ' + str(attempt) + '/' + str(maxretry) + cc.reset)
                    #quit client and throw error (?)


    # Return number of active points (nop) on interface
    def return_nop(self,interface):
        self.cur.execute('select count(*) from configpoints where lambda = ? and success = 1 and deactivated = 0', [interface])
        retval = 0

        r = self.cur.fetchone()
        return r[0]

    # return number of all points on interface (including deactivated)
    def return_nop_all(self,interface):
        self.cur.execute('select count(*) from configpoints where lambda = ? and success = 1', [interface])
        retval = 0

        r = self.cur.fetchone()
        return r[0]
        

    def return_last_received_count(self,clname):
        self.cur.execute('select myid from configpoints where myid like \'' + str(clname) + '%\'')
        retval = [0]
        for row in self.cur:
            retval.append(int(re.sub(str(clname) + '_','',str(row[0]))))
        return int(max(retval))

    # Return overall calculation time on escape interface
    def return_ctime(self):
        self.cur.execute('select sum(ctime) from configpoints where lambda = 0 and success = 1 and deactivated = 0')
        ctime = 0.0
        for row in self.cur:
            try:
                ctime = float(row[0])
            except:
                ctime = 0.0
        return ctime

    # Return overall calculation time on escape interface, calculated by the simulation's dt
    def return_ctime_from_calcsteps(self,dt):
        self.cur.execute('select sum(calcsteps) from configpoints where lambda = 0 and success = 1 and deactivated = 0')
        the_calcsteps = 0
        for row in self.cur:
            the_calcsteps = int(row[0])
        return dt*float(the_calcsteps)

    def return_runcount(self, interface):
        self.cur.execute('select max(runcount) from configpoints where lambda = ? and deactivated = 0', [interface])
        runcount = 0
        for row in self.cur:
            runcount = row[0]
        return runcount
        

    def return_escape_point_list(self):
        """Return a list of points on the escape interface."""
        lop = []
        self.cur.execute('select configpoint from configpoints where success = 1 and lambda = 0')
        

    def return_most_recent_escape_point(self):
        """Return the most recent sampled point from escape interface."""

        retpoints = []
        retpoint_ids = ''

        # Count the allowed points
        self.cur.execute('select count(*) from configpoints where success = 1 and lambda = 0')
        n_points = self.cur.fetchone()[0]
        if n_points == 0:
            return 'None', 'escape', 0
            
        # Get the point
        self.cur.execute('select configpoint, myid, rcval from configpoints where success = 1 and lambda = 0 order by rowid desc limit 1')

        ##save the info
        r = self.cur.fetchone()
        retpoints = ast.literal_eval(str(r[0]))
        retpoint_ids = str(r[1])
        rcval = float(r[2])
            
        return retpoints, retpoint_ids, rcval               
        
        
    # Return random point from interface
    def return_random_point(self,the_lambda):

        retpoints = []
        retpoint_ids = ''

        ##Create a view of the DB to save searching repeatedly for the set of candidate points
        viewname = 'v_'+str(the_lambda)
        self.cur.execute(\
   'create temp view if not exists '+viewname+' as select * from configpoints where deactivated = 0 and lambda = '+\
                         str(the_lambda))
        ##Note that passing arguments doesn't work for view creation in sqlite,
        ##you have to mung the string directly.


        # Count the allowed points
        self.cur.execute('select count(*) from '+viewname)
        n_points = self.cur.fetchone()[0]
        if n_points == 0 :
            self.cur.execute('drop view if exists '+viewname)
            return retpoints, retpoint_ids

        ##get a random number
        index = random.randint(0, n_points - 1)

        ##do the select
        ##order by seed is less efficient than order by rowid; but should be deterministic, unlike rowid.
        ##Note: if the seed is NULL, or appears twice, then should tiebreak by rowid anyway.
        self.cur.execute(\
            'select configpoint, myid from '+viewname+' order by seed limit 1 offset ?',\
             [index])

        ##save the info
        r = self.cur.fetchone() 
        retpoints = ast.literal_eval(str(r[0]))
        retpoint_ids = str(r[1])
            

        self.cur.execute('drop view if exists '+viewname)
        return retpoints, retpoint_ids

    # Return a config point based on its unique id.
    def return_point_by_id(self, rp_id):

        self.cur.execute('select configpoint from configpoints where myid = ?', [rp_id])
        r = self.cur.fetchone() 

        return str(r[0])

    def return_escape_point_by_id(self, pt_id):
        # Return all collected configpoints and ids and rcval from interface
        self.cur.execute('select configpoint, myid, rcval from configpoints where myid = ?', [pt_id])
        retconfig = ''
        retid = ''
        retrc = 0.0
        for row in self.cur:
            retconfig = ast.literal_eval(str(row[0]))
            retid = str(row[1])
            retrc = float(row[2])
        return retconfig, retid, retrc


    # Check if origin point is in database
    def origin_point_in_database(self, the_point):
        print "Checking for ghostpoint on", the_point
        self.cur.execute('select count(origin_point) from configpoints where origin_point = ?', [str(the_point)])
        for row in self.cur:
            print "Found", row
            occurrence = int(row[0])
        print "Checking", occurrence
        if occurrence >= 1:
            return 1
        else:
            return 0

    # Check if origin point is in database
    def origin_point_in_database_and_active(self, the_point):
        self.cur.execute('select count(origin_point) from configpoints where deactivated = 0 and usecount = 0 and origin_point = ?', [str(the_point)])
        for row in self.cur:
            occurrence = int(row[0])
        if occurrence >= 1:
            # "Origin point is in database"
            return True
        else:
            # "No active origin point in database"
            return False

    def return_usecount(self, the_point):
        self.cur.execute('select usecount from configpoints where origin_point = ?', [str(the_point)])
        for row in self.cur:
            usecount = int(row[0])
        #print "Point was used", usecount, "times."
        return usecount

    # Delete line where origin_point matches (necessary for ghosts)
    def delete_origin_point(self, ghostline):
        # lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, \
        # myid text, seed int, lambda_old int, weight real
        self.cur.execute("delete from configpoints where lambda = ? and configpoint = ? and origin_point = ? and calcsteps = ? and ctime = ? and runtime = ? and success = ? and runcount = ? and myid = ? and seed = ? and lambda_old = ? and weight = ?", ghostline)
        #self.con.commit()

    # change number of runs on last point by 'nor'
    def update_M_0(self,nor=0,point='last'):
        # get last calculated point from database
        if nor != 0:
            if point == 'last':
                self.cur.execute("select configpoint from configpoints where deactivated = 0 and lambda=? order by runcount desc limit 1",[str(self.biggest_lambda())])
            for row in self.cur:
                point = row[0]
            self.cur.execute("update configpoints set runcount=runcount+? where configpoint = ?", [str(nor), str(point)])
            #self.con.commit()
        
    # Return number of runs performed on origin_point
    def runs_on_point(self, point):
        self.cur.execute("select count(*) from configpoints where origin_point = ?", [str(point)])
        retval = 0
        for row in self.cur:
            retval = int(row[0])
        return retval
    
    # Return the biggest lambda in database
    def biggest_lambda(self):
        self.cur.execute('select lambda from configpoints order by lambda desc limit 1')
        biglam = 0
        for row in self.cur:
            biglam = row[0]
        return biglam  

    # Return complete database line where origin_point matches (for copying the ghost-line to real world)
    def get_line_origin_point(self, point):
#        retval = (interface, str(newpoint), str(originpoint), calcsteps, ctime, runtime, success, runcount, pointid, seed, 0, 0.0)
        retval = ()
        self.cur.execute("select * from configpoints where origin_point = ? and usecount = 0 and deactivated = 0 limit 1", [str(point)])
        for row in self.cur:
            retval = row
        return retval


    def get_line_via_myid(self,myid):
        self.cur.execute('select * from configpoints where myid = ?', [myid])
        retval = ''
        for row in self.cur:
            retval = row[:]
        return retval

    # Return all collected configpoints from interface
    def return_configpoints(self, interface):
        self.cur.execute('select configpoint from configpoints where lambda = ? and deactivated = 0 and success = 1', [interface])
        retval = []
        for row in self.cur:
            retval.append(ast.literal_eval(str(row[0])))
        return retval

    # Return all collected configpoints ids from interface
    def return_configpoints_ids(self, interface):
        self.cur.execute('select myid from configpoints where lambda = ? and deactivated = 0 and success = 1', [interface])
        retval = []
        for row in self.cur:
            retval.append(str(row[0]))
        return retval
        
    # Return all collected configpoints and ids from interface
    def return_configpoints_and_ids(self, interface):
        self.cur.execute('select configpoint, myid from configpoints where lambda = ? and deactivated = 0 and success = 1', [interface])
        retconfigs = []
        retids = []
        for row in self.cur:
            retconfigs.append(ast.literal_eval(str(row[0])))
            retids.append(str(row[1]))
        return retconfigs, retids    

    # Return all collected configpoints and ids and rcval from interface
    def return_configpoints_and_ids_and_rcval(self, interface):
        self.cur.execute('select configpoint, myid, rcval from configpoints where lambda = ? and deactivated = 0 and success = 1', [interface])
        retconfigs = []
        retids = []
        retrcs = []
        for row in self.cur:
            retconfigs.append(ast.literal_eval(str(row[0])))
            retids.append(str(row[1]))
            retrcs.append(float(row[2]))
        return retconfigs, retids, retrcs 

    # add ctime to point. Point can be found by comparing calcsteps * dt with ctime.
    def add_ctime_steps(self, origin_point_id, ctime, calcsteps):
        self.cur.execute("update configpoints set ctime=ctime+? where myid = ?", [str(ctime), str(origin_point_id)])
        self.cur.execute("update configpoints set calcsteps=calcsteps+? where myid = ?", [str(calcsteps), str(origin_point_id)])

    # check, if id is somewhere in origin_point, meaning that point is part of a trace
    def id_in_origin(self, pt):
        occurrence = 0
        self.cur.execute('select count(*) from configpoints where origin_point = ?', [str(pt)])
        for row in self.cur:
            occurrence = int(row[0])
        #print "Found ", pt, occurrence, "times as origin point."
        if occurrence > 0:
            return True
        else:
            return False

    # Traceback helper function
    def get_escapetrace_origin_id_by_id(self, the_point_id):
        origin_point_id = 'escape'
        warncnt = 0
        self.cur.execute('select origin_point from configpoints where myid = ?', [str(the_point_id)])
        for row in self.cur:
            warncnt += 1
            origin_point_id = str(row[0])
        if warncnt > 1:
            print "configpoints warning: More than one point found! Returning last one!"
        #print "Origin point from", the_point_id, "is", origin_point_id
        return origin_point_id

    def return_calcsteps_by_id(self, pt_id):
        calcsteps = 0
        self.cur.execute('select calcsteps from configpoints where myid = ?', [str(pt_id)])
        for row in self.cur:
            calcsteps = int(row[0])
        #print "Returning calcsteps from", pt_id, ":", calcsteps
        return calcsteps

    # traceback the points and add up calcsteps.
    # This should only be called in FFS escape run because we assume
    # that we have only one particular trace and no branches at this point!
    def traceback_escape_point(self, pt_id):
        tracesteps = 0
        # add calcsteps from point
        tracesteps += self.return_calcsteps_by_id(pt_id)
        while pt_id != 'escape':
            #print "Visiting", pt_id
            try:
                # find origin point
                pt_id = self.get_escapetrace_origin_id_by_id(pt_id)
                # add calcsteps from point
                if pt_id != 'escape':
                    tracesteps += self.return_calcsteps_by_id(pt_id)
            except:
                break

        return tracesteps

      
    def update_usecount(self,origin_point):
        self.cur.execute("update configpoints set usecount=usecount+1 where configpoint = ?", [str(origin_point)])
        
    def update_usecount_by_myid(self,myid):
        self.cur.execute("update configpoints set usecount=usecount+1 where myid = ?", [str(myid)])        
        
    def return_origin_ids(self,ilambda):
        self.cur.execute('select origin_point from configpoints where lambda = ? and deactivated = 0', [ilambda])
        retval = []
        for row in self.cur:
            retval.append(str(row[0]))
        return retval

    def return_escape_ids(self):
        self.cur.execute('select myid from configpoints where lambda = 0 and deactivated = 0 and origin_point=\'escape\'')
        retval = []
        for row in self.cur:
            retval.append(str(row[0]))
        return retval

    def interface_statistics(self,lam):
        statdict = {}
        for op in self.return_origin_ids(lam):
            if op in statdict:
                statdict[op] += 1
            else:
                statdict[op] = 1
        return statdict

    # return all origin ids of given id array
    def return_origin_ids_by_ids(self, ids):
        origin_points = []
        if len(ids) > 0:
            while len(ids) > 0:
                # split into queries of 500 (sqlite max is 999 for one query)
                if len(ids) >= 500:
                    ids_tmp = ids[0:500]
                else:
                    ids_tmp = ids[:]
                aps = '?'
                for iid in range(len(ids_tmp)-1):
                    aps += ' or myid = ?'
                tquery = 'select origin_point from configpoints where myid = ' + aps
                #print "Query:", tquery
                self.cur.execute(tquery, ids_tmp)
                for row in self.cur:
                    origin_points.append(str(row[0]))
                ids = ids[len(ids_tmp):]
        return origin_points

    # return number of different points on first interface by backtracing
    def interface_statistics_backtrace(self,lam):
        # get origin points from current interface
        newids = self.return_origin_ids(lam)
        # remove dupliactes
        newids = list(set(newids))

        if lam > 1:
            for i in range(lam-1):
                #newids_tmp = []
                #for sel in newids:
                #    newids_tmp.append(self.return_origin_id_by_id(sel))
                newids = list(set(self.return_origin_ids_by_ids(newids)))
                #print self.return_origin_point_by_id(newids[0])

        return newids

    def return_id(self,point):
        self.cur.execute('select myid from configpoints where configpoint = ?', [str(point)])
        retval = ''
        for row in self.cur:
            retval = str(row[0])
        return retval 

    # Select ghost point for calculation 
    def select_ghost_point(self, interface):
        # get configpoints on current interface
        candidates = self.return_configpoints_ids(interface)
        countdict = {}
        for candidate in candidates:
            countdict[str(candidate)] = self.server.ghostpoints.runs_on_point(candidate) + self.runs_on_point(candidate)
        # get (one) point with lowest number
        # min([(countdict[x],x) for x in countdict])[1]
        point_id = min(countdict,key = lambda a: countdict.get(a))
        return self.return_point_by_id(point_id), point_id

    # Return all entries corresponding to one interface
    def return_interface(self, interface):
        self.cur.execute('select * from configpoints where lambda = ? and deactivated = 0', [interface])
        retval = []
        for row in self.cur:
            retval.append(list(row))
        return retval

    # Return all entries corresponding to one interface including deactivated points
    def return_interface_all(self, interface):
        self.cur.execute('select * from configpoints where lambda = ?', [interface])
        retval = []
        for row in self.cur:
            retval.append(list(row))
        return retval

    def return_ghost_success_count(self, interface):
        self.cur.execute('select count(*) from configpoints where lambda = ? and deactivated = 0 success = 1', [interface])
        retval = 0
        for row in self.cur:
            retval = int(row[0])
        return retval

    def return_sum_calcsteps(self):
        self.cur.execute('select sum(calcsteps) from configpoints where deactivated = 0')
        calcsteps = 0
        for row in self.cur:
            try:
                calcsteps = int(row[0])
            except:
                calcsteps = 0
        return calcsteps

    def return_nohs(self):
        self.cur.execute('select max(lambda) from configpoints')
        nohs = 0
        for row in self.cur:
            try:
                nohs = int(row[0])
            except:
                nohs = 0
        return nohs

    def return_lamlist(self):
        lamlist = []
        for at_lam in range(10):
            self.cur.execute('select lpos from configpoints')
            for row in self.cur:
                if row[0] not in lamlist:
                    lamlist.append(row[0])
        return lamlist

    def return_origin_point(self, the_point):
        origin_point = []
        self.cur.execute('select * from configpoints where configpoint = ?', [str(the_point)])
        for row in self.cur:
            origin_point = row[:]
        return origin_point

    def return_origin_point_by_id(self, the_id):
        origin_point = []
        self.cur.execute('select * from configpoints where myid = ?', [str(the_id)])
        for row in self.cur:
            origin_point = row[:]
        return origin_point

    def return_origin_id_by_id(self, the_id):
        origin_point = ''
        self.cur.execute('select origin_point from configpoints where myid = ?', [str(the_id)])
        for row in self.cur:
            origin_point = str(row[0])
        return origin_point

    def return_dest_points_by_id(self, the_id):
        dest_points = []
        self.cur.execute('select * from configpoints where origin_point = ?', [str(the_id)])
        for row in self.cur:
            dest_points.append(row[:])
        return dest_points

    def return_points_on_interface(self,interface):
        the_points = []
        self.cur.execute('select * from configpoints where lambda = ? and deactivated = 0', [interface])
        for row in self.cur:
            the_points.append(row)
        return the_points

    def return_points_on_last_interface(self):
        the_points = []
        self.cur.execute('select * from configpoints where lambda = ? and deactivated = 0', [str(self.biggest_lambda())])
        for row in self.cur:
            the_points.append(row)
        return the_points

    def return_points_on_last_interface_all(self):
        the_points = []
        self.cur.execute('select * from configpoints where lambda = ?', [str(self.biggest_lambda())])
        for row in self.cur:
            the_points.append(row)
        return the_points

    def return_runtime_list(self, the_lambda):
        rtl = []
        self.cur.execute('select runtime from configpoints where lambda = ? and deactivated = 0', [str(the_lambda)])
        for row in self.cur:
            rtl.append(row[0])
        return rtl

    def return_calcsteps_list(self, the_lambda):
        csl = []
        self.cur.execute('select calcsteps from configpoints where lambda = ? and deactivated = 0', [str(the_lambda)])
        for row in self.cur:
            csl.append(row[0])
        return csl

    # Show contents of table
    def show_table(self):
        self.cur.execute('select * from configpoints')
        for row in self.cur:
            print row
    
    def show_summary(self):
        self.cur.execute('select * from configpoints')
        tmp = -1
        countdict = {}
        for row in self.cur:
            if row[0] != tmp:
                if tmp != -1:
                    print "Configpoints on lambda" + str(tmp) + ": " + str(countdict[tmp])
                # new entry in dict
                countdict[row[0]] = 0
                tmp = row[0]
                
            countdict[row[0]] += 1
        if tmp != -1:     
            print "Configpoints on lambda" + str(tmp) + ": " + str(countdict[tmp])
    
    
    
    
    














