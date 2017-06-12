#!/usr/bin/env python
"""prints sentence-level scores"""
import sys
import argparse
from evaluate import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--metric', required=True,
                        help='metric to use (GLEU, IM, M2)')
    parser.add_argument('-c', '--cand', required=True,
                        help='path to candidate text (one sentence per line)')
    parser.add_argument('-o', '--orig',
                        help='path to original text (one sentence per line)')
    parser.add_argument('-r', '--ref', required=True, nargs='*',
                        help='path to reference file(s) (only GLEU uses >1 ref file)')
    args = parser.parse_args()

    with codecs.open(args.cand, 'r', 'utf-8') as fin:
        predictions = [l.strip() for l in fin]

    if args.metric.upper() == 'M2':
        scores = compute_m2(args.ref[0], predictions)
    elif args.metric.upper() == 'IM':
        scores = compute_im(args.ref[0], args.cand)
    elif args.metric.upper() == 'GLEU':
        scores = compute_gleu(args.orig, args.ref, args.cand)
    else:
        sys.stderr.write(args.metric + ' unknown. exiting')
        sys.exit(1)
    sys.stderr.write('Done\n')

    print('\n'.join([str(f) for f in scores]))
