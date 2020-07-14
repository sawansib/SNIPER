#!/usr/bin/env python

# BEGIN_LEGAL
# BSD License
#
# Copyright (c)2014 Intel Corporation. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
# Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.  Redistributions
# in binary form must reproduce the above copyright notice, this list of
# conditions and the following disclaimer in the documentation and/or
# other materials provided with the distribution.  Neither the name of
# the Intel Corporation nor the names of its contributors may be used to
# endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# ``AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE INTEL OR
# ITS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# END_LEGAL
#
#
# @ORIGINAL_AUTHORS: T. Mack Stallcup, Cristiano Pereira, Harish Patil, Chuck Yount
#
#
# $Id: config.py,v 1.82 2014/06/26 15:02:01 tmstall Exp tmstall $

import os

# Local modules
#
import msg

#####################################################################################
#
# The 'config' module is imported by all tracing modules.  
#
# Global data which is used by every module is stored here.  The class
# GlobalVar reads/writes pickle files 'global data' files which are used to
# transfer the global data from calling Python scripts to the called Python
# scripts.
#
# The class ConfigClass reads/writes tracing parameter configuration files.
#
#####################################################################################

"""
Here's the process for adding new parameters.

1) Since all parameters can be also initilized from command options, the first
   step is to add a new option to the module 'cmd_options.py'.

    a) Determine the appropriate 'options group' for the new option, if any.
    b) Add the option to the file.

3) Parameters in the top level and mid level scripts may need to be propogated to
   other, lower level, scripts.

4) The following steps are required in this module:
    a) Add a new parameter in the section 'Tracing configuration parameters'.
    b) Add new parameter to these methods: DumpGlobalVars(), ReadGlobalVars()
       and SetGlobalVars().

5) If the new option is a parameter which can be read from a tracing
   parameter configuration file, then also add it to the method ParseCfgFile().

NOTE: To add a new simulator, code in this module needs to be modified.
Look for the string:  Types of kits
"""

#####################################################################################
#
# Global variables
#
# Global variables are saved in a pickle file when calling a new python script.
# This allows the globals to be passed between scripts.  If a pickle file
# exists, then assume we were called from another script.  Read in the global
# variables from the pickle file.
#
#####################################################################################

# Base name of the pickle file used to transfer data.
#
pickle_file_name = 'global.dat'

# Did we already read global variables from a pickle file?
#
read_pickle_vars = False

# Global variables
#
verbose = False
debug   = False

#####################################################################################
#
# Tracing configuration parameters
#
# These define paramters which describe the application being traced and how to trace it.
# Many of these tracing parameters are also saved/restored in the pickle file to pass
# them to the lower level scripts.
#
#####################################################################################

# Default file name for the application tracing configuration information
#
config_ext = '.cfg'
default_config_file = 'tracing' + config_ext

# File extension for PinPlay message files.
#
msgfile_ext = ''

# String used to differentiate the per instance cfg/status files from the 
# remaining file/dir names.
#
instance_ext = '.info'

# File extension for the status of the phases run by a script.
#
phase_status_ext = '.status'

# File extension for the simulator output log file.
#
sim_out_ext = '.sim.txt'

# File extension for the Sniper output file (i.e. text generated
# when Sniper runs).  See also 'sniper_result_dir'.
#
sniper_out_ext = '.sniper.txt'

# Parameters from config file or command line options. Set to nonsense values
# here.  Defaults are set in the module 'cmd_options.py' when the option is
# defined.
#
param_section  = 'Parameters'
archsim_config_dir = ''
command        = ''
cutoff         = 0.0
epilog_length  = 0
focus_thread   = -1
input_name     = ''
maxk           = 0
mode           = ''
num_cores      = 0
num_proc       = 0
pin_options    = ''
pinplayhome    = ''
program_name   = ''
prolog_length  = 0
sdehome        = ''
simhome        = ''
simpoint_options = ''
slice_size     = 0
sniper_root    = ''
warmup_length  = 0

# Basename for the whole program pinball directories.
#
wp_dir_basename = 'whole_program'

# User defined directory containing the whole program pinballs.
#
whole_pgm_dir = ''

# Name of the directory which contains the relogged whole program pinballs.
#
relog_dir = ''

# String added to a directory name when it is filtered by relogging.
#
relog_dir_str = '.relog'

# Location of Sniper result files. This is where the results from running
# Sniper are located, not the location where the output from running
# Sniper is stored. See also 'sniper_out_ext'.
#
sniper_result_dir = 'sniper_results'

# Char which is used as the separator between 'program_name' and 'input_name'
# when generating the Data/pp/lit dir names for a given tracing instance.  Set
# default value here.  It can be changed in config files or with a command line
# option.  
#
dir_separator = '.'

# Should the files be compressed.
#
compressed = True

# Should the LIT FILES be cooperative of the default (per thread).
#
coop_lit = False

# Should the region pinballs be cooperative instead of the default (per thread).
#
coop_pinball = False

# Whole program pinballs collected on Windows, but remaining processing is being done on Linux.
#
cross_os = False

# Do not use a focus thread.
#
no_focus_thread = False

# MPI command line options
#
mpi_options = ''

# Boolean to see if the global data files should be saved instead
# of deleted after they are read.  Useful for debugging.
#
save_global = False

# List of global files which should be deleted when the script exits.
#
global_file_list = []

# The type of the simulator kit. Used by a script to pass along the kit
# type to another script.
#
# NOTE: This is only used to pass a kit type between scripts.  It is NOT used
# to store data from a command line option.
#
sim_kit_type = None

# Process to use for running a simulator.
#
processor = ''

# Number of instructions in a CMPSim 'phase'.  To calculate the number of
# phases which should be given to the knob '-phaselen', divide the pinball
# icount by this value.
# 
instr_cmpsim_phase = 1000000

#####################################################################################
#
# Parameters for the rename.py script
#
#####################################################################################

app_version = ''
compiler_version = ''
platform = ''

#####################################################################################
#
# Define types used in the scripts.
#
#####################################################################################

# What is architecture.
#
ARCH_INVALID = 0
ARCH_IA32 = 1
ARCH_INTEL64 = 2

# What type of application are we working with.
#
ST_MODE = 'st'
MT_MODE = 'mt'
MPI_MODE = 'mpi'
MPI_MT_MODE = 'mpi_mt'

# Relogging phases
#
RELOG_CODE_EXCLUDE = 0       # Relogging with code exclusion
RELOG_FOCUS        = 1       # Relogging with a focus thread
RELOG_NAME         = 2       # User defined name for relogging (user must specify logging knobs)
RELOG_NO_CLEANUP   = 3       # Relogging to remove cleanup instructions
RELOG_NO_INIT      = 4       # Relogging to remove initialization instructions
RELOG_NO_MPI_SPIN  = 5       # Relogging to remove MPI spin instructions
RELOG_NONE         = 6       # Not relogging
RELOG_NO_OMP_SPIN  = 7       # Relogging to remove OpenMP spin instructions

# Types of kits.
#
# NOTE: If you are adding a kit for a new simulator, then you need
# to add the type here.
#
PINPLAY = 0
SDE     = 1
BRPRED  = 2
CMPSIM  = 3
X86NOAS = 4
X86     = 5

#####################################################################################
#
# Define a unique string to identify each phase of the tracing process
#
#####################################################################################

phase_str = [  \
    'native_pure', \
    'native_pin', \
    'log_whole', \
    'filter_user_defn', \
    'filter_focus_thread', \
    'filter_init', \
    'filter_cleanup', \
    'filter_code_exclude', \
    'filter_OMP_spin', \
    'filter_MPI_spin', \
    'replay_whole', \
    'gen_BBV', \
    'Simpoint', \
    'relog_regions', \
    'replay_regions', \
    'LIT', \
    'traceinfo', \
    'CMPsim_regions', \
    'CMPsim_whole', \
    'pred_error', \
    'verify_LIT', \
    'sim_regions', \
    'sim_whole', \
    'imix_lit', \
    'imix_regions', \
    'imix_whole', \
    'check_code_exclude', \
    'sniper_regions', \
    'sniper_whole' \
]

native_pure         = 0
native_pin          = 1
log_whole           = 2
filter_user_defn    = 3
filter_focus_thread = 4
filter_init         = 5
filter_cleanup      = 6
filter_code_exclude = 7
filter_OMP_spin     = 8
filter_MPI_spin     = 9
replay_whole        = 10
gen_BBV             = 11
Simpoint            = 12
relog_regions       = 13
replay_regions      = 14
LIT                 = 15
traceinfo           = 16
CMPsim_regions      = 17
CMPsim_whole        = 18
pred_error          = 19
verify_LIT          = 20
sim_regions         = 21
sim_whole           = 22
imix_lit            = 23
imix_regions        = 24
imix_whole          = 25
check_code_exclude  = 26
sniper_regions      = 27
sniper_whole        = 28

def PhaseStr(phase):
    """Format a unique string for each phase."""

    return '[%s]' % phase_str[phase]


#####################################################################################
#
# Class for global variables
#
#####################################################################################

class GlobalVar(object):

    """
    Contains methods to dump/save global variables.

    When one script invokes another script using a system call, the global
    variables are saved in a pickle file.  The name of the specific pickle file
    where the variables are stored is given as an option to the called script.
    When the called script starts, it then reads the global variables from this
    pickle file.
    """

    def DumpGlobalVars(self):
        """
        Save global variables when using a system call to execute another
        tracing script.  It uses the pickle module to write out the global
        objects to be passed to the next script.

        Because some scripts are run concurrently, the pickle file name must be
        unique for each instance of method DumpGlobalVars().  As a result, this
        method returns the unique pickle file name it generates.

        NOTE: Methods DumpGlobalVars(), ReadGlobalVars() and SetGlobalVars() must
        all be identically modified when the objects in the pickle file are changed.

        Any script which calls this method, should also call RmGlobalFiles() to
        clean up any global files remaining when the script exits.

        Return: pickle file name
        """

        import pickle
        import random

        # Add a random number to the pickle file name.  If the file already
        # exists, then get different file name.  Only do this one time.
        #
        key = random.randint(0,32728)
        pickle_name = pickle_file_name + '.' + str(key)
        if os.path.isfile(pickle_name):
            key = random.randint(0,32728)
            pickle_name = pickle_file_name + '.' + str(key)

        try:
            pickle_file = open(pickle_name, 'wb+')
        except:
            msg.PrintAndExit('Can\'t open pickle file: ' + pickle_name)

        # Add to the global list of files. This is used for cleanup when the
        # script exits.
        #
        global global_file_list
        global_file_list.append(pickle_file)

        global verbose, debug, mode, num_cores, focus_thead, coop_pinball, no_focus_thread
        global num_proc, command, input_name, program_name, pin_options
        global pinplayhome, sdehome, sniper_root, mpi_options, simhome, archsim_config_dir, processor
        global coop_lit, cross_os, msgfile_ext, save_global, dir_separator, simpoint_options

        try:
            # Save variables in the config module
            #
            # import pdb;  pdb.set_trace()
            pickle.dump(archsim_config_dir, pickle_file)
            pickle.dump(command, pickle_file)
            pickle.dump(coop_lit, pickle_file)
            pickle.dump(coop_pinball, pickle_file)
            pickle.dump(cross_os, pickle_file)
            pickle.dump(debug, pickle_file)
            pickle.dump(dir_separator, pickle_file)
            pickle.dump(focus_thread, pickle_file)
            pickle.dump(input_name, pickle_file)
            pickle.dump(simhome, pickle_file)
            pickle.dump(simpoint_options, pickle_file)
            pickle.dump(mode, pickle_file)
            pickle.dump(mpi_options, pickle_file)
            pickle.dump(msgfile_ext, pickle_file)
            pickle.dump(no_focus_thread, pickle_file)
            pickle.dump(num_cores, pickle_file)
            pickle.dump(num_proc, pickle_file)
            pickle.dump(pin_options, pickle_file)
            pickle.dump(pinplayhome, pickle_file)
            pickle.dump(processor, pickle_file)
            pickle.dump(program_name, pickle_file)
            pickle.dump(save_global, pickle_file)
            pickle.dump(sdehome, pickle_file)
            pickle.dump(sniper_root, pickle_file)
            pickle.dump(sim_kit_type, pickle_file)
            pickle.dump(verbose, pickle_file)
        except (pickle.PicklingError):
            msg.PrintAndExit('Error writing pickle file: ' + pickle_name)
        pickle_file.close()

        return pickle_name

    def ReadGlobalVars(self, options):
        """
        If a pickle data file exists, use this method sets the global variables
        in the current instance from the pickle file.  This must be done AFTER
        all the config files are read.  This allows the global variables from
        the previous script to overwrite values read from the config file.

        NOTE: Methods DumpGlobalVars(), ReadGlobalVars() and SetGlobalVars() must
        all be identically modified when the objects in the pickle file are changed.
        """

        import pickle

        # import pdb;  pdb.set_trace()
        if options.verbose:
            msg.PrintMsg('Global data file given on the command line: ' + str(hasattr(options, 'global_file')))
        if hasattr(options, 'global_file') and options.global_file != '':
            pickle_f = options.global_file      # Use name given in command line option
        else:
            pickle_f = pickle_file_name         # Use default name

        if options.verbose:
            msg.PrintMsg('Reading from global data file:  ' + str(pickle_f))
        if os.path.isfile(pickle_f):
            global command, coop_pinball, cutoff, debug, epilog_length, focus_thread
            global input_name, maxk, mode, mode, no_focus_thread, num_cores, num_proc
            global pinplayhome, program_name, prolog_length, sdehome, sniper_root, slice_size
            global verbose, warmup_length, simhome, archsim_config_dir, processor
            global coop_lit, cross_os, msgfile_ext, save_global, sim_kit_type
            global pin_options, mpi_options, dir_separator, simpoint_options

            try:
                pickle_file = open(pickle_f, 'rb')
            except:
                msg.PrintAndExit('method config.ReadGlobalVars() can\'t open global data (pickle) file: ' + \
                    pickle_f)
            archsim_config_dir = pickle.load(pickle_file)
            command         = pickle.load(pickle_file)
            coop_lit        = pickle.load(pickle_file)
            coop_pinball    = pickle.load(pickle_file)
            cross_os        = pickle.load(pickle_file)
            debug           = pickle.load(pickle_file)
            dir_separator   = pickle.load(pickle_file)
            focus_thread    = pickle.load(pickle_file)
            input_name      = pickle.load(pickle_file)
            simhome         = pickle.load(pickle_file)
            simpoint_options = pickle.load(pickle_file)
            mode            = pickle.load(pickle_file)
            mpi_options     = pickle.load(pickle_file)
            msgfile_ext     = pickle.load(pickle_file)
            no_focus_thread = pickle.load(pickle_file)
            num_cores       = pickle.load(pickle_file)
            num_proc        = pickle.load(pickle_file)
            pin_options     = pickle.load(pickle_file)
            pinplayhome     = pickle.load(pickle_file)
            processor       = pickle.load(pickle_file)
            program_name    = pickle.load(pickle_file)
            save_global     = pickle.load(pickle_file)
            sdehome         = pickle.load(pickle_file)
            sniper_root     = pickle.load(pickle_file)
            sim_kit_type    = pickle.load(pickle_file)
            verbose         = pickle.load(pickle_file)

            pickle_file.close()
            self.read_pickle_vars = True

            # Once the global data is read from the file, delete it.  This is
            # to ensure other scripts don't read this by by mistake.
            #
            if not save_global:
                os.remove(pickle_f)

        # Set these values in the options object as some locations in the code
        # use the config object and others use the options object.  Only set
        # them in the options if the value is the default (i.e. was not set on
        # the command line) and the config value is not the default.
        #
        if hasattr(options, 'archsim_config_dir') and options.archsim_config_dir == '' and archsim_config_dir != '':
            options.archsim_config_dir = archsim_config_dir
        if hasattr(options, 'command') and options.command == '' and command != '':
            options.command = command
        if hasattr(options, 'input_name') and options.input_name == '' and input_name != '':
            options.input_name = input_name
        if hasattr(options, 'program_name') and options.program_name == '' and program_name != '':
            options.program_name = program_name
        if hasattr(options, 'cutoff') and options.cutoff == 0 and cutoff > 0:
            options.cutoff = cutoff
        if hasattr(options, 'coop_lit')and options.coop_lit == False and coop_lit != False:
            options.coop_lit = coop_lit
        if hasattr(options, 'coop_pinball')and options.coop_pinball == False and coop_pinball != False:
            options.coop_pinball = coop_pinball
        if hasattr(options, 'cross_os')and options.cross_os == False and cross_os != False:
            options.cross_os = cross_os
        if hasattr(options, 'compressed') and options.compressed == '' and compressed != 'bzip2':
            options.compressed = compressed
        if hasattr(options, 'debug') and options.debug == False and debug != False:
            options.debug = debug
        if hasattr(options, 'dir_separator') and options.dir_separator == '' and dir_separator != '':
            options.dir_separator = dir_separator
        if hasattr(options, 'epilog_length') and options.epilog_length == 0 and epilog_length > 0:
            options.epilog_length = epilog_length
        if hasattr(options, 'focus_thread') and options.focus_thread == -1 and focus_thread > -1:
            options.focus_thread = focus_thread
        if hasattr(options, 'simhome') and options.simhome == '' and simhome != '':
            options.simhome = simhome
        if hasattr(options, 'simpoint_options') and options.simpoint_options == '' and simpoint_options != '':
            options.simpoint_options = simpoint_options
        if hasattr(options, 'pinplayhome') and options.pinplayhome == '' and pinplayhome != '':
            options.pinplayhome = pinplayhome
        if hasattr(options, 'pin_options') and options.pin_options == '' and pin_options != '':
            options.pin_options = pin_options
        if hasattr(options, 'prolog_length') and options.prolog_length == 0 and prolog_length > 0:
            options.prolog_length = prolog_length
        if hasattr(options, 'maxk') and options.maxk == 0 and maxk > 0:
            options.maxk = maxk
        if hasattr(options, 'mode') and options.mode == '' and mode != '':
            options.mode = mode
        if hasattr(options, 'mpi_options') and options.mpi_options == '' and mpi_options != '':
            options.mpi_options = mpi_options
        if hasattr(options, 'msgfile_ext') and options.msgfile_ext == '' and msgfile_ext != '':
            options.msgfile_ext = msgfile_ext
        if hasattr(options, 'no_focus_thread') and options.no_focus_thread == False and no_focus_thread != False:
            options.no_focus_thread = no_focus_thread
        if hasattr(options, 'num_cores') and options.num_cores == 0 and num_cores > 0:
            options.num_cores = num_cores
        if hasattr(options, 'num_proc') and options.num_proc == 0 and num_proc > 0:
            options.num_proc = num_proc
        if hasattr(options, 'processor') and options.processor == '' and processor != '':
            options.processor = processor
        if hasattr(options, 'save_global') and options.save_global == False and save_global != False:
            options.save_global = save_global
        if hasattr(options, 'sdehome') and options.sdehome == '' and sdehome != '':
            options.sdehome = sdehome
        if hasattr(options, 'sniper_root') and options.sniper_root == '' and sniper_root != '':
            options.sniper_root = sniper_root
        if hasattr(options, 'slice_size') and options.slice_size == 0 and slice_size > 0:
            options.slice_size = slice_size
        if hasattr(options, 'verbose') and options.verbose == False and verbose != False:
            options.verbose = verbose
        if hasattr(options, 'warmup_length') and options.warmup_length == 0 and warmup_length > 0:
            options.warmup_length = warmup_length

        if hasattr(options, 'whole_pgm_dir') and options.whole_pgm_dir == '' and whole_pgm_dir != '':

            # If deleting files, then we do NOT want to set the option
            # 'whole_pgm_dir' from the per instance configuration file.
            # This is required in order to ensure the parameter from the old
            # cfg file is not propogated to the new tracing instance which will
            # be generated after the old files are deleted.
            #
            if not hasattr(options, 'delete') and not hasattr(options, 'delete_all'):
                    options.whole_pgm_dir = whole_pgm_dir
            elif (hasattr(options, 'delete') and not options.delete) and \
                 (hasattr(options, 'delete_all') and not options.delete_all):
                    options.whole_pgm_dir = whole_pgm_dir

        # For the script rename.py.  These are not passed via the global pickle file,
        # only used as parameters which can be read from a tracing configuration file.
        #
        global app_version, compiler_version, platform

        # import pdb ; pdb.set_trace()
        if hasattr(options, 'app_version') and options.app_version == '' and app_version != '':
            options.app_version = app_version
        if hasattr(options, 'compiler_version') and options.compiler_version == '' and compiler_version != '':
            options.compiler_version = compiler_version
        if hasattr(options, 'platform') and options.platform == '' and platform != '':
            options.platform = platform

    def SetGlobalVars(self, options):
        """
        Set the 'global' variables on this module.

        If this method was called from another script, then the global
        variables were already read from a pickle file.  Otherwise, this script
        was run from the command line and we will set global variables from
        options.

        NOTE: Methods DumpGlobalVars(), ReadGlobalVars() and SetGlobalVars() must
        all be identically modified when the objects in the pickle file are changed.
        """

        global command, coop_pinball, cutoff, debug, epilog_length, focus_thread
        global input_name, maxk, mode, mode, no_focus_thread, num_cores, num_proc
        global pinplayhome, program_name, prolog_length, sdehome, sniper_root, slice_size
        global verbose, warmup_length, compressed, simhome, archsim_config_dir
        global pin_options, mpi_options, save_global, processor
        global coop_lit, cross_os, msgfile_ext, whole_pgm_dir, dir_separator, simpoint_options

        # import pdb ; pdb.set_trace()
        if not read_pickle_vars:

            # Since there isn't a pickle file, these variables in this module
            # have not been set from options given to a previous script.  If
            # the globals are already true, this came from the config file.
            # However, the options override the config file, so set them now.
            #
            verbose = options.verbose
            debug   = options.debug

        # If these options were given on the command line, then set the
        # config values from these options.
        #
        if hasattr(options, 'command') and options.command != '':
            command = options.command
        if hasattr(options, 'input_name') and options.input_name != '':
            input_name = options.input_name
        if hasattr(options, 'program_name') and options.program_name != '':
            program_name = options.program_name
        if hasattr(options, 'mode') and options.mode != '':
            mode = options.mode

        if hasattr(options, 'archsim_config_dir') and options.archsim_config_dir != '':
             archsim_config_dir = options.archsim_config_dir
        if hasattr(options, 'cutoff') and options.cutoff > 0:
            cutoff = options.cutoff
        if hasattr(options, 'coop_lit') and options.coop_lit != False:
            coop_lit = options.coop_lit
        if hasattr(options, 'coop_pinball') and options.coop_pinball != False:
            coop_pinball = options.coop_pinball
        if hasattr(options, 'cross_os') and options.cross_os != False:
            cross_os = options.cross_os
        if hasattr(options, 'compressed') and options.compressed != 'bzip2':
            compressed = options.compressed
        if hasattr(options, 'dir_separator') and options.dir_separator != '':
             dir_separator = options.dir_separator
        if hasattr(options, 'focus_thread') and options.focus_thread >= 0:
             focus_thread = options.focus_thread
        if hasattr(options, 'epilog_length') and options.epilog_length > 0:
             epilog_length = options.epilog_length
        if hasattr(options, 'simhome') and options.simhome != '':
             simhome = options.simhome
        if hasattr(options, 'simpoint_options') and options.simpoint_options != '':
             simpoint_options = options.simpoint_options
        if hasattr(options, 'pinplayhome') and options.pinplayhome != '':
             pinplayhome = options.pinplayhome
        if hasattr(options, 'pin_options') and options.pin_options != '':
             pin_options = options.pin_options
        if hasattr(options, 'prolog_length') and options.prolog_length > 0:
             prolog_length = options.prolog_length
        if hasattr(options, 'maxk') and options.maxk > 0:
             maxk = options.maxk
        if hasattr(options, 'mpi_options') and options.mpi_options != '':
             mpi_options = options.mpi_options
        if hasattr(options, 'msgfile_ext') and options.msgfile_ext != '':
            msgfile_ext = options.msgfile_ext
        if hasattr(options, 'no_focus_thread') and options.no_focus_thread != False:
            no_focus_thread = options.no_focus_thread
        if hasattr(options, 'num_cores') and options.num_cores > 0:
             num_cores = options.num_cores
        if hasattr(options, 'num_proc') and options.num_proc > 1:
             num_proc = options.num_proc
        if hasattr(options, 'processor') and options.processor != '':
             processor = options.processor
        if hasattr(options, 'save_global') and options.save_global != False:
             save_global = options.save_global
        if hasattr(options, 'sdehome') and options.sdehome != '':
             sdehome = options.sdehome
        if hasattr(options, 'sniper_root') and options.sniper_root != '':
             sniper_root = options.sniper_root
        if hasattr(options, 'slice_size') and options.slice_size > 0:
             slice_size = options.slice_size
        if hasattr(options, 'warmup_length') and options.warmup_length > 0:
             warmup_length = options.warmup_length
        if hasattr(options, 'whole_pgm_dir') and options.whole_pgm_dir != '':
             whole_pgm_dir = options.whole_pgm_dir

        # For the script rename.py.  These are not passed via the global pickle file,
        # only used as parameters which can be read from a tracing configuration file.
        #
        global app_version, compiler_version, platform

        if hasattr(options, 'app_version') and options.app_version != '':
             app_version = options.app_version
        if hasattr(options, 'compiler_version') and options.compiler_version != '':
             compiler_version = options.compiler_version
        if hasattr(options, 'platform') and options.platform != '':
             platform = options.platform

    def RmGlobalFiles(self, options):
        """
        Clean up any global data files which may still exist.  For instance,
        if there has been an error.

        If the user just wants to list the instructions, then don't delete the
        file becaused it's assumed the user will be using another method (such
        as NetBatch) to run the commands which may need the file.  Thus the
        global data file must still be around when the scripts are run.  Also
        save them if the user explicitly requests they not be deleted via
        '--save_global'.

        This should be called at the end of each script which calls DumpGlobalVars().
        """

        import subprocess

        if not (hasattr(options, 'list') and options.list) and not save_global:
            for glob_file in global_file_list:
                if os.path.isfile(glob_file.name):
                    cmd = 'rm -f ' + glob_file.name
                    p = subprocess.Popen(cmd, shell=True)
                    p.communicate()


#####################################################################################
#
# Class for parsing and setting configuration file variables
#
#####################################################################################

class ConfigClass(object):
    """
    Tracing configuration parameters are read in from a file, if it exists.

    Any values for parameters from the command line override the values read
    from the tracing configuration file.
    """

    # Global configuration file parser object
    #
    import ConfigParser
    parser = ConfigParser.ConfigParser()

    def GetVarStr(self, section, name):
        """
        Get a string parameter.

        Return '' if not found or an error occurs.
        """

        value = ''
        if self.parser.has_option(section, name):
            try:
                value = self.parser.get(section, name)
            except ValueError:
                pass

        return value

    def GetVarBool(self, section, name):
        """
        Get a boolean parameter from the config file.

        Return False if not found or an error occurs.
        """

        value = False
        if self.parser.has_option(section, name):
            try:
                value = self.parser.getboolean(section, name)
            except ValueError:
                pass

        return value

    def GetVarInt(self, section, name):
        """
        Get a integer parameter from the config file.

        Return 0 if not found or an error occurs.
        """

        value = 0
        if self.parser.has_option(section, name):
            try:
                value = self.parser.getint(section, name)
            except ValueError:
                pass

        return value

    def GetVarFloat(self, section, name):
        """
        Get a float parameter from the config file.

        Return 0.0 if not found or an error occurs.
        """

        value = 0.0
        if self.parser.has_option(section, name):
            try:
                value = self.parser.getfloat(section, name)
            except ValueError:
                pass

        return value

    def PrintCfg(self):
        """For debugging, print out the sections & values."""

        for section_name in self.parser.sections():
            print 'Section:', section_name
            # print '  Options:', self.parser.options(section_name)
            for name, value in self.parser.items(section_name):
                print '  %s = %s' % (name, value)
            print

    def ParseCfgFile(self):
        """
        Read the parameters from the tracing configuration file.
        """

        # See if the config file has the section 'Parameters'.
        #
        if self.parser.has_section(param_section):
            section = param_section
        else:
            # No parameter section so no parameters to read.
            #
            msg.PrintAndExit('The configuration file does not have the'
                ' required section \'Parameters\'.\n'
                'Add a section with the header \'[Parameters]\'.')

        # Get the values for the tracing parameters from the config file.
        # These can also be given with command line options.
        #
        global program_name, input_name, command, mode
        global debug, compressed, cutoff, num_cores, num_proc, epilog_length, focus_thread
        global maxk, pinplayhome, sdehome, sniper_root, prolog_length, processor, simhome, archsim_config_dir
        global slice_size, warmup_length, verbose, no_focus_thread
        global mpi_options, relog_dir, pin_options, whole_pgm_dir, dir_separator, simpoint_options

        # import pdb ; pdb.set_trace()
        archsim_config_dir  = self.GetVarStr(section,   'archsim_config_dir')
        command         = self.GetVarStr(section,   'command')
        compressed      = self.GetVarStr(section,   'compressed')
        cutoff          = self.GetVarFloat(section, 'cutoff')
        debug           = self.GetVarBool(section,  'debug')
        epilog_length   = self.GetVarInt(section,   'epilog_length')
        input_name      = self.GetVarStr(section,   'input_name')
        simhome         = self.GetVarStr(section,   'simhome')
        simpoint_options = self.GetVarStr(section,   'simpoint_options')
        maxk            = self.GetVarInt(section,   'maxk')
        mode            = self.GetVarStr(section,   'mode')
        mpi_options     = self.GetVarStr(section,   'mpi_options')
        no_focus_thread = self.GetVarBool(section,  'no_focus_thread')
        num_cores       = self.GetVarInt(section,   'num_cores')
        num_proc        = self.GetVarInt(section,   'num_proc')
        pin_options     = self.GetVarStr(section,   'pin_options')
        pinplayhome     = self.GetVarStr(section,   'pinplayhome')
        processor       = self.GetVarStr(section,   'processor')
        program_name    = self.GetVarStr(section,   'program_name')
        prolog_length   = self.GetVarInt(section,   'prolog_length')
        relog_dir       = self.GetVarStr(section,   'relog_dir')
        sdehome         = self.GetVarStr(section,   'sdehome')
        sniper_root     = self.GetVarStr(section,   'sniper_root')
        slice_size      = self.GetVarInt(section,   'slice_size')
        verbose         = self.GetVarBool(section,  'verbose')
        warmup_length   = self.GetVarInt(section,   'warmup_length')
        whole_pgm_dir   = self.GetVarStr(section,   'whole_pgm_dir')

        # Treat the global config value 'dir_separator' differently than the
        # rest of the values.  We always need this to to be set via one of
        # these methods:
        #   1) the default value in the config module
        #   2) parameter given in a tracing configuration file
        #   3) parameter given on command line option
        #
        # If it's not given in the config file which is currently being read,
        # then do NOT set it to the default value returned by GetVarStr ('').
        # If dir_separator is already set in the global config we don't want to
        # overwrite it with the default value ''.
        #
        # import pdb ; pdb.set_trace()
        cfg_dir_separator = self.GetVarStr(section,   'dir_separator')
        if cfg_dir_separator != '':
            dir_separator = cfg_dir_separator

        # For the script rename.py
        #
        global app_version, compiler_version, platform

        # import pdb ; pdb.set_trace()
        app_version       = self.GetVarStr(section,   'app_version')
        compiler_version  = self.GetVarStr(section,   'compiler_version')
        platform          = self.GetVarStr(section,   'platform')

        # Can't use self.GetVarInt() for focus_thread, because the default
        # return value from this method when a parameter is found is 0.
        # However, 0 is a valid focus_thread.  Hence, need the following code
        # to set focus_thread to -1 if it's not a parameter in the config file.
        #
        focus_thread = -1
        if self.parser.has_option(section, 'focus_thread'):
            try:
                focus_thread = self.parser.getint(section, 'focus_thread')
            except ValueError:
                pass

        if debug:
            self.PrintCfg()

    def GetCfgFile(self, cfg_file):
        """
        If the config file exists and has not already been read by a previous
        module, then parse it. It's OK if the default or instance configuration
        files don't exist.
        """

        # import pdb ; pdb.set_trace()
        if os.path.isfile(cfg_file):
            try:
                self.parser.read(cfg_file)
            except self.ConfigParser.MissingSectionHeaderError:
                msg.PrintAndExit('This configuration file does not have any'
                    ' sections.\nIt must at least contain the section '
                    '\'Parameters\'.\n' '   ' + cfg_file)
            except self.ConfigParser.ParsingError:
                msg.PrintAndExit('There was an error parsing the configuration file.\n' + \
                    '   ' + cfg_file)
            self.ParseCfgFile()
        else:
            if cfg_file != default_config_file and \
               cfg_file != self.GetInstanceFileName(config_ext):
                    msg.PrintAndExit('Configuration file does not exist. '
                        '   Please double check the file name.\n' '   ' + cfg_file)

    def CheckRequiredParameter(self, var):
        """Check to make sure a string variable has been initialized."""

        err_msg = lambda string: msg.PrintAndExit('Required parameter \'%s\' not found.\n'
                'It must be defined in order to run the script.  Use either the option\n'
                '--%s or add the parameter to the tracing configuration file.' % (string, string))

        if eval(var) == '':
            err_msg(var)

    def Check2RequiredParameters(self):
        """
        Check to make sure the two basic, required variables have been initialized.
        """

        self.CheckRequiredParameter('program_name')
        self.CheckRequiredParameter('input_name')

    def Check4RequiredParameters(self):
        """
        Check to make sure the two basic, required variables and two additional variables
        required for logging have been initialized.
        """

        self.Check2RequiredParameters()
        self.CheckRequiredParameter('command')
        self.CheckRequiredParameter('mode')

    def FobidErrMsg(self, string, param, char):
        """Print a error msg about forbidden characters."""

        msg.PrintAndExit('Parameter \'%s\' (%s) has the forbidden character \'%s\'.\n'
            'This is not allowed when using SDE/PinPlay. Traces in GTR cannot have these chars.' % \
            (string, param, char))

    def CheckForbiddenChar(self):
        """
        Check to see if several parameters contain one of the 'forbidden' chars, '.' or '_'.
        """

        if program_name.find('_') != -1:
            self.FobidErrMsg('program_name', program_name, '_')
        if program_name.find('.') != -1:
            self.FobidErrMsg('program_name', program_name, '.')
        if input_name.find('_') != -1:
            self.FobidErrMsg('input_name', input_name, '_')
        if input_name.find('.') != -1:
            self.FobidErrMsg('input_name', input_name, '.')

    def GetCfgGlobals(self, options, required_vars):
        """
        Read in all tracing configuration files, if any exist.  Read in the
        pickle file, if it exists. Use tracing paramters to set any global
        variables which need to be set.  This method does NOT require a
        configuration file.

        If boolean 'required_vars' is true, then check to make sure the
        required variables are defined.
        """

        # Get the tracing configuration parameters from all the cfg files given
        # on the command line.  It's OK if the default or instance configuration
        # files don't exist.
        #
        # import pdb ; pdb.set_trace()
        if hasattr(options, 'config_file'):
            for cfg_file in options.config_file:
                if os.path.isfile(cfg_file):
                    self.GetCfgFile(cfg_file)
                else:
                    if cfg_file != default_config_file and \
                       cfg_file != self.GetInstanceFileName(config_ext):
                            msg.PrintAndExit('Configuration file does '
                                'not exist.  Please double check the file name.\n' + \
                                '   ' + cfg_file)

        # Get tracing parameters from the 'per instance' tracing configuration file.
        #
        # import pdb ; pdb.set_trace()
        self.GetCfgFile(self.GetInstanceFileName(config_ext))

        # If this script was called from another script, read in any global
        # variables set in the previous script.  This is done after reading the
        # config file. This allows the global variables passed from the calling
        # script (in pickle file) to override any parameters set in the config
        # file(s).
        #
        gv = GlobalVar()
        gv.ReadGlobalVars(options)

        # Set the global variables using the command line options given when
        # this script was run.  These have the highest precedence and over-ride
        # any parameters already set.
        #
        # import pdb ; pdb.set_trace()
        gv.SetGlobalVars(options)

        # If needed, check to see if required variables have been defined. 
        #
        if required_vars:
            if hasattr(options, 'log') and options.log:
                # All 4 are only required if logging.
                #
                self.Check4RequiredParameters()
            else:
                # Otherwise, only 2 are required.
                #
                self.Check2RequiredParameters()

    def GetInstanceName(self):
        """
        Generate the basename for the per instance files.

        The instance name identifies this specific tracing instance.  It is
        derived from: program_name and input_name.  Using these parameters as
        the file name ensures each tracing instance will have a unique file for
        recording parameters specific to this instance.
        """

        return program_name + dir_separator + input_name

    def GetInstanceFileName(self, f_ext):
        """Get an instance file name with a specific file extension."""

        return self.GetInstanceName() + instance_ext + f_ext

    #####################################################################################
    #
    # Methods for reading/writing tracing parameters in configuration files.
    #
    #####################################################################################

    def SaveCfgParameter(self, param, value):
        """
        Save a parameter/value pair in a configuration file.

        1) If the parameter is already in the file, then replace with the new
           value.
        2) If the parameter isn't already in the file, then add it.
        3) If the configuration file doesn't exist, then create it.
        """

        import tempfile, shutil

        # Use the 'unique' configuration file for this tracing instance.
        #
        # import pdb ; pdb.set_trace()
        config_file = self.GetInstanceFileName(config_ext)

        # Does the config file already exist?
        #
        if os.path.isfile(config_file):

            # File exist, process it.
            #
            try:
                fp = open(config_file, 'rb')
            except:
                msg.PrintAndExit('SaveCfgParameter(), unable to open per instance config file: ' + \
                    config_file)

            # First, check to see if the section 'Parameters' exists.  If not,
            # then it's not a valid config file.
            #
            # import pdb ; pdb.set_trace()
            string = fp.read()
            fp.seek(0, 0)
            if string.find('Parameters') == -1:

                # Not a valid file, just clean up & return without doing
                # anything.  No need for an error msg, just a warning.
                # 
                # TODO - fix this so it does something reasonable
                #
                msg.PrintMsgPlus('WARNING: Tracing configuration file found, but not valid:\n' + \
                    config_file)
                fp.close()
                return
            else:

                # Open a temporary file. This will be used to create a new
                # config file.  
                #
                # import pdb ; pdb.set_trace()
                tmp_file = tempfile.mkstemp()
                tmp_fp = os.fdopen(tmp_file[0], 'wb')
                tmp_name = tmp_file[1]

                # Backup file name for the current configuration file.
                #
                backup_name = config_file + '.bak'

                # Next, check to see if the parameter already exist in the file.
                #
                if string.find(param) != -1:

                    # Parameter in old file.  Find the line with the parameter.
                    # Generate a line with the param & new value.
                    #
                    new_line = ''
                    for line in fp.readlines():
                        if line.find(param) != -1:
                            new_line = param + ':\t' + value + '\n'

                            # Don't write the current line, it contains the old value.
                            #
                            continue

                        # Write current line to the tmp file.
                        #
                        tmp_fp.write(line)

                    # Now write the parameter/value to the end of tmp file.
                    #
                    if new_line != '':
                        tmp_fp.write(new_line)
                else:

                    # Parameter not in the old file.  Copy old file to the tmp file.
                    #
                    for line in fp.readlines():
                        tmp_fp.write(line)

                    # Add the new parameter/value to the end of tmp file.
                    #
                    tmp_fp.write(param + ':\t' + value + '\n')

                # Save the old config file (just in case). Then copy the tmp file
                # as the new per instance config file.  Don't use os.rename() to move
                # the file as this may fail if src/dst file systems are different.
                #
                fp.close()
                tmp_fp.close()
                # import pdb ; pdb.set_trace()
                if os.path.isfile(backup_name):
                    os.remove(backup_name)
                if os.path.isfile(config_file):
                    os.rename(config_file, backup_name)
                shutil.copy(tmp_name, config_file)
                os.remove(tmp_name)
        else:

            # Config file does not exist so create it now.
            #
            try:
                fp = open(config_file, 'wb')
            except:
                msg.PrintAndExit('SaveCfgParameter(), unable to open per instance config file: ' + \
                    config_file)
            fp.write('[Parameters]\n')
            fp.write(param + ':\t' + value + '\n')
            fp.close()

        return

    def GetCfgParam(self, param):
        """
        Get the current value of a parameter from the per instance configuration file.

        Always read the file to ensure the value is the latest one.

        The value is always returned as a string, since the type of the paramter is unknown.
        Return '' if the parameter is not found.
        """

        config_file = self.GetInstanceFileName(config_ext)

        result = ''
        if os.path.isfile(config_file):

            # If the file exists, parse it and get the contents.
            #
            self.parser.read(config_file)

            # See if the config file has the section 'Parameters'. Then
            # try to read the parameter.  Always read it as string since
            # the type is unknown.
            #
            if self.parser.has_section(param_section):
                result = self.GetVarStr(param_section, param)

        return result

    def ClearCfgParameter(self, param):
        """
        Clear the value for a parameter in the per instance configuration file.

        Do this by setting the value to '', since the type of the paramter is unknown.
        """
        self.SaveCfgParameter(param, '')

"""Initialize the module by reading the default configuration file."""

# import pdb ; pdb.set_trace()
Config = ConfigClass()
Config.GetCfgFile(default_config_file)

