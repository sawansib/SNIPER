#!/bin/bash

INFILE="../../common/system/hooks_manager.h"
OUTFILE=hooks.h

echo "// available hooks" > "${OUTFILE}"
grep '\s\+HOOK_' "${INFILE}" | cut -d , -f 1 | tr -d ' ' | grep -v HOOK_TYPES_MAX >> "${OUTFILE}"
