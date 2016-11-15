#!/usr/bin/env python2
"""
A scoring program for evaluating GEC system output on the CoNLL-2014 Shared Task test set.
Requires python2 as the metric modules are not python3 compliant.
"""
__author__ = 'Courtney Napoles'
__date__ = '2016-11-04'
__email__ = 'napoles@cs.jhu.edu'
__usage__ = 'python evaluate.py input-dir output-dir'

import sys
import os
import codecs
from subprocess import Popen, PIPE
import numpy as np
import m2scorer.scripts.levenshtein as ld
from detokenize import Detokenizer
from gleu import GLEU
from m2scorer.m2scorer import load_annotation as load_m2_annotation
from imeasure.ieval import IMeasure

skip_im = True
debug = False

cwd = os.path.dirname(os.path.realpath(sys.argv[0]))
if debug:
    sys.stderr.write('PATH: %s\n' % sys.path)
    sys.stderr.write('SCRIPT DIR: %s\n' % cwd)
    sys.stderr.write('CONTENTS SCRIPT DIR: %s\n' % os.listdir(cwd))

# GLOBAL VARIABLES
REF_NAMES = ['NUCLE', 'EXPFLUENCY', 'EXPMIN', 'TURKMIN', 'TURKFLUENCY']
## lambdas are stored in the order: lambda_rho, lambda_r
LAMBDAS = {'GLEU': (0.04, 0.09),
           'I-measure': (0.01, 0.01),
           'M2': (0, 0)}


def compute_gleu(source, references, prediction_path):
    """get sentence-level gleu scores"""
    sys.stderr.write('Running GLEU...\n')
    gleu_calculator = GLEU(4)
    gleu_calculator.load_sources(source)
    num_iterations = 200
    gleu_calculator.load_references(references)
    return np.array(
        [float(g[0]) for g in gleu_calculator.run_iterations(num_iterations,
                                                             len(references),
                                                             source=source,
                                                             hypothesis=prediction_path,
                                                             per_sent=True)])


def compute_m2(reference, predictions):
    """get sentence-level m2 scores"""
    sys.stderr.write('Running M2...\n')
    source_sentences, gold_edits = load_m2_annotation(reference)
    m2 = [l for l in ld.batch_multi_pre_rec_f1(predictions,
                                               source_sentences,
                                               gold_edits)]
    return np.array(m2)


def compute_im(reference, prediction_path, skip=False):
    """get sentence-level im scores (im-correction)"""
    if skip:
        return None
    sys.stderr.write('Running I-measure (note that this may take several minutes)...\n')
    im = IMeasure()
    im.mix = False
    im.file_hyp = prediction_path
    im.file_ref = reference
    im.per_sent = True
    if debug:
        im.verbose, im.v_verbose = True, True
    im_result = [i for i in im.run()]
    return np.array(im_result)


def call_lt(_sentences):
    """counts errors with an external call to LanguageTool"""
    sys.stderr.write('Running LanguageTool...\n')
    detokenizer = Detokenizer()
    sentences = [detokenizer.detokenize(sent) for sent in _sentences]
    if debug:
        sys.stderr.write('Java info: %s %s\n' % (os.system('which java'), os.system('java -version')))
    process = Popen(['java', '-Dfile.encoding=utf-8',
                     '-jar', os.path.join(cwd, 'LanguageTool-3.1/languagetool-commandline.jar'),
                     '-d', 'COMMA_PARENTHESIS_WHITESPACE,WHITESPACE_RULE,' +
                     'EN_UNPAIRED_BRACKETS,EN_QUOTES',
                     '-b', '-l', 'en-US', '-c', 'utf-8'],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE)
    ret = process.communicate(input=('\n'.join(sentences)).encode('utf-8'))
    if debug:
        sys.stderr.write('LT out: %s\n' % str(ret))
    counts = [0] * len(sentences)
    for l in ret[0].split('\n'):
        if 'Rule ID' in l:
            ll = l.split()
            ind = (int(ll[2][:-1]) - 1)
            counts[ind] += 1
    return np.array(counts)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.stderr.write('Usage: python evaluate.py input-dir output-dir [--im] [--ref:NUCLE|EXPFLUENT|EXPMIN|TURKFLUENT|TURKMIN] [-d]\n')
        sys.exit(0)

    # setup paths and load predictions
    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    use_refs = REF_NAMES

    if len(sys.argv) > 3:
        for arg in sys.argv[3:]:
            if arg == '--im':
                skip_im = False
            elif arg.startswith('--ref'):
                use_refs = [arg.split(':')[1]]
            elif arg == '-d':
                debug = True

    prediction_path = os.path.join(input_dir, 'res/answer.txt')
    reference_dir = os.path.join(input_dir, 'ref')

    with codecs.open(prediction_path, 'r', 'utf-8') as fin:
        predictions = [l.strip() for l in fin]

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # call metrics and colect scores
    scores = []
    lt_score = call_lt(predictions)
    if debug:
        sys.stderr.write('Reference dir: %s\n' % str([o for o in os.walk(reference_dir)]))

    for ref in use_refs:
        im = compute_im(os.path.join(reference_dir, ref + '.m2.ieval.xml'),
                        prediction_path, skip=skip_im)
        if im is not None:
            scores.append(('I-measure', ref, im))
        gleu = compute_gleu(os.path.join(reference_dir, 'source'),
                            [os.path.join(reference_dir, ref + anno) for anno in 'AB'],
                            prediction_path)
        scores.append(('GLEU', ref, gleu))
        m2 = compute_m2(os.path.join(reference_dir, ref + '.m2'),
                        predictions)
        scores.append(('M2', ref, m2))

    with open(os.path.join(output_dir, 'scores.txt'), 'wb') as fout:
        outstr = 'LT:%f' % np.mean(lt_score)
        fout.write(outstr + '\t')
        print(outstr)
        for metric_name, reference_name, sentence_scores in scores:
            outstr = '%s,%s:%f' % (metric_name, reference_name, np.mean(sentence_scores))
            fout.write(outstr + '\n')
            print(outstr)
            for r, opt_metric in enumerate(['rho', 'r']):
                intpl_scores = (LAMBDAS[metric_name][r] * sentence_scores +
                                (1 - LAMBDAS[metric_name][r]) * lt_score)
                outstr = 'LT+%s,%s,%s:%f' % (metric_name, reference_name, opt_metric,
                                             np.mean(intpl_scores))
                print(outstr)
                fout.write(outstr + '\n')
