# Reimplementation of Heilman et al., 2014. "Predicting Grammaticality on an Ordinal Scale"

```
@InProceedings{heilman-EtAl:2014:P14-2,
  author    = {Heilman, Michael  and  Cahill, Aoife  and  Madnani, Nitin  and  Lopez, Melissa  and  Mulholland, Matthew  and  Tetreault, Joel},
  title     = {Predicting Grammaticality on an Ordinal Scale},
  booktitle = {Proceedings of the 52nd Annual Meeting of the Association for Computational Linguistics (Volume 2: Short Papers)},
  month     = {June},
  year      = {2014},
  address   = {Baltimore, Maryland},
  publisher = {Association for Computational Linguistics},
  pages     = {174--180},
  url       = {http://www.aclweb.org/anthology/P14-2029}
}
```

Note that this implementation differs from the original: it does not include the PET parser, which is difficult to install and run.

## Requirements

- python 2
- pyenchant
- scikit-learn
- scipy
- kenlm python module (https://github.com/kpu/kenlm)
- Link Grammar Parser (5.2.5) (http://www.abisource.com/projects/link-grammar/)
- Stanford Parser (3.5.2) (http://nlp.stanford.edu/software/lex-parser.shtml)
- ~~PET parser (http://moin.delph-in.net/PetTop)~~

The model is trained on the train/dev portions of the GUG dataset (https://github.com/EducationalTestingService/gug-data). Running the pipeline will automatically train the model and report results on the GUG test set and (optionally) user-supplied sentences.

## Instructions

1. Supply native and learner English 5-gram LMs (we used Gigaword 5 and TOEFL11)
*  Set environmental variable `STANFORDHOME` to point to your installation of the Stanford parser
*  Change `LINKDIR` in `linkparser.py` to point to the link grammar parent directory
*  Run pipeline:
   ```
   sh pipeline.sh [-t test-sentences.txt] \
       [-n native_english.kenlm] \
       [-l learner_english.kenlm] \
       [-w working/directory]
   ```

---

contact: Courtney Napoles (napoles@cs.jhu.edu)
updated: 11/16/2016
