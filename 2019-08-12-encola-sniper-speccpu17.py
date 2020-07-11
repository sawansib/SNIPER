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
sniperexec = "/home/users/aros/sniper/run-sniper"
sniperoptspre = "-cgainestown -crob -gperf_model/dram/num_controllers=1 -gperf_model/l3_cache/shared_cores="
sniperoptspost = " -gperf_model/l2_cache/perfect=true -gperf_model/l3_cache/perfect=true -gperf_model/l1_icache/perfect=true  -gperf_model/dram/direct_access=true -ggeneral/enable_icache_modeling=false -gperf_model/branch_predictor/type=none -gperf_model/l1_dcache/perfect=true -gclock_skew_minimization/barrier/quantum=2147483647 -gperf_model/dtlb/size=0 -gperf_model/core/interval_timer/window_size=256 -gperf_model/core/rob_timer/rs_entries=256 -gperf_model/core/rob_timer/outstanding_loads=256 -gperf_model/core/rob_timer/outstanding_stores=256 -gperf_model/core/rob_timer/commit_width=4 -gperf_model/core/rob_timer/deptrace=true -gperf_model/core/rob_timer/store_to_load_forwarding=false -gperf_model/core/rob_timer/deptrace_microops=true -gperf_model/core/rob_timer/deptrace_start_active=true -gperf_model/core/rob_timer/deptrace_roi=true"

benchdir = "/home/users/aros/benchmarks/original/SpecCPU2017/CPU2017_BINS_NOHOOKS_STATIC_NOFAKE_ONELINK_MEGA/"

vars = {
    "500.perlbench_1": ["500.perlbench_r", "./perlbench_r_base.GCC_7_3_0_HOOKS-m64 -I./lib checkspam_noprints.pl 2500 5 25 11 150 1 1 1 1 > perlbench_1.opts-O3.out 2>> perlbench_1.opts-O3.err"],
    "500.perlbench_2": ["500.perlbench_r", "./perlbench_r_base.GCC_7_3_0_HOOKS-m64 -I./lib diffmail_noprints.pl 4 800 10 17 19 300 > perlbench_2.opts-O3.out 2>> perlbench_2.opts-O3.err"],
    "500.perlbench_3": ["500.perlbench_r", "./perlbench_r_base.GCC_7_3_0_HOOKS-m64 -I./lib splitmail_noprints.pl 6400 12 26 16 100 0 > perlbench_3.opts-O3.out 2>> perlbench_3.opts-O3.err"],
    "502.gcc_1": ["502.gcc_r", "./cpugcc_r_base.GCC_7_3_0_HOOKS-m64 gcc-pp.c -O3 -finline-limit=0 -fif-conversion -fif-conversion2 -o gcc-pp.opts-O3_-finline-limit_0_-fif-conversion_-fif-conversion2.s > gcc-pp.opts-O3_-finline-limit_0_-fif-conversion_-fif-conversion2.out 2>> gcc-pp.opts-O3_-finline-limit_0_-fif-conversion_-fif-conversion2.err"],
    "502.gcc_2": ["502.gcc_r", "./cpugcc_r_base.GCC_7_3_0_HOOKS-m64 gcc-pp.c -O2 -finline-limit=36000 -fpic -o gcc-pp.opts-O2_-finline-limit_36000_-fpic.s > gcc-pp.opts-O2_-finline-limit_36000_-fpic.out 2>> gcc-pp.opts-O2_-finline-limit_36000_-fpic.err"],
    "502.gcc_3": ["502.gcc_r", "./cpugcc_r_base.GCC_7_3_0_HOOKS-m64 gcc-smaller.c -O3 -fipa-pta -o gcc-smaller.opts-O3_-fipa-pta.s > gcc-smaller.opts-O3_-fipa-pta.out 2>> gcc-smaller.opts-O3_-fipa-pta.err"],
    "502.gcc_4": ["502.gcc_r", "./cpugcc_r_base.GCC_7_3_0_HOOKS-m64 ref32.c -O5 -o ref32.opts-O5.s > ref32.opts-O5.out 2>> ref32.opts-O5.err"],
    "502.gcc_5": ["502.gcc_r", "./cpugcc_r_base.GCC_7_3_0_HOOKS-m64 ref32.c -O3 -fselective-scheduling -fselective-scheduling2 -o ref32.opts-O3_-fselective-scheduling_-fselective-scheduling2.s > ref32.opts-O3_-fselective-scheduling_-fselective-scheduling2.out 2>> ref32.opts-O3_-fselective-scheduling_-fselective-scheduling2.err"],
    "503.bwaves_1": ["503.bwaves_r", "./bwaves_r_base.GCC_7_3_0_HOOKS-m64 bwaves_1 < bwaves_1.in > bwaves_1.out 2>> bwaves_1.err"],
    "503.bwaves_2": ["503.bwaves_r", "./bwaves_r_base.GCC_7_3_0_HOOKS-m64 bwaves_2 < bwaves_2.in > bwaves_2.out 2>> bwaves_2.err"],
    "503.bwaves_3": ["503.bwaves_r", "./bwaves_r_base.GCC_7_3_0_HOOKS-m64 bwaves_3 < bwaves_3.in > bwaves_3.out 2>> bwaves_3.err"],
    "503.bwaves_4": ["503.bwaves_r", "./bwaves_r_base.GCC_7_3_0_HOOKS-m64 bwaves_4 < bwaves_4.in > bwaves_4.out 2>> bwaves_4.err"],
    "505.mcf": ["505.mcf_r", "./mcf_r_base.GCC_7_3_0_HOOKS-m64 inp.in > inp.out 2>> inp.err"],
    "507.cactuBSSN": ["507.cactuBSSN_r", "./cactusBSSN_r_base.GCC_7_3_0_HOOKS-m64 spec_ref.par > spec_ref.out 2>> spec_ref.err"],
    "508.namd": ["508.namd_r", "./namd_r_base.GCC_7_3_0_HOOKS-m64 --input apoa1.input --output apoa1.ref.output --iterations 65 > namd.out 2>> namd.err"],
    "510.parest": ["510.parest_r", "./parest_r_base.GCC_7_3_0_HOOKS-m64 ref.prm > ref.out 2>> ref.err"],
    "511.povray": ["511.povray_r", "./povray_r_base.GCC_7_3_0_HOOKS-m64 SPEC-benchmark-ref.ini > SPEC-benchmark-ref.stdout 2>> SPEC-benchmark-ref.stderr"],
    "519.lbm": ["519.lbm_r", "./lbm_r_base.GCC_7_3_0_HOOKS-m64 3000 reference.dat 0 0 100_100_130_ldc.of > lbm.out 2>> lbm.err"],
    "520.omnetpp": ["520.omnetpp_r", "./omnetpp_r_base.GCC_7_3_0_HOOKS-m64 -c General -r 0 > omnetpp.General-0.out 2>> omnetpp.General-0.err"],
    "521.wrf": ["521.wrf_r", "./wrf_r_base.GCC_7_3_0_HOOKS-m64 > rsl.out.0000 2>> wrf.err"],
    "523.xalancbmk": ["523.xalancbmk_r", "./cpuxalan_r_base.GCC_7_3_0_HOOKS-m64 -v t5.xml xalanc.xsl > ref-t5.out 2>> ref-t5.err"],
    "525.x264_1": ["525.x264_r", "./x264_r_base.GCC_7_3_0_HOOKS-m64 --pass 1 --stats x264_stats.log --bitrate 1000 --frames 1000 -o BuckBunny_New.264 BuckBunny.yuv 1280x720 > run_000-1000_x264_r_base.GCC_7_3_0_HOOKS-m64_x264_pass1.out 2>> run_000-1000_x264_r_base.GCC_7_3_0_HOOKS-m64_x264_pass1.err"],
    "525.x264_2": ["525.x264_r", "./x264_r_base.GCC_7_3_0_HOOKS-m64 --pass 2 --stats x264_stats.log --bitrate 1000 --dumpyuv 200 --frames 1000 -o BuckBunny_New.264 BuckBunny.yuv 1280x720 > run_000-1000_x264_r_base.GCC_7_3_0_HOOKS-m64_x264_pass2.out 2>> run_000-1000_x264_r_base.GCC_7_3_0_HOOKS-m64_x264_pass2.err"],
    "525.x264_3": ["525.x264_r", "./x264_r_base.GCC_7_3_0_HOOKS-m64 --seek 500 --dumpyuv 200 --frames 1250 -o BuckBunny_New.264 BuckBunny.yuv 1280x720 > run_0500-1250_x264_r_base.GCC_7_3_0_HOOKS-m64_x264.out 2>> run_0500-1250_x264_r_base.GCC_7_3_0_HOOKS-m64_x264.err"],
    "526.blender": ["526.blender_r", "./blender_r_base.GCC_7_3_0_HOOKS-m64 sh3_no_char.blend --render-output sh3_no_char_ --threads 1 -b -F RAWTGA -s 849 -e 849 -a > sh3_no_char.849.spec.out 2>> sh3_no_char.849.spec.err"],
    "527.cam4": ["527.cam4_r", "./cam4_r_base.GCC_7_3_0_HOOKS-m64 > cam4_r_base.GCC_7_3_0_HOOKS-m64.txt 2>> cam4_r_base.GCC_7_3_0_HOOKS-m64.err"],
    "531.deepsjeng": ["531.deepsjeng_r", "./deepsjeng_r_base.GCC_7_3_0_HOOKS-m64 ref.txt > ref.out 2>> ref.err"],
    "538.imagick": ["538.imagick_r", "./imagick_r_base.GCC_7_3_0_HOOKS-m64 -limit disk 0 refrate_input.tga -edge 41 -resample 181% -emboss 31 -colorspace YUV -mean-shift 19x19+15% -resize 30% refrate_output.tga > refrate_convert.out 2>> refrate_convert.err"],
    "541.leela": ["541.leela_r", "./leela_r_base.GCC_7_3_0_HOOKS-m64 ref.sgf > ref.out 2>> ref.err"],
    "544.nab": ["544.nab_r", "./nab_r_base.GCC_7_3_0_HOOKS-m64 1am0 1122214447 122 > 1am0.out 2>> 1am0.err"],
    "548.exchange2": ["548.exchange2_r", "./exchange2_r_base.GCC_7_3_0_HOOKS-m64 6 > exchange2.txt 2>> exchange2.err"],
    "549.fotonik3d": ["549.fotonik3d_r", "./fotonik3d_r_base.GCC_7_3_0_HOOKS-m64 > fotonik3d_r.log 2>> fotonik3d_r.err"],
    "554.roms": ["554.roms_r", "./roms_r_base.GCC_7_3_0_HOOKS-m64 < ocean_benchmark2.in.x > ocean_benchmark2.log 2>> ocean_benchmark2.err"], 
    "557.xz_1": ["557.xz_r", "./xz_r_base.GCC_7_3_0_HOOKS-m64 cld.tar.xz 160 19cf30ae51eddcbefda78dd06014b4b96281456e078ca7c13e1c0c9e6aaea8dff3efb4ad6b0456697718cede6bd5454852652806a657bb56e07d61128434b474 59796407 61004416 6 > cld.tar-160-6.out 2>> cld.tar-160-6.err"],
    "557.xz_2": ["557.xz_r", "./xz_r_base.GCC_7_3_0_HOOKS-m64 cpu2006docs.tar.xz 250 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 23047774 23513385 6e > cpu2006docs.tar-250-6e.out 2>> cpu2006docs.tar-250-6e.err"],
    "557.xz_3": ["557.xz_r", "./xz_r_base.GCC_7_3_0_HOOKS-m64 input.combined.xz 250 a841f68f38572a49d86226b7ff5baeb31bd19dc637a922a972b2e6d1257a890f6a544ecab967c313e370478c74f760eb229d4eef8a8d2836d233d3e9dd1430bf 40401484 41217675 7 > input.combined-250-7.out 2>> input.combined-250-7.err"],
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
    "INSTR_COUNT": 1000000000,
    "INSTR_COUNT_CLEAR_STATS": 100000000,
    "TRACE_SIZE_NAME": "ref",
    }

def out_file(config):
    return path.join(outs_dir_base, "%s_%s" % (config["BENCHMARK"], config["TRACE_SIZE_NAME"]))

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
            f.write("ulimit -c0\n")
            f.write("cd " + benchdir + vars[config["BENCHMARK"]][0] + "\n")
            f.write(sniperexec + " -n " + str(config["NUM_THREADS"]) + " -sstop-by-icount:" + str(config["INSTR_COUNT"]) + ":" + str(config["INSTR_COUNT_FAST_FWD"]) + " --roi-script " +
                    " --insert-clear-stats-by-icount=" + str(config["INSTR_COUNT_CLEAR_STATS"]) + " " +
                    sniperoptspre + str(config["NUM_THREADS"]) + sniperoptspost + " --no-cache-warming --save-output -d " + out_file(config) + 
                    " -- " + vars[config["BENCHMARK"]][1] + "\n")

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
    "500.perlbench_1",
    "500.perlbench_2",
    "500.perlbench_3",
    "502.gcc_1",
    "502.gcc_2",
    "502.gcc_3",
    "502.gcc_4",
    "502.gcc_5",
    "503.bwaves_1",
    "503.bwaves_2",
    "503.bwaves_3",
    "503.bwaves_4",
    "505.mcf",
    "507.cactuBSSN",
    "508.namd",
    "510.parest",
    "511.povray",
    "519.lbm",
    "520.omnetpp",
    "521.wrf",
    "523.xalancbmk",
    "525.x264_1",
    "525.x264_2",
    "525.x264_3",
    "526.blender",
    "527.cam4",
    "531.deepsjeng",
    "538.imagick",
    "541.leela",
    "544.nab",
    "548.exchange2",
    "549.fotonik3d",
    "554.roms",
    "557.xz_1",
    "557.xz_2",
    "557.xz_3",
    ])

configs = config_vary(configs, "INSTR_COUNT", [ 
        1000000, # 1M test
        10000000, # 10M small
        100000000, # 100M medium
        500000000, # 500M large
        1000000000, # 1B ref
        ])

configs = config_vary(configs, "INSTR_COUNT_FAST_FWD", [ 
        4000000000, # 4B
        ])

# Reset stats at 10%
configs = config_vary(configs, "INSTR_COUNT_CLEAR_STATS", [ 100000 ], lambda c: c["INSTR_COUNT"] == 1000000)
configs = config_vary(configs, "INSTR_COUNT_CLEAR_STATS", [ 1000000 ], lambda c: c["INSTR_COUNT"] == 10000000)
configs = config_vary(configs, "INSTR_COUNT_CLEAR_STATS", [ 10000000 ], lambda c: c["INSTR_COUNT"] == 100000000)
configs = config_vary(configs, "INSTR_COUNT_CLEAR_STATS", [ 50000000 ], lambda c: c["INSTR_COUNT"] == 500000000)
configs = config_vary(configs, "INSTR_COUNT_CLEAR_STATS", [ 100000000 ], lambda c: c["INSTR_COUNT"] == 1000000000)

# Set names for the trace sizes
configs = config_vary(configs, "TRACE_SIZE_NAME", [ "test" ], lambda c: c["INSTR_COUNT"] == 1000000)
configs = config_vary(configs, "TRACE_SIZE_NAME", [ "small" ], lambda c: c["INSTR_COUNT"] == 10000000)
configs = config_vary(configs, "TRACE_SIZE_NAME", [ "medium" ], lambda c: c["INSTR_COUNT"] == 100000000)
configs = config_vary(configs, "TRACE_SIZE_NAME", [ "large" ], lambda c: c["INSTR_COUNT"] == 500000000)
configs = config_vary(configs, "TRACE_SIZE_NAME", [ "ref" ], lambda c: c["INSTR_COUNT"] == 1000000000)

configs = remove_duplicates(configs)
check_duplicate_output_files(configs)

for c in configs:
    enqueue(c)
