# Metrics for evaluating grammatical error corrections

These metrics were used in
[Courtney Napoles, Keisuke Sakaguchi, and Joel Tetreault. _There's No Comparison: Reference-less Evaluation Metrics in Grammatical Error Correction_. EMNLP 2016](https://www.aclweb.org/anthology/D/D16/D16-1228.pdf)

If you use this code or the accompanying CodaLab evaluation, please cite:
```
@InProceedings{napoles-sakaguchi-tetreault:2016:EMNLP2016,
  author    = {Napoles, Courtney  and  Sakaguchi, Keisuke  and  Tetreault, Joel},
  title     = {There's No Comparison: Reference-less Evaluation Metrics in Grammatical Error Correction},
  booktitle = {Proceedings of the 2016 Conference on Empirical Methods in Natural Language Processing},
  month     = {November},
  year      = {2016},
  address   = {Austin, Texas},
  publisher = {Association for Computational Linguistics},
  pages     = {2109--2115},
  url       = {https://aclweb.org/anthology/D16-1228}
}
```
## Online evaluation

The CodaLab evaluation can be used for to evaluate grammatical error correcions of the CoNLL-2014 shared task test set.

https://competitions.codalab.org/competitions/15475

## Contents

1. `codalab/`
   - Code for evaluating GEC output of the CoNLL 2014 test set using combination of metrics and reference sets.
   - The platform for scoring output can be found at https://competitions.codalab.org/competitions/15475
   - This contains the an error-count method using [Language Tool](https://languagetool.org/) and interpolations of LT with existing GEC metrics GLEU, I-measure, and M2.
2. `heilman-et-al/`
   -  A linguistic feature-based model
   - a slightly modified implementation of Heilman et al. (2014), [*Predicting Grammaticality on an Ordinal Scale*](http://www.aclweb.org/anthology/P14-2029).
