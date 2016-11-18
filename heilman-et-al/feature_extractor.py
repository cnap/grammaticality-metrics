#!/usr/bin/env python
"""
extracts features from sentences
following Heilman et al. 2014. Predicting Grammaticality on an Ordinal Scale.
"""
import os
import sys
import json
import argparse
import traceback
import itertools
import kenlm
import enchant
from math import log
from collections import Counter
from linkparser import LinkParser


# features used in heilman et al. 2014
HPSG_FEATURES = set(['trees', 'unify cost succ', 'unify cost fail,' 'unifications succ',
                     'unifications fail', 'subsumptions succ', 'subsumptions fail', 'words',
                     'words pruned', 'aedges', 'pedges', 'upedges', 'raedges', 'rpedges', 'medges'])


class TooLongError(Exception):
    """error for sentences that were too long to parse"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class FeatureLoader:
    """loads features for sentences"""

    def __init__(self):
        """init dictionary"""
        # note that this dict recognizes more british spellings than en_US but not all
        self.dict = enchant.Dict('en')

    def load_link_parser(self, path):
        """loads link parser"""
        self.lparser = LinkParser(path=path)

    def process_line(self, line):
        """returns feature dict for line"""
        line = line.strip()
        tokens = line.lower().split()
        features = {'length': len(tokens)}
        if len(line) == 0:
            return features
        try:
            features.update(self.feats_spelling(tokens))
        except:
            print >>sys.stderr, 'Error extracting spelling feats'
            print >>sys.stderr, traceback.format_exc()
        try:
            features.update(self.feats_link(' '.join(tokens)))
        except:
            print >>sys.stderr, 'Error extracting link feats'
            print >>sys.stderr, traceback.format_exc()
        try:
            features.update(self.feats_ngram_lm(tokens))
        except:
            print >>sys.stderr, 'Error extracting ngram/lm feats'
            print >>sys.stderr, traceback.format_exc()
        return features

    def process_file(self, fpath):
        """iterate through file and extract features by line"""
        all_features = []
        with open(fpath) as f:
            for i, l in enumerate(f):
                if i % 100 == 0:
                    print i
                all_features.append(self.process_line(l))

    def feats_spelling(self, tokens):
        """get spelling features"""
        n = 0
        miss = 0
        for s in tokens:
            if s.isalpha():
                n += 1
                if not self.dict.check(s):
                    miss += 1
        return {'num_miss': miss,
                'prop_miss': 1.0 * miss / max(1, n),
                'log_miss': log(miss + 1)}

    def load_lms(self, gpath, tpath):
        """load language models"""
        self.gigalm = kenlm.LanguageModel(gpath)
        self.toefllm = kenlm.LanguageModel(tpath)

    def get_ngram_prob(self, tokens):
        """get smoothed ngram prob from gigaword LM"""
        return self.gigalm.score(' '.join(tokens), bos=False, eos=False)

    def get_sent_prob(self, tokens, lm):
        oovs = 0
        score = 0
        for s in lm.full_scores(' '.join(tokens)):
            if s[2]:
                oovs += 1
            score += s[0]
        return oovs, score

    def feats_ngram_lm(self, tokens):
        """extract ngram and lm features"""
        features = {}
        for n in range(1, 4):
            if n > len(tokens):
                continue
            ngrams = Counter([tuple(tokens[i:i+n]) for i in xrange(len(tokens) + 1 - n)])
            probabilities = [self.get_ngram_prob(ng) for ng in ngrams]
            features['min_s_%d' % n] = min(probabilities)
            features['max_s_%d' % n] = max(probabilities)
            features['sum_s_%d' % n] = sum(probabilities) / sum(ngrams.values())
        features['giga_oov'], features['giga_p'] = self.get_sent_prob(tokens, self.gigalm)
        features['toefl11_oov'], features['toefl11_p'] = self.get_sent_prob(tokens, self.toefllm)
        return features

    def feats_link(self, l):
        """extract link parser feature"""
        return {'complete_link': self.lparser.has_parse(l)}

    def get_next_block(self, infile):
        """return the next block of lines in a file until a blank line is read
        specifically for dealing with the parser output"""
        lines = None
        while True:
            l = infile.readline().strip()
            if l.strip() == '(())':
                raise TooLongError('Sentence too long to parse')
            if not l or len(l) == 0:
                return lines
            if lines is None:
                lines = []
            lines.append(l)
        return lines

    def load_parse_features(self, f):
        """read the stanford parser output to get parse features"""
        ret = []
        with open(f) as infile:
            while True:
                try:
                    next_parse = self.get_next_block(infile)
                except TooLongError:
                    ret.append(None)
                    continue
                if not next_parse:
                    break
                if next_parse[0].startswith('#'):
                    features = {}
                    features['parse'] = next_parse[1]
                    if next_parse[0].endswith('NA'):
                        continue
                    features['parse_score'] = float(next_parse[0].split()[-1])
                    features['sentential_top_node'] = next_parse[1].split()[1][1] == 'S'
                    features['dep_count'] = sum(
                        [1 if l.startswith('dep') else 0 for l in next_parse[2:]])
                    ret.append(features)
        return ret

    def load_hpsg_features(self, fpath):
        """given a path to the output of ./cheap, return a list of dictionaries that contain the
        specified features of each sentence"""
        features = None
        for line in open(fpath):
            if ':' not in line:
                continue
            key, value = line.split(':', 1)
            if key == 'id':
                # marks a new sentence
                if features:
                    yield(features)
                features = {}
            elif key in HPSG_FEATURES:
                features[key] = log(value + 1)
        yield(features)


def check_path(cwd, f):
    """get absolute path"""
    if f[0] != '/':
        return os.path.join(cwd, f)
    return f

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--files', nargs='*',
                        help='file(s) to extract features from')
    parser.add_argument('-p', '--parse',
                        help='directory containing the parser outputs (from call_parser.sh)')
    parser.add_argument('-d', '--dest',
                        help='directory to write features')
    parser.add_argument('--giga',
                        help='path to Gigaword (native English) lm')
    parser.add_argument('--toefl',
                        help='path to TOEFL (non-native English) lm')
    parser.add_argument('--link',
                        help='path to link parser home directory')
    parser.add_argument('--cheap',
                        help='directory containing cheap outputs')

    args = parser.parse_args()

    fl = FeatureLoader()

    cwd = os.getcwd()

    try:
        os.mkdir(args.dest)
    except:
        pass
    fl.load_lms(args.giga, args.toefl)

    # after loading the link parser, must use absolute paths because linkparser changes the cwd
    fl.load_link_parser(args.link)

    for f in args.files:
        base = os.path.basename(f)
        print >>sys.stderr, 'Loading features from', f
        outpath = os.path.join(check_path(cwd, args.dest), base+'.json')
        with open(outpath, 'w') as outfile, \
             open(check_path(cwd, f)) as infile:
            # use iterators that return None if the parsed or cheap features are not defined
            # will skip any feature extraction if the parse features are not present
            if args.parse:
                all_parse_features = fl.load_parse_features(
                    os.path.join(check_path(cwd, args.parse), base + '.stp'))
            else:
                all_parse_features = itertools.repeat(None)
            if args.cheap:
                all_cheap_features = fl.load_hpsg_features(
                    os.path.join(check_path(cwd, args.cheap), base + '.cheap'))
            else:
                all_cheap_features = itertools.repeat(None)

            for i, (parse_features, cheap_features, line) in enumerate(
                    zip(all_parse_features, all_cheap_features, infile)):
                if i % 100 == 0:
                    print i
                features = {'id': base + '.%d' % i}
                if parse_features:
                    features.update(parse_features)
                    features.update(fl.process_line(line))
                    if cheap_features:
                        features.update(cheap_features)
                    # normalize appropriate features by length
                    for s in ['parse_score', 'giga_p', 'toefl11_p']:
                        try:
                            features[s] = features[s] / max(1, features['length'])
                        except:
                            pass
                    del features['parse']
                outfile.write(json.dumps(features) + '\n')
        print >>sys.stderr, 'Done. features saved to ' + outpath
