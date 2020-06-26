#!/bin/bash

set -o nounset
set -o errexit

source "$(dirname "${BASH_SOURCE}")/tools/env_setup.sh"

TEMPDIR=$(mktemp -d)
cd $TEMPDIR
echo $TEMPDIR


git clone $SNIPER_ROOT graphite
cd $TEMPDIR/graphite
SNIPER_ROOT_ORIG=$SNIPER_ROOT
SNIPER_ROOT=$(pwd)
git checkout intel

LASTTAG=$(git describe --abbrev=0 --tags)
git log $LASTTAG.. || true


NAME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "intel-$NAME" >$TEMPDIR/commit.msg.init
echo "  * " >>$TEMPDIR/commit.msg.init
cp $TEMPDIR/commit.msg.init $TEMPDIR/commit.msg
[ -z $EDITOR ] && EDITOR=nano
$EDITOR $TEMPDIR/commit.msg
if diff -bBq $TEMPDIR/commit.msg.init $TEMPDIR/commit.msg; then echo "No changes??"; exit -1; fi

echo "Committing using changelog entry"
cat $TEMPDIR/commit.msg
sleep 5


git tag intel-$NAME intel
git push origin intel-$NAME
git commit --allow-empty -F $TEMPDIR/commit.msg
git push
(cd $SNIPER_ROOT_ORIG && git push -u origin intel-$NAME)


cd $TEMPDIR
git clone ssh://atuin/afs/elis.ugent.be/group/csl/perflab/exascience/src/sniper-intel.git
cd $TEMPDIR/sniper-intel
# Remove all existing files so we can detect deletions
rm -rf *

FILES="common COMPILATION config CHANGELOG Doxyfile \
       include LICENSE LICENSE.interval Makefile.external Makefile.config NOTICE \
       pin README run-sniper record-trace scripts sift standalone test tools"

(cd $SNIPER_ROOT && git archive intel) | tar x $FILES

mv Makefile.external Makefile

git add --all
git commit -F $TEMPDIR/commit.msg
git push origin
