#!/bin/bash

INFILE="../../include/sim_api.h"
OUTFILE=sim_api_doc.h

if [ ! -e "$INFILE" ] ; then
	echo "$0: Unable to find $INFILE"
	exit 2
fi

echo "// sniper/include/sim_api.h" > "${OUTFILE}"
echo >> "${OUTFILE}"
echo "// SimSetInstrumentMode options" >> "${OUTFILE}"
grep "SIM_OPT_INSTRUMENT" "${INFILE}" >> "${OUTFILE}"
echo >> "${OUTFILE}"
echo "// SimAPI commands" >> "${OUTFILE}"
grep 'define Sim' ../../include/sim_api.h | cut -d ' ' -f 2- | cut -d ')' -f 1 | grep -v SimMagic | sed 's/$/)/' >> "${OUTFILE}" 
