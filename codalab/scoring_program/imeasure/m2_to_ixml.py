# -*- coding: utf-8 -*-
#!/usr/bin/python

# Copyright (c) 2015 Mariano Felice
#
# Converts an M^2 Scorer .m2 file to the I-measure XML format.
#
# This script is part of the I-measure package and is covered by the MIT License.
#

from elementtree.SimpleXMLWriter import XMLWriter
from itertools import groupby
import nltk # For tokenisation of corrections
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

help_str = \
'''Usage: python ''' + sys.argv[0] + ''' -in:<file> [-out:<file>]
\t -in:  Input .m2 file.
\t -out: Output file. Default is input filename .ieval.xml.
'''

# Globals
in_file = None
out_file = None

### FUNCTIONS ###

def cluster_has_overlap(c, e):
    return any(edit_has_overlap(e, ce) for ce in c)

def edit_has_overlap(e1, e2):
    # [0]: start offset
    # [1]: end offset
    if e1[0] == e2[0] and e1[1] == e2[1]:
        return True
    elif e1[0] == e1[1]:
        return (e1[0] > e2[0] and e1[1] < e2[1])
    elif e2[0] == e2[1]:
        return (e2[0] > e1[0] and e2[1] < e1[1])
    else:
        return (e1[1] > e2[0] and e1[1] <= e2[1]) or \
        (e1[0] >= e2[0] and e1[0] < e2[1])

def group_by_alternatives(cluster):
    alt_list = []
    # Sort and group by annotator
    cluster.sort(key=lambda x: x[-1])
    for key, group in groupby(cluster, lambda x: x[-1]):
        alt_list.append([x for x in group])
    return alt_list

def get_type(cluster):
    types = set(x[2] for x in cluster)
    return '/'.join(types)

### MAIN ###

for i in range(1,len(sys.argv)):
    if sys.argv[i].startswith("-in:"):
        in_file = sys.argv[i][4:]
    if sys.argv[i].startswith("-out:"):
        out_file = sys.argv[i][5:]

# Do we have what we need?
if not in_file:
    print help_str
    exit(0)

# Read gold standard annotations
f_in = open(in_file,"r")
src_sents = []  # Save source sentences
annotators = [] # Save annotators per sentence
ref_annot = []
s = -1
for line in f_in:
    if line[0] == "S":
        s += 1
        # Get and save original sentence
        src_sents.append(line.split()[1:])
        annotators.append(set())
        ref_annot.append([])
    elif line[0] == "A":
        # Save annotations
        tokens = line.split("|||")
        coords = tokens[0].split()
        c_start = int(coords[1])
        c_end = int(coords[2])
        etype = tokens[1]
        # Uses only the first correction
        correction = tokens[2].split("||")[0]
        # Tokenise it just in case!
        correction = tokens[2].split("||")[0]
        correction = ' '.join(nltk.word_tokenize(correction))
        required = tokens[3]
        annotator = int(tokens[5])
        annotators[s].add(annotator)
        if c_start == -1 and c_end == -1 and etype.lower() == "noop":
            # Noop --> empty set of edits (source is right)
            pass
        else:
            ref_annot[s].append([c_start, c_end, etype, correction, annotator])
f_in.close()

# Create the output XML
if not out_file:
    out_file = in_file + ".ieval.xml"
f_out = XMLWriter(out_file, "UTF-8")
f_out.declaration()
f_out.start("scripts")
f_out.start("script", id="1") # Assume only one script

# Do clustering
for s in xrange(len(ref_annot)):
    sys.stdout.write("\rSentence %s..." % (s+1))
    sys.stdout.flush()
    
    clusters = []
    # Sort edits from longest to shortest range
    ref_annot[s].sort(key=lambda x: x[0] - x[1])
    for e in ref_annot[s]: # Go through each edit
        merge = False
        for c in clusters:
            if cluster_has_overlap(c, e):
                # If the edit overlaps with an existing cluster, merge
                c.append(e)
                merge = True
                break
        if not merge:
            # If the edit couldn't be merged, create a new cluster
            clusters.append([e])
    
    # Sort clusters by start and end offsets
    clusters.sort(key=lambda x: (x[0][0],x[0][1]))
    
    # Write to XML
    f_out.start("sentence", id=str(s+1), numann=str(len(annotators[s])))
    f_out.element("text", ' '.join(src_sents[s]))
    f_out.start("error-list")

    # Clusters
    for i in xrange(len(clusters)):
        alternatives = group_by_alternatives(clusters[i])
        f_out.start("error", id=str(i+1), type=get_type(clusters[i]),
                    req=('yes' if len(alternatives)==len(annotators[s]) else 'no'))
        # Alternatives
        for j in xrange(len(alternatives)):
            f_out.start("alt", ann=str(alternatives[j][0][4]))
            # Corrections
            for k in xrange(len(alternatives[j])):
                f_out.element("c", alternatives[j][k][3], start=str(alternatives[j][k][0]), end=str(alternatives[j][k][1]))
            f_out.end("alt")
        f_out.end("error")
    f_out.end("error-list")
    f_out.end("sentence")
f_out.end("script")
f_out.end("scripts")
print ""
