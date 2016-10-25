import os
import sys

with open(os.path.join(sys.argv[1], 'scores.txt'), 'r') as fin, \
     open(os.path.join(sys.argv[2], 'scores.txt'), 'w') as fout:
    for line in fin:
        fout.write('foo\n')
