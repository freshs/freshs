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

# For checks on filesystem status
import os

#### CLASS FOR HANDLING CONFIG POINTS ON HYPERSURFACES ####
class configpoints:
    def __init__(self, server, dbfile, time):
    
        self.server = server
        
        self.base_db_name = dbfile
        self.leftPad      = 10
        self.dbfile       = dbfile+"."+(str(time).zfill(self.leftPad))

        dirName=os.path.dirname(dbfile)
	dirList=os.listdir(dirName)
	self.server.logger_freshs.info(cc.c_green + 'listing dir of DB file: ' +\
	                    dirName + ' , just before connect, gives: '+ str(dirList)+cc.reset)

	try:
	    db_size = os.path.getsize(self.dbfile)
	    self.server.logger_freshs.info(cc.c_green + 'byte size of db file: ' +\
		self.dbfile + ' was: '+ str(db_size)+cc.reset)
	except:
	    self.server.logger_freshs.debug(cc.c_magenta + 'could not test size of db file: ' +\
	         self.dbfile + cc.reset)



        # create sqlite database
        self.con, self.cur = self.connect()
        self.init_db()
        self.con_prev      = None
        self.cur_prev      = None
        self.have_pair_ij  = 0

        ###is this an existing or new database?
        self.cur.execute('select count(*) from points')
        r = self.cur.fetchone()
        self.server.logger_freshs.info(cc.c_magenta + 'DB has point count: ' +\
                                            str(r[0]) + cc.reset)

    def increment_active_db(self, new_t):

        ##close old db
        if self.con_prev:
            self.con_prev.commit()
            self.con_prev.close()

        ##move back pointer, python should do this by-reference
        self.con.commit()
        self.con_prev      = self.con
        self.cur_prev      = self.cur
        
        ##open a new db
        self.dbfile        = self.base_db_name+"."+(str(new_t).zfill(self.leftPad))
        self.con, self.cur = self.connect()
        self.init_db()
        self.clear_db()

    # Connect to database
    def connect(self):
        
        retry = 0
        
        self.server.logger_freshs.info(cc.c_magenta + 'attempting connect to db: ' +\
                                                            self.dbfile + cc.reset)
        con = sqlite3.connect(self.dbfile)
        cur = con.cursor()
 

        return con, cur

    def commit(self):
        self.con.commit()

    # Close database connection
    def close(self):
        self.cur.close()
        self.con.close()


    # Create table layout
    def init_db(self):

        try:
            self.cur.execute('create table points (lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, myid text, seed int, lambda_old int, weight real, rcval real)')
        except:
            pass

    # Create table layout
    def clear_db(self):

        try:
            self.cur.execute('drop table points') 
            self.cur.execute('create table points (lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, myid text, seed int, lambda_old int, weight real, rcval real)')
        except:
            pass



  # Add config point to database
    def add_point_ij(self, interface, newpoint, originpoint, calcsteps, ctime, runtime, success, runcount, pointid, seed, interface_prev, rcval=0.0):
        entries = []
        # Create table entries
        #for point_index in range(len(originpoint)):
        success = 0
        # check for success (important for ghost table)
        if newpoint != '':
            success = 1

        point = (interface, \
                        str(newpoint), \
                        str(originpoint), \
                        int(calcsteps), \
                        ctime, \
                        runtime, \
                        success, \
                        runcount, \
                        str(pointid), \
                        seed, \
                        interface_prev, \
                        0.0, rcval)

        ##save the point.
        entries.append(point)                         
            
        for t in entries:
            # TODO: error handling, if database is locked or so
            maxretry = 99
            attempt = 0
            writeok = 0
            while (not writeok) and (attempt < maxretry):
                try:
                    self.cur.execute('insert into points values (?,?,?,?,?,?,?,?,?,?,?,?,?)', t)
                    #self.con.commit()
                    writeok = 1
                except:
                    attempt += 1
                    self.server.logger_freshs.warn(cc.c_red + 'Could not write data to DB, retrying ' + str(maxretry) + ' times: ' + str(attempt) + '/' + str(maxretry) + cc.reset)
            if attempt >= maxretry:
                self.server.logger_freshs.warn(cc.c_red +\
                      'ERROR! Could not write data to DB:'+ self.dbfile+ cc.reset)
                exit( "Could not write" )

        del entries

    # Return number of points  on interface at time csteps
    def count_points_from_if_at_t(self,interface,csteps):

        self.cur.execute('select count(*) from points where lambda_old = ? and calcsteps = ?', [interface, csteps])
        r = self.cur.fetchone()
        return r[0]

   # Return number of points  on interface after time csteps
    def count_points_from_if_after_t(self,interface,csteps):

        self.cur.execute('select count(*) from points where lambda_old = ? and calcsteps > ?', [interface, csteps])

        r = self.cur.fetchone()
        return r[0]

    # Return number of points  on interface after time csteps
    def count_points_from_if_between_t(self,interface, csteps1, csteps2):


        self.cur.execute('select count(*) from points where lambda_old = ? and calcsteps > ? and calcsteps <= ?', [interface, csteps1, csteps2])

        r = self.cur.fetchone()
        return r[0]

    # Return number of points  on interface at previous time csteps
    def count_points_in_if_at_t(self,interface,csteps):
        self.cur_prev.execute('select count(*) from points where lambda = ? and calcsteps = ?', [interface, csteps])
        r = self.cur_prev.fetchone()
        return r[0]

    # Return number of points  on interface after time csteps
    def count_points_in_if_between_t(self,interface,csteps1, csteps2):
        self.cur_prev.execute('select count(*) from points where lambda = ? and calcsteps > ? and calcsteps <= ?', [interface, csteps1, csteps2])

        r = self.cur_prev.fetchone()
        return r[0]


    # Return random point from interface
    def return_point_by_id(self, point_id, retpoint ):

        ##do the select
        ##consider indexing the table by point id.
        self.cur_prev.execute(\
            'select configpoint, calcsteps, lambda from points where myid = ?', [str(point_id)]) 

        ##save the info
        r = self.cur_prev.fetchone() 
        #retpoint.append(ast.literal_eval(str(r[0])))
        retpoint.append(ast.eval(str(r[0])))
   
        return r[1], r[2]


    # Return a config point based on its unique id.
    def return_point_by_id(self, rp_id):

        self.cur_prev.execute('select configpoint from points where myid = ?', [rp_id])
        r = self.cur_prev.fetchone() 

        return str(r[0])

    # Return a config point based on its unique id, and time because the DB is sorted by t.
    def return_point_by_id_t(self, rp_id, t):

        #self.server.logger_freshs.warn(cc.c_red +\
        #       'reading: ' +self.prev_table +" "+str(t)+" "+str(rp_id)+cc.reset)

        self.cur_prev.execute('select configpoint from points where calcsteps = ? and myid = ?', [t, rp_id])
        r = self.cur_prev.fetchone() 

        return str(r[0])
        
    # count points linking two bins at given time
    def count_points_linking_ij(self, lambda_old, lambda_new, age_steps ):
        self.cur_prev.execute('select count(*) from points where lambda_old = ? and lambda = ? and calcsteps = ?', \
                                                        [lambda_old, lambda_new, age_steps ])
        r = self.cur_prev.fetchone()[0]
        return r

    # count points linking two bins at given time
    def count_points_linking_ij_after_t(self, lambda_old, lambda_new, min_age_steps ):
        self.cur_prev.execute('select count(*) from points where lambda_old = ? and lambda = ? and calcsteps > ?', \
                                            [lambda_old, lambda_new, min_age_steps ])
        r = self.cur_prev.fetchone()[0]
        return r

    def save_weights_of_points( self, lambda_old, lambda_new, age_steps, weight ):

        ##get a set of points which have the same weight
        self.cur_prev.execute('update points set weight = ? where lambda_old = ? and lambda = ? and calcsteps = ?', \
                         [weight, lambda_old, lambda_new, age_steps ])
        #self.con_prev.commit()

    def save_weights_of_points_after_t( self, lambda_old, lambda_new, min_age_steps, weight ):

        ##get a set of points which have the same weight

        ##this function does not scale well as the database becomes larger:
        ##consider building an index on "calcsteps"
        self.cur.execute('update points set weight = ? where calcsteps > ? and lambda_old = ? and lambda = ?', \
                          [weight, min_age_steps, lambda_old, lambda_new ])
        #self.con.commit()


    # Return number of points (nop) on interface
    def return_nop_l(self,interface):
        self.cur.execute('select count(*) from points where lambda = ?', [interface])
        retval = 0

        r = self.cur.fetchone()
        return r[0]

    # Return number of points (nop) on interface
    def return_nop(self):
        self.cur.execute('select count(*) from points')
        retval = 0

        r = self.cur.fetchone()
        return r[0]


    # Return number of points (nop) from interface
    def return_nop_lold(self,interface):
        self.cur.execute('select count(*) from points where lambda_old = ?', [interface])
        r = self.cur.fetchone()

        return r[0]


    # list of points by their seed and runid
    def return_epoch_points(self, ep_buf):

        self.cur.execute('select lambda, lambda_old, myid, seed from points')

        c = 0
        r = self.cur.fetchone()
        while r:
            if ep_buf[r[0]].has_key(r[1]):
                ep_buf[r[0]][r[1]].append((r[2], r[3]))
            else:
                ep_buf[r[0]][r[1]] = [(r[2], r[3])]
            c = c + 1
            r = self.cur.fetchone()
        return c

    def return_last_received_count(self,clname):
        self.cur.execute('select myid from points where myid like \'' + str(clname) + '%\'')
        retval = [0]
        for row in self.cur:
            retval.append(int(re.sub(str(clname) + '_','',str(row[0]))))
        return int(max(retval))

    



