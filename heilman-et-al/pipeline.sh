#!/usr/bin/bash
#
# Calls a pipeline to extract features and train a model for predicting grammaticality

# check for environmental variables
if [ -z $STANFORDHOME ]; then
    echo "set STANFORDHOME to point to the root directory of the Stanford parser"
    exit
fi

usage="./pipeline.sh [sentences.txt] [-n native.kenlm] [-l learner.kenlm] [-w working/dir]
  sentences.txt -- file containing tokenized sentences for testing, one sentence per line
  native.kenlm -- native English LM
  learner.kenlm -- learner English LM
  working/dir -- directory to store generated model files"


# set variables
homedir="$(cd "$(dirname "$0")"; pwd)"
wkdir=`pwd`
learnerlm="$wkdir/learner.kenlm"
nativelm="$wkdir/native.kenlm"
test=""
shift

while [ $# -gt 0 ]; do
    case "$1" in
	-l) learnerlm="$2"; shift;;
	-n) nativelm="$2"; shift;;
	-t) test="$(cd "$(dirname "$2")"; pwd)/$(basename "$2")"; shift;;
	-w) wkdir="$(cd $2; pwd)"; shift;;
	-h) echo $usage; exit 0;;
	*) echo "Invalid option"; echo $usage; exit 1;;
    esac
    shift
done

#### Prep GUG data ####

# download GUG data if necessary
if [ ! -d "$homedir/gug-data" ]; then
    echo "Downloading GUG data..."
    git clone git@github.com:EducationalTestingService/gug-data.git $homedir/gug-data
    echo "Done"
fi
# extract sentences to plain text file
tail -n +2 $homedir/gug-data/gug_annotations.tsv | cut -f 2 > $homedir/gug-data/gug_sentences.txt

#### Extract features ####
parser_cmd="java -cp $STANFORDHOME/*: edu.stanford.nlp.parser.lexparser.LexicalizedParser \
    -outputFormat \"oneline,typedDependencies\" \
    -sentences newline \
    -printPCFGkBest 1 \
    -writeOutputFiles \
    -outputFilesDirectory $wkdir/parsed \
    edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"

feat_cmd="python $homedir/feature_extractor.py \
    -p $wkdir/parsed/ \
    -d features \
    --giga $nativelm \
    --toefl $learnerlm"

mkdir $wkdir/parsed 2> /dev/null
mkdir $wkdir/features 2> /dev/null

for f in "$wkdir/gug-data/gug_sentences.txt" "$test"; do
	if [ "x$f" == "x" ]; then
		continue
	fi

    bn=`basename $f`
    # parse
    if [ ! -s $wkdir/parsed/$bn.stp ]; then
	echo "Parsing $f..."
	eval "$parser_cmd $f"
	echo "Done"
    fi
    # extract features
    if [ ! -s "$wkdir/features/$bn.json" ]; then
	echo "Extracting features from $f..."
	eval "$feat_cmd -f $f"
	echo "Done"
    fi
done

#### Train/classify ####
mkdir $wkdir/model 2> /dev/null
echo "Running model..."
test_opt=""
if [ "x$test" != "x" ]; then
	bn=`basename $test`
	test_opt="-t $wkdir/features/$bn.json"
fi
echo $test_opt
python $homedir/grammatical_model.py -f $wkdir/features/gug_sentences.txt.json \
       -s $homedir/gug-data/gug_annotations.tsv \
       -d $wkdir/model $test_opt
echo "Done. Model and predictions saved to $wkdir/model"
