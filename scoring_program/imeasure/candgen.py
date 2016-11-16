# -*- coding: utf-8 -*-
#!/usr/bin/python

# Copyright (c) 2015 Mariano Felice
#
# Generate all possible valid gold standard sentences from a set of annotations.
# Takes in an XML file in the format used by the evaluation script.
#
# This script is part of the I-measure package and is covered by the MIT License.
#

import sys
import itertools

#### AUXILIARY CLASSES ####

class SentCorrectionsIndex:
    def __init__(self):
        self.clusters = []
    
    def _mergeCorrections(self, corrections):
        index = {}
        for t_start, t_end, c in corrections:
            if t_start in index:
                if t_end in index[t_start]:
                    index[t_start][t_end] = ' '.join([index[t_start][t_end], c])
                else:
                    index[t_start][t_end] = c
            else:
                index[t_start] = {t_end: c}
        return [(a, b, index[a][b]) for a in index for b in index[a]]
    
    def addAlternatives(self, errorXMLNode, annotator=None):
        # Create a correction cluster
        cluster = set()
        
        if annotator:
            alt_iter = errorXMLNode.findall(".//alt[@ann='" + str(annotator) + "']")
        else:
            # If the correction is not compulsory (i.e. it is optional),
            # allow for an empty correction        
            if errorXMLNode.get("req") == "no":
                # An empty list is used to force an empty value in cartesian product
                cluster.add(frozenset())
            alt_iter = errorXMLNode.iter("alt")
            
        # Add all alternative corrections to it
        for alt in alt_iter:
            # Build alternative tuple
            alternative = []
            for corr in alt.iter("c"):
                alt_corr = (int(corr.get("start")), int(corr.get("end")), corr.text or '')
                alternative.append(alt_corr)
            # Merge any sequential corrections referring to the same tokens
            alternative = self._mergeCorrections(alternative)
            # Append correction alternative to cluster
            cluster.add(frozenset(alternative))
        # Append cluster to index
        self.clusters.append(cluster)

class Candidate:
    def __init__(self, tokens, edits):
        self.tokens = tokens
        self.edits = edits

#### MAIN CLASS ####

class CandidateGenerator:

    ### METHODS ###

    def correct_sentence(self, sentence, edits):
        changes = 0
        corrected = sentence[:] # Corrected sentence
        last_corrected = corrected[:] # Latest corrections
        if edits:
            # Sort edits from last to first token
            edits.sort(key = lambda x : (x[0], x[1]), reverse=True)
            for e in edits:
                last_corrected = corrected[:] # Save latest corrected version
                # Count changes
                if corrected[e[0]:e[1]] != [e[2]]:
                    changes += 1
                # Correct
                corrected[e[0]:e[1]] = e[2].split()
                # WORKAROUND FOR NUCLE!
                # This is a patch to preserve sentences that get completely deleted
                # because of some long-span errors that do not have corrections
                if corrected == []:
                    # Go back to the previous corrected version and ignore this annotation
                    corrected = last_corrected[:]
                    changes -= 1
                    continue
        corrected_string = " ".join(corrected)
        # WORKAROUND FOR NUCLE!
        # If the correction generates an empty sentence, return the original sentence
        if corrected_string.strip() == "":
            corrected_string = " ".join(sentence) 
            changes = 0
        return (corrected_string, changes)

    def get_cart_product(self, multilist):
        return itertools.product(*multilist)

    def has_duplicates(self, seq):
        seen = set()
        for x in seq:
            if x in seen: return True
            seen.add(x)
        return False

    def are_compatible(self, seq):
        # COMPATIBLE: there should be no overlapping corrections
        offset_list = [(x[0], x[1]) for x in seq]
        return not self.has_duplicates(offset_list)
        
    def flatten_list(self, seq):
        return list(itertools.chain(*seq))

    def get_candidates(self, sentElement, mix=False):
        # Don't keep duplicates
        targets = {}
        src = sentElement.find("text").text
        
        if mix:
            # Build index
            corrIndex = SentCorrectionsIndex()
            for error in sentElement.iter("error"):
                # Add corrections cluster to index
                corrIndex.addAlternatives(error)
            # Generate candidates only if there are proposed corrections
            if corrIndex.clusters:
                # Generate all possible combinations (cartesian product)
                product = self.get_cart_product(corrIndex.clusters)
                for edits in product:
                    # No need to keep distinctions about corrections now
                    edits = self.flatten_list(edits)
                    if not edits:
                        # No edits => original sentence
                        # Remember candidate
                        targets[src] = edits
                    else:
                        # Apply corrections if they are compatible
                        if self.are_compatible(edits):
                            tgt, changes = self.correct_sentence(src.split(), edits)
                            # If the candidate has been generated before...
                            if tgt in targets:
                                # Keep this new version if it requires fewer edits
                                if len(edits) < len(targets[tgt]):
                                    targets[tgt] = edits
                            else:
                                targets[tgt] = edits
                        #else:
                        #    print "EDITS ARE NOT COMPATIBLE!!!"
            else:
                return [Candidate(src.split(),[])]
        else: # Don't mix corrections
            # Generate one target per annotator (at most)
            if int(sentElement.get("numann")) <= 0:
                # No annotations => original sentence
                targets[src] = []
                sent_annotators = []
            else:
                # Get list of annotators
                sent_annotators = set(a.get("ann") for a in sentElement.iter("alt"))
                # If we don't have effective annotations for all annotators,
                # then the missing annotators think the source is ok
                if len(sent_annotators) < int(sentElement.get("numann")):
                    targets[src] = []

            for ann in sent_annotators:
                # Build index
                corrIndex = SentCorrectionsIndex()
                for error in sentElement.iter("error"):
                    # Add corrections cluster to index
                    corrIndex.addAlternatives(error, ann)
                # Generate candidate
                # Get rid of frozensets (cart_product does it above)
                edits = self.flatten_list(corrIndex.clusters)
                # No need to keep distinctions about corrections now
                edits = self.flatten_list(edits)
                if not edits:
                    # No edits => original sentence
                    # Remember candidate
                    targets[src] = edits
                else:
                    # Corrections should be compatible
                    tgt, changes = self.correct_sentence(src.split(), edits)
                    # If the candidate has been generated before...
                    if tgt in targets:
                        # Keep this new version if it requires fewer edits
                        if len(edits) < len(targets[tgt]):
                            targets[tgt] = edits
                    else:
                        targets[tgt] = edits

        # Return candidate list
        return [Candidate(t.split(), sorted(edits, key=lambda x: (x[0],x[1]))) for t, edits in targets.items()]


#### MAIN ####

if __name__ == '__main__':

    import pprint
    import xml.etree.cElementTree as ET
    
    pp = pprint.PrettyPrinter(indent=4)

    # Globals
    fn_in = None
    mix = False

    # Read parameters
    for i in range(1,len(sys.argv)):
        if sys.argv[i].startswith("-in:"):
            fn_in = sys.argv[i][4:]
        elif sys.argv[i] == "-mix":
            mix = True

    # Do we have what we need?
    if not fn_in:
        print '''Usage: python ''' + sys.argv[0] + ''' -in:<file> [-mix]
        -in  : Gold standard XML file.
        -mix : Mix corrections from different annotators to generate all possible valid target sentences.
        '''
        exit(0)

    ### PROCESS SENTENCES
    cg = CandidateGenerator()
    context = ET.iterparse(fn_in, events=("start", "end"))
    context = iter(context)
    event, root = context.next()
    # Read original sentences
    for event, elem in context:
        if event == "end":
            if elem.tag == "sentence":
                reflist = cg.get_candidates(elem, mix)
                print "[", elem.get("id"), "]", len(reflist), " generated reference(s).\n"
                print "SRC:", elem.find("text").text, "\n"
                for r in reflist:
                    print "REF:", ' '.join(r.tokens)
                    #raw_input("Press a key to continue...")
                    #sys.stdout.write("\033[A") # Go back one line
                    #sys.stdout.write(" "*30 + "\r")
                print "-" * 20
                # Free up
                elem.clear()
            elif elem.tag == "script":
                # Free up processed elements
                elem.clear()
                root.clear()

