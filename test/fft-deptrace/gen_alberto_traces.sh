#!/bin/bash

IN_DIR=${HOME}/traces/pb/w0-d1B
OUT_DIR=${HOME}/traces/alberto/w0-d1B

export SNIPER_ROOT=${HOME}/prog/sniper-dep-trace

NTHREADS=1
ROBSIZE=256
SNIPER_OPTS="-sprogresstrace:50000000 -cgainestown -crob -gperf_model/dram/num_controllers=1 -gperf_model/l3_cache/shared_cores=${NTHREADS}  -gperf_model/l2_cache/perfect=true -gperf_model/l3_cache/perfect=true -gperf_model/l1_icache/perfect=true  -gperf_model/dram/direct_access=true -ggeneral/enable_icache_modeling=false -gperf_model/branch_predictor/type=none -gperf_model/l1_dcache/perfect=true -gclock_skew_minimization/barrier/quantum=2147483647 -gperf_model/dtlb/size=0 -gperf_model/core/interval_timer/window_size=${ROBSIZE} -gperf_model/core/rob_timer/rs_entries=${ROBSIZE} -gperf_model/core/rob_timer/outstanding_loads=${ROBSIZE} -gperf_model/core/rob_timer/outstanding_stores=${ROBSIZE} -gperf_model/core/rob_timer/commit_width=4 -gperf_model/core/rob_timer/deptrace=true -gperf_model/core/rob_timer/deptrace_start_active=true -gperf_model/core/rob_timer/store_to_load_forwarding=false"

for t in ${IN_DIR}/* ; do
	echo $t
	TRACE_NAME=$(basename $t)
	if [ -e "${OUT_DIR}/${TRACE_NAME}" ] ; then
		echo "skipping $TRACE_NAME"
		continue
	fi

	"${SNIPER_ROOT}/run-sniper" --save-output -d "${OUT_DIR}/${TRACE_NAME}" -n ${NTHREADS} ${SNIPER_OPTS} --pinballs="${IN_DIR}/${TRACE_NAME}/pinball.address"

done
