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
import concolors

# Parsing
import ast

#### CLASS FOR HANDLING CONFIG POINTS ON HYPERSURFACES ####
class configpoints:
    def __init__(self, server, dbfile):
    
        self.server = server
        
        # create sqlite database
        self.dbfile = dbfile
        self.con, self.cur = self.connect()
        self.active_table  = self.init_table_time(0)
        self.prev_table    = ""
        self.have_pair_ij  = 0

    def increment_active_table(self, new_t):
        self.prev_table   = self.active_table
        self.active_table = self.init_table_time(new_t) 

    # Connect to database
    def connect(self):
        try:
            self.server.logger_freshs.info(concolors.c_yellow + 'attempting connect to db: ' + self.dbfile + concolors.reset)
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
    def init_table_time(self, time):

        name = "points_"+str(time)
        self.atablename = name
        try:
            self.cur.execute('create table '+name+' (lambda int, configpoint text, origin_point text, calcsteps int, ctime real, runtime real, success int, runcount int, myid text, seed int, lambda_old int, weight real, rcval real)')
            self.con.commit()
        except:
            #print "Not creating table, already exists."
            pass

        return name

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
                    self.cur.execute('insert into '+self.active_table+' values (?,?,?,?,?,?,?,?,?,?,?,?,?)', t)
                    self.con.commit()
                    writeok = 1
                except:
                    attempt += 1
                    self.server.logger_freshs.warn(concolors.c_red + 'Could not write data to DB, retrying ' + str(maxretry) + ' times: ' + str(attempt) + '/' + str(maxretry) + concolors.reset)
            if attempt >= maxretry:
                self.server.logger_freshs.warn(concolors.c_red + 'ERROR! Could not write data to DB.' + concolors.reset)
                exit( "Could not write" )


    # Return number of points  on interface at time csteps
    def count_points_from_if_at_t(self,interface,csteps):

        self.server.logger_freshs.warn(concolors.c_red + 'X attempting to count points age ' +\
                 str(csteps) + ' in table: ' + self.active_table + concolors.reset)

        self.cur.execute('select count(*) from '+self.active_table+' where lambda_old = ? and calcsteps = ?', [interface, csteps])

        r = self.cur.fetchone()
        return r[0]

   # Return number of points  on interface after time csteps
    def count_points_from_if_after_t(self,interface,csteps):

        
        self.server.logger_freshs.warn(concolors.c_red + 'Y attempting to count points age > ' +\
                 str(csteps) + ' in table: ' + self.active_table + concolors.reset)

        self.cur.execute('select count(*) from '+self.active_table+' where lambda_old = ? and calcsteps > ?', [interface, csteps])

        r = self.cur.fetchone()
        return r[0]

    # Return number of points  on interface after time csteps
    def count_points_from_if_between_t(self,interface, csteps1, csteps2):


        self.cur.execute('select count(*) from '+self.active_table+' where lambda_old = ? and calcsteps > ? and calcsteps <= ?', [interface, csteps1, csteps2])

        r = self.cur.fetchone()
        return r[0]

    # Return number of points  on interface at time csteps
    def count_points_in_if_at_t(self,interface,csteps):
        self.cur.execute('select count(*) from '+self.prev_table+' where lambda = ? and calcsteps = ?', [interface, csteps])

        r = self.cur.fetchone()
        return r[0]

    # Return number of points  on interface after time csteps
    def count_points_in_if_between_t(self,interface,csteps1, csteps2):
        self.cur.execute('select count(*) from '+self.prev_table+' configpoints where lambda = ? and calcsteps > ? and calcsteps <= ?', [interface, csteps1, csteps2])

        r = self.cur.fetchone()
        return r[0]


    # Return random point from interface
    def return_point_by_id(self, point_id, retpoint ):

        ##do the select
        ##consider indexing the table by point id.
        self.cur.execute(\
            'select configpoint, calcsteps, lambda from '+self.prev_table+' where myid = ?', [str(point_id)]) 

        ##save the info
        r = self.cur.fetchone() 
        retpoint.append(ast.literal_eval(str(r[0])))
            
        return r[1], r[2]


    # Return a config point based on its unique id.
    def return_point_by_id(self, rp_id):

        self.cur.execute('select configpoint from '+self.prev_table+' where myid = ?', [rp_id])
        r = self.cur.fetchone() 

        return str(r[0])

    # Return a config point based on its unique id, and time because the DB is sorted by t.
    def return_point_by_id_t(self, rp_id, t):

        #self.server.logger_freshs.warn(concolors.c_red +\
        #       'reading: ' +self.prev_table +" "+str(t)+" "+str(rp_id)+concolors.reset)

        self.cur.execute('select configpoint from '+self.prev_table+' where calcsteps = ? and myid = ?', [t, rp_id])
        r = self.cur.fetchone() 

        return str(r[0])
        
    # Return random point from interface
    def return_random_point_linking_ij(self, lambda_old, lambda_new, age_steps ):

        ##create a view of the DB to save searching repeatedly for the set of candidate points
        viewname = 'v_'+str(lambda_old)+'_'+str(lambda_new)+'_'+str(age_steps)
        self.cur.execute(\
   'create temp view if not exists '+viewname+\
   ' as select * from configpoints where calcsteps = '+str(age_steps)+\
   ' and lambda = '+str(lambda_new)+\
   ' and lambda_old = '+str(lambda_old))

        ##count the allowed points
        self.cur.execute( 'select count(*) from ' + viewname)
        count=self.cur.fetchone()[0]
        if count == 0 :
            self.cur.execute('drop view if exists '+viewname)
            return None, None

        ##get a random number
        index = random.randint(0,count - 1)

        ##get the point
        ##order-by-seed is less efficient than order-by-rowid; 
        ##but should be deterministic, unlike rowid.
        self.cur.execute(\
         'select configpoint, myid from '+viewname+' order by seed limit 1 offset ?', [index])
        r = self.cur.fetchone() 
        
        ##clean up & return
        self.cur.execute('drop view if exists '+viewname)
        return str(r[0]), str(r[1])
        


    # count points linking two bins at given time
    def count_points_linking_ij(self, lambda_old, lambda_new, age_steps ):
        self.cur.execute('select count(*) from '+\
             self.prev_table+' where lambda_old = ? and lambda = ? and calcsteps = ?', \
                                                        [lambda_old, lambda_new, age_steps ])
        r = self.cur.fetchone()[0]
        return r

    # count points linking two bins at given time
    def count_points_linking_ij_after_t(self, lambda_old, lambda_new, min_age_steps ):
        self.cur.execute('select count(*) from '+\
             self.prev_table+' where lambda_old = ? and lambda = ? and calcsteps > ?', \
                                            [lambda_old, lambda_new, min_age_steps ])
        r = self.cur.fetchone()[0]
        return r

    def save_weights_of_points( self, lambda_old, lambda_new, age_steps, weight ):

        ##get a set of points which have the same weight
        self.cur.execute('update '+\
             self.active_table+' set weight = ? where lambda_old = ? and lambda = ? and calcsteps = ?', \
                                                                                        [weight, lambda_old, lambda_new, age_steps ])
        self.con.commit()

    def save_weights_of_points_after_t( self, lambda_old, lambda_new, min_age_steps, weight ):

        ##get a set of points which have the same weight

        ##this function does not scale well as the database becomes larger:
        ##consider building an index on "calcsteps"
        self.cur.execute('update '+\
             self.active_table+' set weight = ? where calcsteps > ? and lambda_old = ? and lambda = ?', \
                          [weight, min_age_steps, lambda_old, lambda_new ])
        self.con.commit()

    # Check if origin point is in database
    def origin_point_in_database(self, the_point):
        self.cur.execute('select count(origin_point) from '+self.prev_table+\
                           ' where origin_point = ?', [str(the_point)])
        for row in self.cur:
            occurrence = int(row[0])
        if occurrence >= 1:
            return 1
        else:
            return 0

    # Return number of points (nop) on interface
    def return_nop(self,interface):
        self.cur.execute('select count(*) from '+self.active_table+' where lambda = ?', [interface])
        retval = 0

        r = self.cur.fetchone()
        return r[0]

    # Return number of points (nop) from interface
    def return_nop_lold(self,interface):
        self.cur.execute('select count(*) from '+self.active_table+' where lambda_old = ?', [interface])
        r = self.cur.fetchone()

        return r[0]

    # list of points by their seed and runid
    def return_epoch_points(self, ep_buf):

        self.cur.execute('select lambda, lambda_old, myid, seed from ' + self.atablename)

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
        self.cur.execute('select myid from ' + self.atablename + ' where myid like \'' + str(clname) + '%\'')
        retval = [0]
        for row in self.cur:
            retval.append(int(re.sub(str(clname) + '_','',str(row[0]))))
        return int(max(retval))



