#!/usr/bin/env python2
"""
a scoring program for evaluating GEC system output on the CoNLL-2014 Shared Task test set

contact: Courtney Napoles (napoles@cs.jhu.edu)
"""
import sys
import os
import codecs
import argparse
import numpy as np
from subprocess import Popen, PIPE
import m2scorer.scripts.levenshtein as ld
from gleu import GLEU
from m2scorer.m2scorer import load_annotation as load_m2_annotation
from imeasure.ieval import IMeasure

cwd = os.path.dirname(os.path.realpath(sys.argv[0]))

# GLOBAL VARIABLES
LEGAL_REFERENCE_NAMES = set(
    ['ALL', 'BN', 'EXPFLUENCY', 'EXPMIN', 'NUCLE', 'TURKFLUENCY', 'TURKMIN'])
# lambdas are stored in the order: lambda_rho, lambda_r
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
        [float(g[0]) for g in gleu_calculator.run_iterations(num_iterations=num_iterations,
                                                             num_references=len(references),
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


def compute_im(reference, prediction_path, debug=False):
    """get sentence-level im scores (im-correction)"""
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


def call_lt(sentences, debug=False):
    """counts errors with an external call to LanguageTool"""
    sys.stderr.write('Running LanguageTool...\n')
    if debug:
        sys.stderr.write('Java info: %s %s\n' %
                         (os.system('which java'), os.system('java -version')))
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

    parser = argparse.ArgumentParser()
    parser.add_argument('input_dir',
                        help='required argument pointing to the codalab input dir')
    parser.add_argument('output_dir',
                        help='required argument pointing to the codalab output dir')
    parser.add_argument('--im', dest='use_im', default=False, action='store_true',
                        help='score using I-measure (default False)')
    parser.add_argument('--ref', nargs='*', default=['ALL', 'EXPFLUENCY', 'BN', 'NUCLE'],
                        help='reference set(s) to use. options: ' + ', '.join(LEGAL_REFERENCE_NAMES))
    parser.add_argument('-d', '--debug', default=False, action='store_true',
                        help='print debugging messages')
    parser.add_argument('--metrics', nargs='*', default=['LT', 'M2', 'GLEU'],
                        help='which metrics to use (default: LT M2 GLEU)')
    parser.add_argument('-f', help='input file (overrides answer.txt in input_dir)')

    args = parser.parse_args()

    use_metrics = set([m.lower() for m in args.metrics])
    if args.use_im:
        use_metrics.add('im')

    if args.debug:
        sys.stderr.write('PATH: %s\n' % sys.path)
        sys.stderr.write('SCRIPT DIR: %s\n' % cwd)
        sys.stderr.write('CONTENTS SCRIPT DIR: %s\n' % os.listdir(cwd))

    use_refs = args.ref

    # set paths and load predictions
    prediction_path = os.path.join(args.input_dir, 'res/answer.txt')
    if args.f:
        prediction_path = args.f
    reference_dir = os.path.join(args.input_dir, 'ref')

    if not os.path.exists(prediction_path):
        sys.stderr.write('Error: submitted zip file does not contain answer.txt\n')
        prediction_path = None
        for fname in os.listdir(os.path.join(args.input_dir, 'res')):
            if fname.endswith('.txt'):
                prediction_path = os.path.join(args.input_dir, 'res/' + fname)
                sys.stderr.write('Found file ' + fname + '. Will try to evaluate ' + fname + '. If '
                                 'this fails, please resubmit with the submission saved as '
                                 'answer.txt.\n')
        if prediction_path is None:
            raise IOError('answer.txt not found')
    with codecs.open(prediction_path, 'r', 'utf-8') as fin:
        predictions = [l.strip() for l in fin]

    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)

    # call metrics and collect scores
    scores = []
    lt_score = call_lt(predictions, debug=args.debug) if 'lt' in use_metrics else -1
    if args.debug:
        sys.stderr.write('Reference dir: %s\n' % str([o for o in os.walk(reference_dir)]))

    for ref in use_refs:
        # get paths of reference text files for GLEU
        sys.stderr.write('Using %s as reference...\n' % ref)
        reference_files = []
        for f in os.listdir(reference_dir):
            if '.' in f:
                continue
            if ref == 'ALL' and f != 'source':
                reference_files.append(f)
            elif f.startswith(ref):
                reference_files.append(f)
        if args.debug:
            sys.stderr.write('Using references: %s\n' % str(reference_files))
        if 'im' in use_metrics:
            im = compute_im(os.path.join(reference_dir, ref + '.m2.ieval.xml'),
                            prediction_path,
                            debug=args.debug)
            scores.append(('I-measure', ref, im))
        if 'gleu' in use_metrics:
            gleu = compute_gleu(os.path.join(reference_dir, 'source'),
                                [os.path.join(reference_dir, f) for f in reference_files],
                                prediction_path)
            scores.append(('GLEU', ref, gleu))
        if 'm2' in use_metrics:
            m2 = compute_m2(os.path.join(reference_dir, ref + '.m2'),
                            predictions)
            scores.append(('M2', ref, m2))

    with open(os.path.join(args.output_dir, 'scores.txt'), 'wb') as fout:
        if 'lt' in use_metrics:
            outstr = 'LT:%f' % np.mean(lt_score)
            fout.write(outstr + '\n')
            print(outstr)
        for metric_name, reference_name, sentence_scores in scores:
            outstr = '%s_%s:%f' % (metric_name, reference_name, np.mean(sentence_scores))
            fout.write(outstr + '\n')
            print(outstr)
            if 'lt' in use_metrics:
                for r, opt_metric in enumerate(['rho', 'r']):
                    intpl_scores = (LAMBDAS[metric_name][r] * sentence_scores +
                                    (1 - LAMBDAS[metric_name][r]) * lt_score)
                    outstr = 'LT_%s_%s_%s:%f' % (metric_name, reference_name, opt_metric,
                                                 np.mean(intpl_scores))
                    print(outstr)
                    fout.write(outstr + '\n')
