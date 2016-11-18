#!/usr/bin/env python
"""interfaces with linkgrammar"""
import os
import sys
from linkgrammar import *

# change this to the absolute path of the linkgrammar installation
LINKDIR = os.path.join(os.path.dirname(sys.argv[0]), 'link-grammar-5.2.5')


class LinkParser:

    def __init__(self, path=None):
        """initialize parser. need to cd into the linkgrammar home dir"""
        if path is None:
            os.chdir(LINKDIR)
        else:
            os.chdir(path)
        self.p = Parser()

    def has_parse(self, s):
        """returns True if a parse was found for a sentence"""
        return len(self.p.parse_sent(s)) > 0
