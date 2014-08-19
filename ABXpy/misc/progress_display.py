# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 18:11:16 2014

:author: Thomas Schatz

This class is used to display the progress during the computing.
"""

import os, sys, collections

class ProgressDisplay(object):
    
    def __init__(self):
       self.message = collections.OrderedDict()
       self.total = collections.OrderedDict()
       self.count = collections.OrderedDict()
       self.init = True 
       if os.isatty(sys.stdin.fileno()): #FIXME the goal of this is to determine whether using \033[<n>A will move the standard output n lines backwards, but I'm not sure this is something that would work on all tty devices ... might rather be a VT100 feature, but not sure how to detect if the stdio is a VT100 from python ...
           self.is_tty = True
       else:
           self.is_tty = False       

    def add(self, name, message, total):
        self.message[name] = message
        self.total[name] = total
        self.count[name] = 0
        
    def update(self, name, amount):
        self.count[name] = self.count[name]+amount        
        
    def display(self):
        if self.is_tty:
            m = "\033[<%d>A" % len(self.message) # move back up several lines (in bash)
        else:
            m = ""
        if self.init:
            m = ""
            self.init = False
        for message, total, count in zip(self.message.values(), self.total.values(), self.count.values()):  
            m = m + "%s %d on %d\n" % (message, count, total)
        sys.stdout.write(m)
        sys.stdout.flush()        
    
    
# Test    
import time
    
def testProgressDisplay():
    
    d=ProgressDisplay()
    d.add('m1', 'truc 1', 12)
    d.add('m2', 'truc 2', 48)
    d.add('m3', 'truc 3', 24)
    
    for i in range(12):
        d.update('m1', 1)
        d.update('m2', 4)
        d.update('m3', 2)
        d.display()
        time.sleep(0.1)# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 18:11:16 2014

:author: Thomas Schatz

This class is used to display the progress during the computing.
"""

import os
import sys
import collections


class ProgressDisplay(object):

    def __init__(self):
        self.message = collections.OrderedDict()
        self.total = collections.OrderedDict()
        self.count = collections.OrderedDict()
        self.init = True
        # FIXME the goal of this is to determine whether using \033[<n>A will
        # move the standard output n lines backwards, but I'm not sure this is
        # something that would work on all tty devices ... might rather be a
        # VT100 feature, but not sure how to detect if the stdio is a VT100
        # from python ...
        if os.isatty(sys.stdin.fileno()):
            self.is_tty = True
        else:
            self.is_tty = False

    def add(self, name, message, total):
        self.message[name] = message
        self.total[name] = total
        self.count[name] = 0

    def update(self, name, amount):
        self.count[name] = self.count[name] + amount

    def display(self):
        if self.is_tty:
            # move back up several lines (in bash)
            m = "\033[<%d>A" % len(self.message)
        else:
            m = ""
        if self.init:
            m = ""
            self.init = False
        for message, total, count in zip(self.message.values(),
                                         self.total.values(),
                                         self.count.values()):
            m = m + "%s %d on %d\n" % (message, count, total)
        sys.stdout.write(m)
        sys.stdout.flush()


# Test
import time


def testProgressDisplay():

    d = ProgressDisplay()
    d.add('m1', 'truc 1', 12)
    d.add('m2', 'truc 2', 48)
    d.add('m3', 'truc 3', 24)

    for i in range(12):
        d.update('m1', 1)
        d.update('m2', 4)
        d.update('m3', 2)
        d.display()
        time.sleep(0.1)
