#!/usr/bin/env python
"""
trains a model following Heilman et al. 2014. Predicting Grammaticality on an Ordinal Scale
"""

import sys
import os
import argparse
import json
import pickle
from collections import namedtuple
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import RidgeCV, LogisticRegressionCV
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score
from scipy.stats.stats import pearsonr, kendalltau

Dataset = namedtuple('Dataset', 'X y')


class FluencyModel:

    def __init__(self):
        pass

    def load_scores(self, sfile):
        """read info from gug_annotations.tsv
        the fields are Id,Sentence,Expert Judgement,Crowd Flower,Judgements,Average,Dataset
        but only Expert Judgement, Judgments, and Average"""
        self.scores = []
        with open(sfile) as f:
            f.readline()  # read header
            for l in f:
                v = l.strip().split('\t')
                # (Judgements, Average, Expert Judgement)
                self.scores.append((float(v[4]), v[5], v[2]))

    def load_vectors(self, ffile):
        """loads vectors and scores from the GUG data and sorts into train/test
        based on the gug_annotations.tsv"""
        train = Dataset([], [])
        test = Dataset([], [])

        # load features and separate into train/dev/test
        with open(ffile) as infile:
            i = 0
            infile.readline()  # read header
            for i, line in enumerate(infile):
                features = json.loads(line)
                # delete values not used in model
                del features['id']
                del features['length']
                # skip sentences that are incomplete (expert judgment = 0)
                if self.scores[i][2] == '0':
                    pass
                else:
                    d = train
                    if self.scores[i][1] == 'dev':
                        pass  # d = self.dev
                    elif self.scores[i][1] == 'test':
                        d = test
                    d.y.append(self.scores[i][0])
                    d.X.append(features)
        # scale vectors
        self.vectorizer = DictVectorizer(sparse=False)
        self.scaler = StandardScaler(with_mean=False)
        return (
            Dataset(
                self.scaler.fit_transform(self.vectorizer.fit_transform(train.X)),
                train.y),
            Dataset(
                self.scaler.transform(self.vectorizer.transform(test.X)),
                test.y))

    def load_test_data(self, path):
        """load non-GUG test data"""
        features = []
        with open(path) as f:
            for line in f:
                features = json.loads(line)
                features.append(features)
                del features['id']
                del features['length']
        return self.scaler.transform(self.vectorizer.transform(features))

    def predict(self, clf, train=None, test=None, binary=False):
        """make predictions for ordinal or binary task"""
        predictions = clf.predict(test.X)
        if not binary:
            predictions = self.rescale_predictions(clf, train.y,
                                                   clf.predict(train.X),
                                                   predictions)
        test_y = test.y
        if binary:
            prob_predict = clf.predict_proba(test.X)
            test_y = self.binarize(test.y)
            print >>sys.stderr, 'accuracy (bin) = ', accuracy_score(predictions, test_y)
            print >>sys.stderr, 'tau (bin) = ', kendalltau(predictions, test_y)
            # correlation for ordinal task
            print >>sys.stderr, 'r (ord) = ', pearsonr(prob_predict[:, 0], test.y)
            print >>sys.stderr, 'tau (ord) = ', kendalltau(prob_predict[:, 0], test.y)
        else:
            print >>sys.stderr, 'r (ord) = ', pearsonr(predictions, test_y)
            print >>sys.stderr, 'tau (ord) = ', kendalltau(predictions, test_y)
            # score for binary task
            print >>sys.stderr, 'accuracy (bin) = ', \
                accuracy_score(self.binarize(predictions), self.binarize(test_y))
            print >>sys.stderr, 'tau (bin) = ', \
                kendalltau(self.binarize(predictions), self.binarize(test_y))
        for a, b in zip(test_y, predictions):
            print a, b

    def binarize(self, y):
        """converts labels to their binary form"""
        return [1 if yy < 3.5 else 0 for yy in y]

    def mean(self, l):
        """returns mean of list"""
        return 1.0 * sum(l) / len(l)

    def sd(self, l, mean):
        """returns std dev of l"""
        return (sum((x-mean)**2 for x in l)/len(l))**0.5

    def rescale_predictions(self, clf, train_y, train_predict, test_predict):
        """recenters predictions for the ordinal task"""
        m_g = self.mean(train_y)
        sd_g = self.sd(train_y, m_g)

        m_p = self.mean(train_predict)
        sd_p = self.sd(train_predict, m_p)

        return [(y - m_p)/sd_p * sd_g + m_g for y in test_predict]

    def save_pickle(self, ordclf, binclf, target_dir):
        """dump model"""
        with open(os.path.join(target_dir, 'bin_model.pkl'), 'w') as fout:
            pickle.dump(binclf, fout)
        with open(os.path.join(target_dir, 'ord_model.pkl'), 'w') as fout:
            pickle.dump(ordclf, fout)
        with open(os.path.join(target_dir, 'vect_scale.pkl'), 'w') as fout:
            pickle.dump([self.vectorizer, self.scaler], fout)
        with open(os.path.join(target_dir, 'info'), 'w') as fout:
            fout.write('bin_coef = %s\n' % str(binclf.coef_))
            fout.write('ord_coef = %s\n' % str(ordclf.coef_))
            fout.write('command = %s\n' % ' '.join(sys.argv))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', required=True,
                        help='feature vectors')
    parser.add_argument('-s', required=True,
                        help='scores and other metadata')
    parser.add_argument('-t', nargs='*',
                        help='(optional) additionally make predictions on these data')
    parser.add_argument('-d', required=True,
                        help='destination for predictions and models')

    args = parser.parse_args()

    fm = FluencyModel()
    fm.load_scores(args.s)
    train, test = fm.load_vectors(args.f)

    print >>sys.stderr, '=== Running the ordinal task ==='
    ord_clf = RidgeCV(alphas=[10**x for x in range(-5, 5)])
    ord_clf.fit(train.X, train.y)
    print >>sys.stderr, ord_clf.coef_
    fm.predict(ord_clf, train=train, test=test)

    print >>sys.stderr, '=== Running binarized task ==='
    bin_clf = LogisticRegressionCV()
    bin_clf.fit(train.X, fm.binarize(train.y))
    print >>sys.stderr, bin_clf.coef_
    fm.predict(bin_clf, binary=True, train=train, test=test)

    fm.save_pickle(ord_clf, bin_clf, target_dir=args.d)

    if args.t is None:
        sys.exit(0)

    for nfile in args.t:
        name = os.path.basename(nfile).replace('.feat', '')
        test_vectors = fm.load_test_data(nfile)

        ord_predicts = ord_clf.predict(test_vectors)
        # rescale
        ord_predicts = fm.rescale_predictions(
            ord_clf, train.y, ord_clf.predict(train.X), ord_predicts)

        with open(os.path.join(args.d, name+'.ord'), 'w') as outf:
            for p in ord_predicts:
                outf.write('%f\n' % p)

        bin_predicts = bin_clf.predict_proba(test_vectors)
        with open(os.path.join(args.d, name+'.bin'), 'w') as outf:
            for p in bin_predicts:
                outf.write('%f\n' % p[0])
