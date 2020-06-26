#!/bin/bash

# Make sure all parts of Sniper are compiled before packaging

if [ ! -e lib/pin_sim.so ] || [ ! -e lib/libcarbon_sim.a ] || [ ! -e lib/sniper ] || [ ! -e config/sniper.py ]; then
  echo ERROR Sniper must be compiled before packaging. 1>&2
  exit -1
fi


# Determine package name

DATE=`date '+%Y%m%d%H%M%S'`
REV=`git rev-parse --short HEAD`
BRANCH=`git branch --no-color | grep '^* ' | cut -c3- | tr -d ' '`
NAME="graphite-${BRANCH}-${DATE}-${REV}"


# Determine which files to package

. ./config/sniper.py

FILES="run-sniper run-graphite record-trace COMPILATION lib/sniper lib/pin_sim.so lib/libcarbon_sim.a sift/recorder/sift_recorder config scripts test tools include mcpat hotspot python_kit"

if [[ $pin_home =~ ^/ ]]; then
  echo WARNING pin_home [${pin_home}] is an absolute path, Pin will not be included in the package. 1>&2
  echo You will have to install it separately on the target system and make sure config/sniper.py sets pin_home correctly. 1>&2
else
  FILES+=" ${pin_home}/pin ${pin_home}/source/include"
  FILES+=" ${pin_home}/intel64/bin ${pin_home}/intel64/runtime"
  FILES+=" ${pin_home}/extras/pinplay"
fi


# When called with -files, just output the list of files to pack

if [ "$1" == "-files" ]; then
  for F in $FILES; do
    echo $F
  done
  exit 0
fi


# Create package

DIR=`mktemp -d`
mkdir -p $DIR/graphite

tar c $FILES | tar x -C $DIR/graphite

if [ "$1" == "-" ]; then
  # stream to stdout
  tar c -C $DIR .
elif [ "$1" != "" ]; then
  # write to file
  if [[ "$1" =~ ".bz2" ]]; then
    tar cvjf $1 -C $DIR .
  else
    tar cvzf $1 -C $DIR .
  fi
else
  # write to file
  tar cvjf ${NAME}.tar.bz2 -C $DIR .
fi

rm -r $DIR
