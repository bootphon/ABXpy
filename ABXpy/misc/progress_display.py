# -*- coding: utf-8 -*-
"""
Created on Tue Jan  7 18:11:16 2014

:author: Thomas Schatz

This class is used to display the progress during the computing.
"""

import os
import sys
import collections


class ProgressDisplay(object):

    def __init__(self, logger=None):
        self.logger = logger
        self.message = collections.OrderedDict()
        self.total = collections.OrderedDict()
        self.count = collections.OrderedDict()
        self.init = True
        # FIXME: the goal of this is to determine whether using \033[<n>A will
        # move the standard output n lines backwards, but I'm not sure this is
        # something that would work on all tty devices ... might rather be a
        # VT100 feature, but not sure how to detect if the stdio is a VT100
        # from python ...
        try:
            self.is_tty = True if os.isatty(sys.stdin.fileno()) else False
        except ValueError:
            self.is_tty = False

    def add(self, name, message, total):
        self.message[name] = message
        self.total[name] = total
        self.count[name] = 0

    def update(self, name, amount):
        self.count[name] = self.count[name] + amount

    def display(self):
        # move back up several lines (in bash)
        m = "\033[<%d>A" % len(self.message) if self.is_tty else ''

        if self.init:
            m = ""
            self.init = False

        for message, total, count in zip(
                self.message.values(),
                self.total.values(),
                self.count.values()):
            m = m + '{} {} on {}\n'.format(message, count, total)

        if self.logger:
            pass
            # self.logger.info(m)
        else:
            sys.stdout.write(m)
            sys.stdout.flush()
