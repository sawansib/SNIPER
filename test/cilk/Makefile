TARGET=test_sort.t
include ../shared/Makefile.shared

# SNIPER_VEC_FLAGS := -mno-sse4 -mno-sse4.1 -mno-sse4.2 -mno-sse4a -mno-avx
SNIPER_CILK_FLAGS := -g -O3 -std=c++0x  -I$(SNIPER_ROOT)/include -lm -L $(SNIPER_ROOT)/lib 
CXX=icc

test_sort.t: test_sort.cpp
	$(CXX) test_sort.cpp $(SNIPER_CILK_FLAGS) -lm -o test_sort.t

run_test_sort.t:
	CILK_NWORKERS=8 ../../run-sniper -n 8 -c gainestown -c rob --roi -- ./test_sort.t  

CLEAN_EXTRA=viz
