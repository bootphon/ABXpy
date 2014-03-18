# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 18:11:16 2014

@author: Thomas Schatz
"""

import sys, collections

class ProgressDisplay(object):
    
    def __init__(self):
       self.message = collections.OrderedDict()
       self.total = collections.OrderedDict()
       self.count = collections.OrderedDict()
       self.init = True 
       

    def add(self, name, message, total):
        self.message[name] = message
        self.total[name] = total
        self.count[name] = 0
        
    def update(self, name, amount):
        self.count[name] = self.count[name]+amount
        
        
    def display(self):
        m = "\033[<%d>A" % len(self.message) # move back up several lines (in bash)
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
        time.sleep(0.1)