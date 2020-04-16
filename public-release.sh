#!/bin/bash

set -o nounset
set -o errexit

VERSION=$1
if [ -z $VERSION ]; then
  echo "Need version number as first argument"
  exit -1
fi

if [ $VERSION != -test ]; then
  if ssh snipersim@snipersim.org test -e snipersim.com/3k9Pv32Gs78s2q9L/packages/sniper-$VERSION.tgz; then
    echo "Version $VERSION already exists"
    exit -1
  fi
fi


source "$(dirname "${BASH_SOURCE}")/tools/env_setup.sh"


TEMPDIR=$(mktemp -d)
cd $TEMPDIR
echo $TEMPDIR


git clone $SNIPER_ROOT graphite
cd $TEMPDIR/graphite
SNIPER_ROOT_ORIG=$SNIPER_ROOT
SNIPER_ROOT=$(pwd)
git checkout public


if [ $VERSION != -test ]; then
LASTTAG=$(git describe --abbrev=0 --tags)
git log $LASTTAG.. || true

echo "Version $VERSION" >$TEMPDIR/commit.msg.init
echo "  * " >>$TEMPDIR/commit.msg.init
cp $TEMPDIR/commit.msg.init $TEMPDIR/commit.msg
[ -z $EDITOR ] && EDITOR=nano
$EDITOR $TEMPDIR/commit.msg
if diff -bBq $TEMPDIR/commit.msg.init $TEMPDIR/commit.msg; then echo "No changes??"; exit -1; fi

echo "Committing version $VERSION using changelog entry"
cat $TEMPDIR/commit.msg
sleep 5


mv CHANGELOG CHANGELOG.orig
cp $TEMPDIR/commit.msg CHANGELOG
echo >> CHANGELOG
cat CHANGELOG.orig >> CHANGELOG
rm CHANGELOG.orig

git add CHANGELOG
git commit -F $TEMPDIR/commit.msg
git push
git tag public-$VERSION public
git push origin public-$VERSION
(cd $SNIPER_ROOT_ORIG && git push -u origin public-$VERSION)
fi


cd $TEMPDIR
git clone ssh://atuin/afs/elis.ugent.be/group/csl/perflab/exascience/src/sniper-public.git
cd $TEMPDIR/sniper-public
# Remove all existing files so we can detect deletions
rm -rf *

FILES="common COMPILATION config CONTRIBUTORS CHANGELOG Doxyfile \
       include LICENSE LICENSE.interval Makefile.external Makefile.config NOTICE \
       pin README run-sniper record-trace scripts sift standalone test tools"

(cd $SNIPER_ROOT && git archive public) | tar x $FILES

mv Makefile.external Makefile


if [ $VERSION == -test ]; then
echo Release set up in $TEMPDIR
exit
fi

git add --all
git commit -F $TEMPDIR/commit.msg
git push origin

git remote add snipersim snipersim@snipersim.org:snipersim.com/3k9Pv32Gs78s2q9L/git/sniper.git
git push snipersim
ssh snipersim@snipersim.org 'cd ~/snipersim.com/3k9Pv32Gs78s2q9L/git/sniper.git; git update-server-info'

tar czf $TEMPDIR/sniper-$VERSION.tgz -C $TEMPDIR --exclude .git --transform "s,^sniper-public,sniper-$VERSION,S" sniper-public

scp $TEMPDIR/sniper-$VERSION.tgz snipersim@snipersim.org:snipersim.com/3k9Pv32Gs78s2q9L/packages
ssh snipersim@snipersim.org "echo sniper-$VERSION.tgz > snipersim.com/3k9Pv32Gs78s2q9L/packages/latest.txt"
ssh snipersim@snipersim.org "ln -sf sniper-$VERSION.tgz snipersim.com/3k9Pv32Gs78s2q9L/packages/sniper-latest.tgz"
