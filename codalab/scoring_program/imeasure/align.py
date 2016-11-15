# -*- coding: utf-8 -*-
#!/usr/bin/python

# Copyright (c) 2015 Mariano Felice
#
# Generate an exact three-way alignment using the Sum of Pairs model.
# Based on http://cs.au.dk/~peterbm/AiBS/project2/sp_exact_3.py
#
# This script is part of the I-measure package and is covered by the MIT License.
#

import numpy
import copy
import os

class Alignment:
    DUMMY = ''
    # Costs
    # MATCH < GAPCOST < MISMATCH
    # and MISMATCH < 2*GAPCOST to ensure gaps are grouped together
    # E.g. A B    NOT:   A B
    #      C -           - C
    #      A -           A -
    GAPCOST  = 2
    MISMATCH = 3
    MATCH    = 0

    def __init__(self, s1, s2, s3):
        self.cost = 0
        self.sequences = (s1, s2, s3)
        self.alignment = []
        self.compute_alignment()

    def __getitem__(self, i):
        return self.alignment[i]

    def _pairwise_cost(self, a, b):
        return self.MATCH if a == b else self.MISMATCH

    def _pairwise_cost_table(self, s1, s2):
        m = len(s1) + 1
        n = len(s2) + 1
        T = numpy.empty(shape=(m,n), dtype=float)

        T[0, 0] = 0

        for i in xrange(1,n):
            T[0, i] = i * self.GAPCOST

        for i in xrange(1,m):
            T[i, 0] = i * self.GAPCOST
            for j in xrange(1,n):
                T[i, j] = min(T[i-1, j] + self.GAPCOST,
                              T[i, j-1] + self.GAPCOST,
                              T[i-1, j-1] + self._pairwise_cost(s1[i-1], s2[j-1]))
        return T

    def _initialize_costs(self, D, s1, s2, s3):
        D[0, 0, 0] = 0

        cost_ij = self._pairwise_cost_table(s1, s2)
        for i in xrange(len(cost_ij)):
            for j in xrange(len(cost_ij[0])):
                D[i, j, 0] = cost_ij[i][j] + (i + j) * self.GAPCOST

        cost_ik = self._pairwise_cost_table(s1, s3)
        for i in xrange(len(cost_ik)):
            for k in xrange(len(cost_ik[0])):
                D[i, 0, k] = cost_ik[i][k] + (i + k) * self.GAPCOST

        cost_jk = self._pairwise_cost_table(s2, s3)
        for j in xrange(len(cost_jk)):
            for k in xrange(len(cost_jk[0])):
                D[0, j, k] = cost_jk[j][k] + (j + k) * self.GAPCOST

    def _threeway_cost_table(self):
        s1, s2, s3 = self.sequences

        n1 = len(s1) + 1
        n2 = len(s2) + 1
        n3 = len(s3) + 1

        D = numpy.empty(shape=(n1,n2,n3), dtype=int)
        self._initialize_costs(D, s1, s2, s3)

        for i in xrange(1, n1):
            for j in xrange(1, n2):
                for k in xrange(1, n3):
                    c_ij = self._pairwise_cost(s1[i-1], s2[j-1])
                    c_ik = self._pairwise_cost(s1[i-1], s3[k-1])
                    c_jk = self._pairwise_cost(s2[j-1], s3[k-1])

                    d1 = D[i-1,j-1,k-1] + c_ij + c_ik + c_jk
                    d2 = D[i-1, j-1, k] + c_ij + 2 * self.GAPCOST
                    d3 = D[i-1, j, k-1] + c_ik + 2 * self.GAPCOST
                    d4 = D[i, j-1, k-1] + c_jk + 2 * self.GAPCOST
                    d5 = D[i-1, j, k] + 2 * self.GAPCOST
                    d6 = D[i, j-1, k] + 2 * self.GAPCOST
                    d7 = D[i, j, k-1] + 2 * self.GAPCOST
                    
                    D[i, j, k] = min(d1, d2, d3, d4, d5, d6, d7)
        return D

    def _threeway_backtrace(self, D):
        la = []
        lb = []
        lc = []

        def _output(a,b,c):
            la.append(a)
            lb.append(b)
            lc.append(c)

        s1, s2, s3 = self.sequences
        i, j, k = len(s1), len(s2), len(s3)

        while i != 0 or j != 0 or k != 0:
            if i > 0 and j > 0:
                c_ij = self._pairwise_cost(s1[i-1], s2[j-1])
            if i > 0 and k > 0:
                c_ik = self._pairwise_cost(s1[i-1], s3[k-1])
            if j > 0 and k > 0:
                c_jk = self._pairwise_cost(s2[j-1], s3[k-1])
            # No gap
            if i > 0 and j > 0 and k > 0:
                if D[i, j, k] == D[i-1,j-1,k-1] + c_ij + c_ik + c_jk:
                    _output(s1[i-1], s2[j-1], s3[k-1])
                    i, j, k = i-1, j-1, k-1
                    continue
            # One gap
            if i > 0 and j > 0 and k >= 0:
                if D[i, j, k] == D[i-1, j-1, k] + c_ij + 2 * self.GAPCOST:
                    _output(s1[i-1], s2[j-1], self.DUMMY)
                    i, j, k = i-1, j-1, k
                    continue
            if i > 0 and j >= 0 and k > 0:
                if D[i, j, k] == D[i-1, j, k-1] + c_ik + 2 * self.GAPCOST:
                    _output(s1[i-1], self.DUMMY, s3[k-1])
                    i, j, k = i-1, j, k-1
                    continue
            if i >= 0 and j > 0 and k > 0:
                if D[i, j, k] == D[i, j-1, k-1] + c_jk + 2 * self.GAPCOST:
                    _output(self.DUMMY, s2[j-1], s3[k-1])
                    i, j, k = i, j-1, k-1
                    continue
            # Two gaps
            if i > 0 and j >= 0 and k >= 0:
                if D[i, j, k] == D[i-1, j, k] + 2 * self.GAPCOST:
                    _output(s1[i-1], self.DUMMY, self.DUMMY)
                    i, j, k = i-1, j, k
                    continue
            if i >= 0 and j > 0 and k >= 0:
                if D[i, j, k] == D[i, j-1, k] + 2 * self.GAPCOST:
                    _output(self.DUMMY, s2[j-1], self.DUMMY)
                    i, j, k = i, j-1, k
                    continue
            if i >= 0 and j >= 0 and k > 0:
                if D[i, j, k] == D[i, j, k-1] + 2 * self.GAPCOST:
                    _output(self.DUMMY, self.DUMMY, s3[k-1])
                    i, j, k = i, j, k-1
                    continue

        return [la[::-1], lb[::-1], lc[::-1]]

    def _pairwise_backtrace(self, D, s1, s2):
        la = []
        lb = []

        def _output(a,b):
            la.append(a)
            lb.append(b)

        i, j = len(s1), len(s2)

        while i != 0 or j != 0:
            if i > 0 and j > 0:
                c_ij = self._pairwise_cost(s1[i-1], s2[j-1])
            # No gap
            if i > 0 and j > 0:
                if D[i, j] == D[i-1,j-1] + c_ij:
                    _output(s1[i-1], s2[j-1])
                    i, j = i-1, j-1
                    continue
            # One gap
            if i > 0 and j >= 0:
                if D[i, j] == D[i-1, j] + self.GAPCOST:
                    _output(s1[i-1], self.DUMMY)
                    i, j = i-1, j
                    continue
            if i >= 0 and j > 0:
                if D[i, j] == D[i, j-1] + self.GAPCOST:
                    _output(self.DUMMY, s2[j-1])
                    i, j = i, j-1
                    continue

        return [la[::-1], lb[::-1]]

    def compute_alignment(self):
        if self.sequences[0] == self.sequences[1] == self.sequences[2]:
            # No need to do anything if all equal
            self.cost = 0
            self.alignment = self.sequences
        else:
            r, s1, s2 = None, None, None
            if self.sequences[0] == self.sequences[1]:
                r, s1, s2 = 0, 1, 2
            elif self.sequences[0] == self.sequences[2]:
                r, s1, s2 = 0, 2, 1
            elif self.sequences[1] == self.sequences[2]:
                r, s1, s2 = 1, 2, 0
            if s1 and s2:
                # Pairwise alignment is enough
                T = self._pairwise_cost_table(self.sequences[s1], self.sequences[s2])
                self.cost = 2 * T[-1,-1]
                pairwise_alignment = self._pairwise_backtrace(T, self.sequences[s1], self.sequences[s2])
                self.alignment = [None] * 3
                self.alignment[r]  = pairwise_alignment[0][:]
                self.alignment[s1] = pairwise_alignment[0][:]
                self.alignment[s2] = pairwise_alignment[1][:]
            else:
                # Three-way alignment required    
                T = self._threeway_cost_table()
                self.cost = T[-1,-1,-1]
                self.alignment = self._threeway_backtrace(T)
        
        self.length = len(self.alignment[0])

    def printme(self, headers=[], lmargin=0, rmargin=0, linespacing=0, wordspacing=1):
        alignment = copy.deepcopy(self.alignment)
        rows, columns = os.popen('stty size', 'r').read().split()
        maxcols = int(columns)-rmargin
        i = 0
        start = 0
        linelen = 0
        maxlen = []
        assert(wordspacing >= 0)
        assert(linespacing >= 0)
        wordspacing -= 1
        linespacing += 1
        # Headers?
        hlen = 0
        if headers:
            hlen += max(len(h) for h in headers) + 1
            for j in xrange(len(alignment)):
                alignment[j].insert(0, headers[j])
        # Add left margin
        if lmargin > 0:
            for j in xrange(len(alignment)):
                alignment[j].insert(0, ' ' * lmargin)
        lmargin += hlen
        while i < len(alignment[0]):
            maxlen.append(max(len(str(x[i])) for x in alignment))
            if linelen + maxlen[i] < maxcols:
                print str(alignment[0][i]).ljust(maxlen[i]) + ' ' * wordspacing,
                linelen += maxlen[i] + wordspacing + 1
            else:
                for j in xrange(1,len(alignment)):
                    print "\n", # New line
                    for k in range(start, i):
                        print str(alignment[j][k]).ljust(maxlen[k]) + ' ' * wordspacing,
                # Move to a new line
                # Add left margin
                for j in xrange(len(alignment)):
                    alignment[j].insert(i, ' ' * lmargin)
                maxlen[i] = lmargin
                print "\n" * linespacing, # New line
                print str(alignment[0][i]).ljust(maxlen[i]) + ' ' * wordspacing,
                linelen = maxlen[i] + wordspacing + 1
                start = i
            i += 1
        for j in xrange(1,len(alignment)):
            print "\n", # New line
            for k in range(start, i):
                print str(alignment[j][k]).ljust(maxlen[k]) + ' ' * wordspacing,
        print ""


if __name__ == '__main__':

    a = ["A", "B"]
    b = [     "C"]
    c = ["A",    ]

    a = raw_input("S1:").split()
    b = raw_input("S2:").split()
    c = raw_input("S3:").split()

    # Get the alignment.
    alignment = Alignment(a,b,c)
    print "COST:", alignment.cost
    print "LEN:", alignment.length
    alignment.printme(headers=["SRC:", "HYP:", "REF:"])
    
