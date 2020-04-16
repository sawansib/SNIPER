#!/usr/bin/env python

# encola.py OUTS_DIR_BASE ID MIN_SEED MAX_SEED

from sys import argv, stdout
from os import getenv, environ, path, makedirs, getcwd, chdir, fdopen, chmod
import stat
from subprocess import Popen, PIPE
from tempfile import mkstemp
import math

if len(argv) < 3:
    raise "Faltan argumentos"

outs_dir_base=argv[1]
id=argv[2]

if len(argv) == 5:
    min_seed = int(argv[3])
    max_seed = int(argv[4])
elif len(argv) == 6:
    min_seed = int(argv[3])
    max_seed = int(argv[4])
    skip_set_file = argv[5]
elif len(argv) == 3:
    min_seed = 0
    max_seed = 0
elif len(argv) == 4:
    raise "min_seed especificado sin max_seed"
else:
    raise "Demasiados argumentos"

skip_set_file = None
sniperexec = "/home/users/ssingh/sniper_v2/run-sniper"
sniperoptspre = "-cgainestown -crob -gperf_model/dram/num_controllers=1 -gperf_model/l3_cache/shared_cores="
sniperoptspost = " -gperf_model/l2_cache/perfect=true -gperf_model/l3_cache/perfect=true -gperf_model/l1_icache/perfect=true  -gperf_model/dram/direct_access=true -ggeneral/enable_icache_modeling=false -gperf_model/branch_predictor/type=none -gperf_model/l1_dcache/perfect=true -gclock_skew_minimization/barrier/quantum=2147483647 -gperf_model/dtlb/size=0 -gperf_model/core/interval_timer/window_size=256 -gperf_model/core/rob_timer/rs_entries=256 -gperf_model/core/rob_timer/outstanding_loads=256 -gperf_model/core/rob_timer/outstanding_stores=256 -gperf_model/core/rob_timer/commit_width=4 -gperf_model/core/rob_timer/deptrace=true -gperf_model/core/rob_timer/store_to_load_forwarding=false -gperf_model/core/rob_timer/deptrace_microops=true"
# Enable it to trace the whole app from start.
#sniperoptsroi = "-gperf_model/core/rob_timer/deptrace_start_active=false -gperf_model/core/rob_timer/deptrace_roi=true --no-cache-warming"
# Enable it to trace just from/to the RMS marks
sniperoptsroi = "-gperf_model/core/rob_timer/deptrace_start_active=true --no-cache-warming"
# Other tries
#sniperoptsroi = "-gperf_model/core/rob_timer/deptrace_start_active=false -gperf_model/core/rob_timer/deptrace_roi=false --no-cache-warming"
#sniperoptsroi = "-gperf_model/core/rob_timer/deptrace_start_active=false -gperf_model/core/rob_timer/deptrace_roi=true --roi --no-cache-warming"
benchdir = "/home/users/ssingh/"

vars = {
    "bakery": ["micro-benchs/benchs/bakery", "./BAKERY -p", " -n 100"],
    "barriers": ["micro-benchs/benchs/barriers", "./BARRIERS -p", " -n 50"],
    "dclocking": ["micro-benchs/benchs/dclocking", "./DCL_SINGLETON -p", " -n 100"],
    "locks": ["micro-benchs/benchs/locks", "./LOCKS -p", " -n 100"],
    "locks2": ["micro-benchs/benchs/locks2", "./LOCKS -p", " -n 100"],
    "mcsqueuelock": ["micro-benchs/benchs/mcsqueuelock", "./MCSQUEUELOCK -p", " -n 20"],
    "postgresql": ["micro-benchs/benchs/postgresql", "./POSTGRESQL -p", " -n 100"],

    "barnes": ["splash2/codes/apps/barnes", "./BARNES < inputs/n16384-p", ""],
    "cholesky": ["splash2/codes/kernels/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fft": ["splash2/codes/kernels/fft", "./FFT -p", " -m16"],
    "fmm": ["splash2/codes/apps/fmm", "./FMM < inputs/input.", ".16384"],
    "lu": ["splash2/codes/kernels/lu/contiguous_blocks", "./LU -p", " -n512"],
    "lunc": ["splash2/codes/kernels/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "ocean": ["splash2/codes/apps/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceannc": ["splash2/codes/apps/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosity": ["splash2/codes/apps/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radix": ["splash2/codes/kernels/radix", "./RADIX -p", " -n1048576"],
    "raytrace": ["splash2/codes/apps/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrend": ["splash2/codes/apps/volrend", "./VOLREND ", " inputs/head"],
    "waternsq": ["splash2/codes/apps/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "watersp": ["splash2/codes/apps/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "barnesRC": ["splash2-RC/codes/apps/barnes", "./BARNES < inputs/n16384-p", ""],
    "choleskyRC": ["splash2-RC/codes/kernels/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fftRC": ["splash2-RC/codes/kernels/fft", "./FFT -p", " -m16"],
    "fmmRC": ["splash2-RC/codes/apps/fmm", "./FMM < inputs/input.", ".16384"],
    "luRC": ["splash2-RC/codes/kernels/lu/contiguous_blocks", "./LU -p", " -n512"],
    "luncRC": ["splash2-RC/codes/kernels/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "oceanRC": ["splash2-RC/codes/apps/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceanncRC": ["splash2-RC/codes/apps/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosityRC": ["splash2-RC/codes/apps/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radixRC": ["splash2-RC/codes/kernels/radix", "./RADIX -p", " -n1048576"],
    "raytraceRC": ["splash2-RC/codes/apps/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrendRC": ["splash2-RC/codes/apps/volrend", "./VOLREND ", " inputs/head"],
    "waternsqRC": ["splash2-RC/codes/apps/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "waterspRC": ["splash2-RC/codes/apps/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "barnesForward": ["splash3-forward/codes/apps-locks/barnes", "./BARNES < inputs/n16384-p", ""],
    "choleskyForward": ["splash3-forward/codes/kernels-locks/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fftForward": ["splash3-forward/codes/kernels-locks/fft", "./FFT -p", " -m16"],
    "fmmForward": ["splash3-forward/codes/apps-locks/fmm", "./FMM < inputs/input.", ".16384"],
    "luForward": ["splash3-forward/codes/kernels-locks/lu/contiguous_blocks", "./LU -p", " -n512"],
    "luncForward": ["splash3-forward/codes/kernels-locks/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "oceanForward": ["splash3-forward/codes/apps-locks/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceanncForward": ["splash3-forward/codes/apps-locks/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosityForward": ["splash3-forward/codes/apps-locks/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radixForward": ["splash3-forward/codes/kernels-locks/radix", "./RADIX -p", " -n1048576"],
    "raytraceForward": ["splash3-forward/codes/apps-locks/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrendForward": ["splash3-forward/codes/apps-locks/volrend", "./VOLREND ", " inputs/head"],
    "waternsqForward": ["splash3-forward/codes/apps-locks/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "waterspForward": ["splash3-forward/codes/apps-locks/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "barnesDRF": ["splash2-DRF-locks/codes/apps/barnes", "./BARNES < inputs/n16384-p", ""],
    "choleskyDRF": ["splash2-DRF-locks/codes/kernels/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fftDRF": ["splash2-DRF-locks/codes/kernels/fft", "./FFT -p", " -m16"],
    "fmmDRF": ["splash2-DRF-locks/codes/apps/fmm", "./FMM < inputs/input.", ".16384"],
    "luDRF": ["splash2-DRF-locks/codes/kernels/lu/contiguous_blocks", "./LU -p", " -n512"],
    "luncDRF": ["splash2-DRF-locks/codes/kernels/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "oceanDRF": ["splash2-DRF-locks/codes/apps/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceanncDRF": ["splash2-DRF-locks/codes/apps/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosityDRF": ["splash2-DRF-locks/codes/apps/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radixDRF": ["splash2-DRF-locks/codes/kernels/radix", "./RADIX -p", " -n1048576"],
    "raytraceDRF": ["splash2-DRF-locks/codes/apps/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrendDRF": ["splash2-DRF-locks/codes/apps/volrend", "./VOLREND ", " inputs/head"],
    "waternsqDRF": ["splash2-DRF-locks/codes/apps/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "waterspDRF": ["splash2-DRF-locks/codes/apps/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "barnesxDRF": ["splash3-xDRF/codes/apps-locks/barnes", "./BARNES < inputs/n16384-p", ""],
    "choleskyxDRF": ["splash3-xDRF/codes/kernels-locks/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fftxDRF": ["splash3-xDRF/codes/kernels-locks/fft", "./FFT -p", " -m16"],
    "fmmxDRF": ["splash3-xDRF/codes/apps-locks/fmm", "./FMM < inputs/input.", ".16384"],
    "luxDRF": ["splash3-xDRF/codes/kernels-locks/lu/contiguous_blocks", "./LU -p", " -n512"],
    "luncxDRF": ["splash3-xDRF/codes/kernels-locks/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "oceanxDRF": ["splash3-xDRF/codes/apps-locks/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceanncxDRF": ["splash3-xDRF/codes/apps-locks/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosityxDRF": ["splash3-xDRF/codes/apps-locks/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radixxDRF": ["splash3-xDRF/codes/kernels-locks/radix", "./RADIX -p", " -n1048576"],
    "raytracexDRF": ["splash3-xDRF/codes/apps-locks/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrendxDRF": ["splash3-xDRF/codes/apps-locks/volrend", "./VOLREND ", " inputs/head"],
    "waternsqxDRF": ["splash3-xDRF/codes/apps-locks/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "waterspxDRF": ["splash3-xDRF/codes/apps-locks/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "barnesxDRF++": ["splash3-xDRF++/codes/apps-locks/barnes", "./BARNES < inputs/n16384-p", ""],
    "choleskyxDRF++": ["splash3-xDRF++/codes/kernels-locks/cholesky", "./CHOLESKY -p", " < inputs/tk15.O"],
    "fftxDRF++": ["splash3-xDRF++/codes/kernels-locks/fft", "./FFT -p", " -m16"],
    "fmmxDRF++": ["splash3-xDRF++/codes/apps-locks/fmm", "./FMM < inputs/input.", ".16384"],
    "luxDRF++": ["splash3-xDRF++/codes/kernels-locks/lu/contiguous_blocks", "./LU -p", " -n512"],
    "luncxDRF++": ["splash3-xDRF++/codes/kernels-locks/lu/non_contiguous_blocks", "./LU -p", " -n512"],
    "oceanxDRF++": ["splash3-xDRF++/codes/apps-locks/ocean/contiguous_partitions", "./OCEAN -p", " -n258"],
    "oceanncxDRF++": ["splash3-xDRF++/codes/apps-locks/ocean/non_contiguous_partitions", "./OCEAN -p", " -n258"],
    "radiosityxDRF++": ["splash3-xDRF++/codes/apps-locks/radiosity", "./RADIOSITY -p ", " -ae 5000 -bf 0.1 -en 0.05 -room -batch"],
    "radixxDRF++": ["splash3-xDRF++/codes/kernels-locks/radix", "./RADIX -p", " -n1048576"],
    "raytracexDRF++": ["splash3-xDRF++/codes/apps-locks/raytrace", "./RAYTRACE -p", " -m64 inputs/car.env"],
    "volrendxDRF++": ["splash3-xDRF++/codes/apps-locks/volrend", "./VOLREND ", " inputs/head"],
    "waternsqxDRF++": ["splash3-xDRF++/codes/apps-locks/water-nsquared", "./WATER-NSQUARED < inputs/n512-p", ""],
    "waterspxDRF++": ["splash3-xDRF++/codes/apps-locks/water-spatial", "./WATER-SPATIAL < inputs/n512-p", ""], 

    "em3d": ["scib/em3d", "./EM3D ", " 38400 2 15 2 50"],
    "tomcatv": ["scib/tomcatv", "./TOMCATV 256 5 ", ""],
    "unstructured": ["scib/unstructured", "./UNSTRUCTURED ", " inputs/mesh.2k 5"], # max 32 threads

    "dedupxDRF": ["parsec-2.1-xDRF/pkgs/kernels/dedup/src", "./DEDUP -c -p -f -t ", " -i media.dat -o output.dat.ddp"], # simmedium
    "fluidanimatexDRF": ["parsec-2.1-xDRF/pkgs/apps/fluidanimate/src", "./fluidanimate ", " 5 in_100K.fluid out.fluid"], # simsmall
    "streamclusterxDRF": ["parsec-2.1-xDRF/pkgs/kernels/streamcluster/src", "./streamcluster 10 20 64 8192 8192 1000 none output.txt ", ""], # simsmall

    "dedupxDRF++": ["parsec-2.1-xDRF++/pkgs/kernels/dedup/src", "./DEDUP -c -p -f -t ", " -i media.dat -o output.dat.ddp"], # simmedium
    "fluidanimatexDRF++": ["parsec-2.1-xDRF++/pkgs/apps/fluidanimate/src", "./fluidanimate ", " 5 in_100K.fluid out.fluid"], # simsmall
    "streamclusterxDRF++": ["parsec-2.1-xDRF++/pkgs/kernels/streamcluster/src", "./streamcluster 10 20 64 8192 8192 1000 none output.txt ", ""], # simsmall
    

#simsmall (fmm, ocean_cp, oceanncp, radiosity, radix, raytrace, volrend, water_nsquared, water_spatial, freqmine, streamcluster, swaptions, and vips)
#simmedium (barnes, cholesky, fft, lu_cb, lu_ncb, blackscholes, bodytrack, canneal, dedup, ferret, fluidanimate, and x264) inputs.

#apps
    "blackscholesxDRF20": ["parsec-3.0-xDRF/pkgs/bin/blackscholes", "./blackscholes ", " in_16K.txt prices.txt"], # simmedium
    "facesimxDRF20": ["parsec-3.0-xDRF/pkgs/bin/facesim", "./facesim  -timing -threads", " "], # sinsmall
    "fluidanimatexDRF20": ["parsec-3.0-xDRF/pkgs/bin/fluidanimate", "./fluidanimate ", " 5 in_100K.fluid out.fluid"], # simmedium
    "vipsxDRF20": ["/home/users/ssingh/parsec-3.0-xDRF/pkgs/bin/vips", "./vips im_benchmark pomegranate_1600x1200.v output.v", ""], # simmedium
    "bodytrackxDRF20": ["parsec-3.0-xDRF/pkgs/bin/bodytrack", "./bodytrack sequenceB_2 4 2 2000 5 0 ", " "], # simmedium 
    "ferretxDRF20": ["parsec-3.0-xDRF/pkgs/bin/ferret", "./ferret corel lsh queries 10 20 ", " output.txt"], # simmedium     
    "swaptionsxDRF20": ["parsec-3.0-xDRF/pkgs/bin/swaptions", "./swaptions -ns 16 -sm 10000 -nt ", " "], # simsmall
    "x264xDRF20": ["parsec-3.0-xDRF/pkgs/bin/x264", "./x264 --quiet --qp 20 --partitions b8x8,i4x4 --ref 5 --direct auto --b-pyramid --weightb --mixed-refs --no-fast-pskip --me umh --subme 7 --analyse b8x8,i4x4 --threads ", " -o eledream.264 eledream_640x360_32.y4m"], # simmedium

#kernerls
    "dedupxDRF20": ["parsec-3.0-xDRF/pkgs/bin/dedup", "./dedup -c -p -v -t ", " -i media.dat -o output.dat.ddp"], # simmedium
    "cannealxDRF20": ["parsec-3.0-xDRF/pkgs/bin/canneal", "./canneal ", " 15000 2000 200000.nets 64"], # simmedium
    "streamclusterxDRF20": ["parsec-3.0-xDRF/pkgs/bin/streamcluster", "./streamcluster 10 20 64 8192 8192 1000 none output.txt ", ""], # simmedium


}

if not path.isdir(outs_dir_base):
    raise "no existe el directorio: '" + outs_dir_base + "'"

if getenv("ENCOLA_JUST_TEST", "0") == "1":
    just_test = 1
else:
    just_test = 0

if skip_set_file == None:
    skip_set = set()
else:
    skip_set = set([l.strip() for l in open(skip_set_file)])

def merge_dicts (d1, d2):
    ret = d1.copy()
    ret.update(d2)
    return ret

base_config = {
    "BENCHMARK": "",
    "NUM_THREADS": 1,
 }

def out_file(config):
    return path.join(outs_dir_base, "%s-p%d_%d" % (config["BENCHMARK"], config["NUM_THREADS"], config["g_RANDOM_SEED"]))

def get_sniper_cores(threads, benchmark):
    if benchmark.startswith("blackscholes"):
        return threads + 1
    if benchmark.startswith("bodytrack"):
        return threads + 2
    if benchmark.startswith("canneal"):
        return threads + 1
    if benchmark.startswith("dedup"):
        return threads * 3 + 3
    if benchmark.startswith("facesim"):
        return threads
    if benchmark.startswith("ferret"):
        return threads * 4 + 3
    if benchmark.startswith("fluidanimate"):
        return threads + 1
    if benchmark.startswith("freqmine"):
        return threads
    if benchmark.startswith("streamcluster"):
        return threads * 2 + 1
    if benchmark.startswith("swaptions"):
        return threads + 1
    if benchmark.startswith("vips"):
        return threads + 3
    if benchmark.startswith("x264"):
        return threads * 2
    else:
        return threads

def enqueue(config):
    def quote(s):
        return s.replace("\"", "\\\"")

    of = out_file(config)

    if not path.isdir(path.dirname(of)):
        makedirs(path.dirname(of))

    if path.exists(of + ".stderr"):
        print "skipped %s (%s exists)" % (path.basename(of), of + ".stderr")
    elif path.basename(of) in skip_set:
        print "skipped %s (in skip_set)" % path.basename(of)
    else:

        def write_script(f):
            num_sniper_cores = get_sniper_cores(config["NUM_THREADS"], config["BENCHMARK"])
            f.write("ulimit -c0\n")
            f.write("cd " + benchdir + vars[config["BENCHMARK"]][0] + "\n")
            f.write(sniperexec + " -n " + str(num_sniper_cores) + " " + sniperoptspre + str(num_sniper_cores) + sniperoptspost + " " + sniperoptsroi + " --save-output -d " + out_file(config) + " -- " + vars[config["BENCHMARK"]][1] + str(config["NUM_THREADS"]) + vars[config["BENCHMARK"]][2]  + "\n")

        if just_test == 0:
            p = Popen(["qsub", "-cwd", "-N", id + path.basename(of), "-r", "yes", "-V", "-e", of + ".stderr", "-o", of + ".stdout"], stdin = PIPE)
            #p = Popen(["qsub", "-cwd", "-N", id + path.basename(of), "-r", "yes", "-V", "-e", of + ".stderr", "-o", of + ".stdout", "-q", "short.q"], stdin = PIPE)
            write_script(p.stdin)
            p.stdin.close()
            p.wait()
        else:
            (fdes, fname) = mkstemp()
            f = fdopen(fdes, "w")
            f.write("#!/bin/bash\n")
            f.write("pushd .\n")
            write_script(f)
            f.write("popd\n")
            f.close()
            chmod(fname, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            print "Created test script %s for %s" % (fname, path.basename(of))
        

def config_vary(base, key, values, guard = lambda c: True):
    ret = []
    if type(base) == list:
        for b in base:
            if guard(b):
                ret += config_vary(b, key, values)
            else:
                ret.append(b)
        return ret
    for v in values:
        c = base.copy()
        if type(key) == tuple:
            for (k, sv) in zip(key, v):
                c[k] = sv
                ret.append(c)
        else:
            c[key] = v
            ret.append(c)
    return ret

def remove_duplicates(l):
    r = []
    for i in l:
        if not i in r:
            r.append(i)
    return r

def check_duplicate_output_files(l):
    m = {}
    for c in l:
        of = out_file(c)
        m.setdefault(of, [])
        m[of].append(c)
    for i in m:
        if len(m[i]) != 1:
            raise "Duplicate out_file: %s, %s" % (i, str(m[i]))

# do not modify
configs = config_vary(base_config, "g_RANDOM_SEED", range(min_seed, max_seed + 1))

# modify if necessary
configs = config_vary(configs, "BENCHMARK", [ 
        # "bakery",
        # "barriers",
        # "dclocking",
        # "locks",
        # "locks2",
        # "postgresql",
        
        # "barnes",
        # "cholesky", 
        # "fft", 
        # "fmm", 
        # "lu", 
        # "lunc", 
        # "ocean" ,
        # "oceannc", 
        # "radiosity", 
        # "radix", 
        # "raytrace", 
        # "volrend", 
        # "waternsq", 
        # "watersp", 
        
        # "barnesRC",
        # "choleskyRC", 
        # "fftRC", 
        # "fmmRC", 
        # "luRC", 
        # "luncRC", 
        # "oceanRC" ,
        # "oceanncRC", 
        # "radiosityRC", 
        # "radixRC", 
        # "raytraceRC", 
        # "volrendRC", 
        # "waternsqRC", 
        # "waterspRC", 
        
        # "barnesForward",
        # "choleskyForward", 
        # "fftForward", 
        # "fmmForward", 
        # "luForward", 
        # "luncForward", 
        # "oceanForward" ,
        # "oceanncForward", 
        # "radiosityForward", 
        # "radixForward", 
        # "raytraceForward", 
        # "volrendForward", 
        # "waternsqForward", 
        # "waterspForward", 

        # "barnesDRF",
        # "choleskyDRF", 
        # "fftDRF", 
        # "fmmDRF", 
        # "luDRF", 
        # "luncDRF", 
        # "oceanDRF" ,
        # "oceanncDRF", 
        # "radiosityDRF", 
        # "radixDRF", 
        # "raytraceDRF", 
        # "volrendDRF", 
        # "waternsqDRF", 
        # "waterspDRF", 

        # "barnesxDRF",
        # "choleskyxDRF", 
        # "fftxDRF", 
        # "fmmxDRF", 
        # "luxDRF", 
        # "luncxDRF", 
        # "oceanxDRF" ,
        # "oceanncxDRF", 
        # "radiosityxDRF", 
        # "radixxDRF", 
        # "raytracexDRF", 
        # "volrendxDRF", 
        # "waternsqxDRF", 
        # "waterspxDRF", 

        # "barnesxDRF++",
        # "choleskyxDRF++", 
        # "fftxDRF++", 
        # "fmmxDRF++", 
        # "luxDRF++", 
        # "luncxDRF++", 
        # "oceanxDRF++" ,
        # "oceanncxDRF++", 
        # "radiosityxDRF++", 
        # "radixxDRF++", 
        # "raytracexDRF++", 
        # "volrendxDRF++", 
        # "waternsqxDRF++", 
        # "waterspxDRF++", 

        # "em3d",
        # "tomcatv",
        # "unstructured", # max 32 threads

        # "dedupxDRF",
        # "fluidanimatexDRF",
        # "streamclusterxDRF",

        # "dedupxDRF++",
        #"fluidanimatexDRF++",
        # "streamclusterxDRF++",
        
        #"blackscholesxDRF20",
       # "facesimxDRF20",
        #"fluidanimatexDRF20",
       # "vipsxDRF20",
        #"bodytrackxDRF20",
        "ferretxDRF20",
        #"swaptionsxDRF20",
        #"x264xDRF20",
        #"dedupxDRF20",
        #"cannealxDRF20",
        #"streamclusterxDRF20",
        ])

configs = config_vary(configs, "NUM_THREADS", [ 
        # 1,
        # 2,
        # 4,
        8,
        # 16,
        # 32,
        # 64,
        # 128,
        # 256,
        ])

configs = remove_duplicates(configs)
check_duplicate_output_files(configs)

for c in configs:
    enqueue(c)
