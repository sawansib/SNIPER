NTHREADS=4
#NTHREADS=18
#NTHREADS_VIPS=16
ROBSIZE=256
STOP_OPTS=#--gdb #-sstop-by-icount:10000000
UOPS=true
OPTS=$(STOP_OPTS) -cgainestown -crob -gperf_model/dram/num_controllers=1 -gperf_model/l3_cache/shared_cores=$(NTHREADS)  -gperf_model/l2_cache/perfect=true -gperf_model/l3_cache/perfect=true -gperf_model/l1_icache/perfect=true  -gperf_model/dram/direct_access=true -ggeneral/enable_icache_modeling=false -gperf_model/branch_predictor/type=none -gperf_model/l1_dcache/perfect=true -gclock_skew_minimization/barrier/quantum=2147483647 -gperf_model/dtlb/size=0 -gperf_model/core/interval_timer/window_size=$(ROBSIZE) -gperf_model/core/rob_timer/rs_entries=$(ROBSIZE) -gperf_model/core/rob_timer/outstanding_loads=$(ROBSIZE) -gperf_model/core/rob_timer/outstanding_stores=$(ROBSIZE) -gperf_model/core/rob_timer/commit_width=4 -gperf_model/core/rob_timer/deptrace=true -gperf_model/core/rob_timer/store_to_load_forwarding=false -gperf_model/core/rob_timer/deptrace_microops=$(UOPS)
ROI_OPTS=$(OPTS) -gperf_model/core/rob_timer/deptrace_roi=true --roi --no-cache-warming

run_fft:
	../../run-sniper --save-output -d fft_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS) $(OPTS) -- ./FFT -p $(NTHREADS) -m 16

run_ocean:
	../../run-sniper --save-output -d ocean_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS) $(OPTS) -- ./OCEAN -p$(NTHREADS) -n258 # -p $(NTHREADS) -m 16

run_bodytrack:
	$(PARSEC_ROOT)/bin/parsecmgmt -a run -s "$(SNIPER_ROOT)/run-sniper $(ROI_OPTS) --save-output -d $(SNIPER_ROOT)/test/fft-deptrace/bodytrack_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS)" -p bodytrack -i simsmall -c gcc-hooks -n $(NTHREADS)

run_facesim:
	$(PARSEC_ROOT)/bin/parsecmgmt -a run -s "$(SNIPER_ROOT)/run-sniper $(ROI_OPTS) --save-output -d $(SNIPER_ROOT)/test/fft-deptrace/facesim_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS)" -p facesim -i simsmall -c gcc-hooks -n $(NTHREADS)

run_vips:
	$(PARSEC_ROOT)/bin/parsecmgmt -a run -s "$(SNIPER_ROOT)/run-sniper $(OPTS) --save-output -d $(SNIPER_ROOT)/test/fft-deptrace/vips_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS)" -p vips -i simsmall -c gcc-hooks -n $(NTHREADS_VIPS)

run_blackscholes:
	$(PARSEC_ROOT)/bin/parsecmgmt -a run -s "$(SNIPER_ROOT)/run-sniper $(OPTS) --save-output -d $(SNIPER_ROOT)/test/fft-deptrace/blackscholes_$(ROBSIZE)_$(NTHREADS)_$(UOPS) -n $(NTHREADS) -gperf_model/core/rob_timer/deptrace_start_active=true" -p blackscholes -i simsmall -c gcc-hooks -n $(NTHREADS)
