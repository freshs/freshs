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

reset = '\033[0;0m'
reverse = '\033[2m'
bold = '\033[1m'

c_white = '\033[37m'
c_black = '\033[30m'
c_blue = '\033[34m'
c_green = '\033[32m'
c_yellow = '\033[33m'
c_red = '\033[31m'
c_cyan = '\033[36m'
c_magenta = '\033[35m'
bg_white = '\033[47m'
bg_black = '\033[40m'
bg_blue = '\033[44m'
bg_green = '\033[42m'
bg_yellow = '\033[43m'
bg_red = '\033[41m'
bg_cyan = '\033[46m'
bg_magenta = '\033[45m'


# Textcolor
def white(text):
    return c_white + str(text) + reset
    
def black(text):
    return c_black + str(text) + reset
    
def blue(text):
    return c_white + str(text) + reset

def green(text):
    return c_green + str(text) + reset

def yellow(text):
    return c_yellow + str(text) + reset

def red(text):
    return c_red + str(text) + reset

def cyan(text):
    return c_cyan + str(text) + reset
   
def magenta(text):
    return c_magenta + str(text) + reset
    
# Backgrounds
def bg_white(text):
    return bg_white + str(text) + reset
    
def bg_black(text):
    return bg_black + str(text) + reset
    
def bg_blue(text):
    return bg_white + str(text) + reset

def bg_green(text):
    return bg_green + str(text) + reset

def bg_yellow(text):
    return bg_yellow + str(text) + reset

def bg_red(text):
    return bg_red + str(text) + reset

def bg_cyan(text):
    return bg_cyan + str(text) + reset
   
def bg_magenta(text):
    return bg_magenta + str(text) + reset



