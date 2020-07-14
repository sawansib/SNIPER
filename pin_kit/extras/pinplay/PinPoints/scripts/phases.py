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
# $Id: phases.py,v 1.89 2014/06/26 15:03:20 tmstall Exp tmstall $

# Print out messages, including error messages
#
#

import glob
import os
import re
import subprocess
import sys

# Local modules
#
import config
import msg
import util

class Phases(object):
    """
    This module contains all PinPlay tracing phases used in high level scripts.

    In order to use these phases, almost all of them require an options object
    and a config object to be instatiated in the high level script.
    """

    # Several objects used by the methods in this class.
    #
    kit_obj = None
    gv = config.GlobalVar()
    Config = config.ConfigClass()

    def SetKit(self, kit):
        """
        Set the kit to use in this class.

        This can not be set in method __init__ because information about the kit
        may be given on the script command line. Thus this method needs to be called
        explicitly at the correct time.
        """

        self.kit_obj = kit

    def PrintTracingInfo(self, options, wp_log_dir, log_file_name, PrintHome):
        """
        Print the tracing parameters.

        It's very handy to have this info to see what was actually used in the
        run. Often it's not quite what you think it is.  :-)  Also, useful for
        debugging.
        """

        import time
        import locale

        pr_str = '***  TRACING: START' + '  ***    ' + time.strftime('%B %d, %Y %H:%M:%S')
        msg.PrintMsg(pr_str)
        locale.setlocale(locale.LC_ALL, "")

        # RCS version of this script.
        #
        version = '$Revision: 1.89 $'
        version = version.replace('$Revision: ', '')
        version = version.replace(' $', '')
        msg.PrintMsg('Script version ' + version)

        # Arguments passed to the script.
        #
        script = os.path.basename(sys.argv[0])
        msg.PrintMsg('Script:                    ' + script),
        msg.PrintMsgNoCR('Script args:               '),
        for string in sys.argv[1:]:
            msg.PrintMsgNoCR(string + ' '),
        msg.PrintMsg('')

        # Tracing parameters.
        #
        msg.PrintMsg('Program name:              ' + config.program_name)
        msg.PrintMsg('Input name:                ' + config.input_name)
        # import pdb;  pdb.set_trace()
        if options.command != '':
            msg.PrintMsg('Command:                   ' + config.command)
        if options.mode != '':
            msg.PrintMsg('Tracing mode:              ' + config.mode)
        if hasattr(options, 'mpi_options') and options.mpi_options != '':
            msg.PrintMsg('MPI options:               ' + options.mpi_options)
        if config.focus_thread >=0:
            msg.PrintMsg('Focus thread:              ' + str(config.focus_thread))
        if options.log_options != '':
            msg.PrintMsg('Logger options:            ' + options.log_options)
        if config.pin_options != '':
            msg.PrintMsg('Pin options:               ' + config.pin_options)
        if hasattr(options, 'lit_options') and options.lit_options != '':
            msg.PrintMsg('pinLIT options:            ' + options.lit_options)
        if options.replay_options != '':
            msg.PrintMsg('Replayer options:          ' + options.replay_options)
        if config.simpoint_options != '':
            msg.PrintMsg('Simpoint options:          ' + str(config.simpoint_options))
        else:
            msg.PrintMsg('Maxk:                      ' + str(config.maxk))
        if config.mode == config.MPI_MODE or config.mode == config.MPI_MT_MODE:
            msg.PrintMsg('Num proc:                  '  + str(config.num_proc))
        msg.PrintMsg('Warmup length:             ' + \
                locale.format('%d', int(config.warmup_length), True))
        msg.PrintMsg('Prolog length:             ' + \
                locale.format('%d', int(config.prolog_length), True))
        msg.PrintMsg('Slice size (region):       ' + \
                locale.format('%d', int(config.slice_size), True))
        msg.PrintMsg('Epilog length:             ' + \
                locale.format('%d', int(config.epilog_length), True))
        if options.dir_separator != '':
            msg.PrintMsg('Dir separator:             ' + options.dir_separator)
        msg.PrintMsg('WP pinball directory:      ' + wp_log_dir)

        # If the user is deleting the existing tracing instance files, then
        # need to print the generic directory name (generated from
        # 'program_name' and 'input_name').  However, if there are WP pinballs,
        # then use the names of the WP pinballs as directory names.
        #
        if options.delete or options.delete_all or options.delete_wp:
            dirs = [log_file_name]
        else:
            dirs = util.GetDataDir()
            dirs = [p.replace('.Data', '') for p in dirs]
        if len(dirs) != 0:
            if len(dirs) == 1:
                msg.PrintMsg('Data/lit/pp directory:     ' + dirs[0])
            else:
                msg.PrintMsg('Data/lit/pp dirs:          ' + dirs[0])
                del dirs[0]
                for d in dirs:
                    msg.PrintMsg('                           ' + str(d))

        if config.focus_thread == -1:
            thread = 0
        else:
            thread = config.focus_thread
        msg.PrintMsg('Trace file name format:    ' + log_file_name + '_t' + str(thread) + \
            'rX_warmup' + str(config.warmup_length) + '_prolog' + str(config.prolog_length) + \
            '_region' + str(config.slice_size) + '_epilog' + str(config.epilog_length))
        msg.PrintMsg('Instance cfg file:         ' + self.Config.GetInstanceFileName(config.config_ext))
        msg.PrintMsg('Instance status file:      ' + self.Config.GetInstanceFileName(config.phase_status_ext))

        # Print some paths which are useful to know.
        #
        PrintHome(options)                             # Kit location
        script = os.path.basename(sys.argv[0])
        p = subprocess.Popen('which ' + script, shell=True, stdout=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        if stdout != '':
            path = os.path.dirname(stdout)
            msg.PrintMsg('Script path:               ' + os.path.realpath(path))
        msg.PrintMsg('Working dir:               ' + os.getcwd())

        # Info about processor & cores used.
        #
        # import pdb;  pdb.set_trace()
        if hasattr(config, 'processor') and config.processor != '':
            msg.PrintMsg('Processor:                 ' + config.processor)
        else:
            msg.PrintMsg('Processor:                 => Not defined, using default processor <=')
        if hasattr(options, 'num_cores') and options.num_cores != 0:
            msg.PrintMsg('Num cores:                 ' + str(options.num_cores))
        msg.PrintMsg('Number cores/system:       '  + str(util.NumCores()))

        # Print some useful environment variables.
        #
        if os.environ.has_key('PATH'):
            msg.PrintMsg('')
            msg.PrintMsg('PATH: ' + os.environ['PATH'])
        if os.environ.has_key('LD_LIBRARY_PATH'):
            msg.PrintMsg('')
            msg.PrintMsg('LD_LIBRARY_PATH: ' + os.environ['LD_LIBRARY_PATH'])

    def DeleteTracingFileDir(self, options):
        """Delete files & directories generated for only the current tracing instance."""

        # The "base" WP pinball directory is the directory before any filters have
        # been applied.
        #
        # import pdb;  pdb.set_trace()
        wp_log_dir = util.GetBaseWPDir()

        # Variables used to define different file types for this tracing instance.
        #
        relog_wp_dir  = wp_log_dir + config.relog_dir_str
        log_file = util.GetLogFile()
        pb_list = [p.replace('.Data', '') for p in util.GetDataDir()]
        csv_list = [p + '*.csv' for p in pb_list]
        sim_list = [p + '_simpoint_out.txt' for p in pb_list]

        # Only delete these files/dirs which are specific to the current
        # tracing instance defined by tracing parameters.
        #
        util.Delete(options, ' '.join(util.GetDataDir()))
        util.Delete(options, ' '.join(util.GetRegionPinballDir()))
        util.Delete(options, ' '.join(util.GetLitDir()))
        util.Delete(options, relog_wp_dir + '.*')
        util.Delete(options, ' '.join(csv_list))
        util.Delete(options, ' '.join(sim_list))
        util.Delete(options, log_file + '*.NATIVE.TIME')
        util.Delete(options,'verify_' + log_file + '_out.txt')
        util.Delete(options, util.GetStatusFile())
        util.Delete(options,'PARALLEL.PARAM')

        # Delete sniper result directories for this tracing instance.
        #
        sniper_dirs = glob.glob(os.path.join(config.sniper_result_dir, wp_log_dir, util.GetLogFile()+'*'))
        sniper_dirs += [os.path.join(config.sniper_result_dir,os.path.basename(w)+'.pp') for w in sniper_dirs]
        for dir in sniper_dirs:
            util.Delete(options, dir)
        util.Delete(options, os.path.join(config.sniper_result_dir, wp_log_dir))

        # Only delete the whole program pinball directory if it was not
        # specified by the user in a previous run of the scripts or the user
        # gave the option '--delete_wp'. 
        #
        # import pdb;  pdb.set_trace()
        if (hasattr(config, 'whole_pgm_dir') and config.whole_pgm_dir == '') or \
           options.delete_wp:
                util.Delete(options, self.Config.GetInstanceFileName(config.config_ext))
                util.Delete(options, wp_log_dir)
        else:
                msg.PrintMsg('\nNOTE: User defined whole program directory was used.  Will NOT\n'
                    'delete this directory.')
                msg.PrintMsg('    ' + config.whole_pgm_dir)

        # No error checking for deleting.
        #
        return 0

    def DeleteAllTracingFileDir(self, options):
        """Delete ALL files & directories generated for all tracing instances."""

        util.Delete(options, config.wp_dir_basename + '*')
        util.Delete(options, '*.Data')
        util.Delete(options, '*.pp')
        util.Delete(options, '*.lit')
        util.Delete(options, '*.csv')
        util.Delete(options, '*.bb')
        util.Delete(options, '*.NATIVE.TIME')
        util.Delete(options, '*.traceinfo*')
        util.Delete(options, '*.procinfo*')
        util.Delete(options, '*_simpoint_out.txt')

        util.Delete(options,'update_tracinfo_files')
        util.Delete(options,'PARALLEL.PARAM')
        util.Delete(options,'verify_*_out.txt')
        util.Delete(options,'global.data.*')
        util.Delete(options,'*.info.*')
        util.Delete(options, config.sniper_result_dir)

        return 0

    def NativePure(self, options):
        """Run the application natively on the HW without using Pin or Pintools."""

        # import pdb;  pdb.set_trace()
        if options.mode == config.MPI_MODE or options.mode == config.MPI_MT_MODE:
            # MPI command line must be first, so MPI will
            # run the command.
            #
            cmd = util.MPICmdLine(options)
            cmd += ' ' + config.command
        else:
            cmd = config.command
        cmd = 'time ' + cmd
        msg.PrintMsgDate('Running the application on the HW without Pin ' + config.PhaseStr(config.native_pure))
        end_str   = 'Finished pure native run of application ' + config.PhaseStr(config.native_pure)
        result = util.RunCmd(cmd, options, end_str, False)

        return result

    def NativePin(self, logger_cmd, wp_log_dir, log_file_name, options):
        """Run the application natively using Pin (no logging)."""

        # import pdb;  pdb.set_trace()
        cmd = logger_cmd + ' --log_file ' + os.path.join(wp_log_dir, log_file_name)
        cmd += ' --no_log'
        cmd += ' "' + config.command + '"'
        cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd += util.AddCfgFile(options)
        msg.PrintStart(options, 'Running application with Pin only (no pintools) ' + config.PhaseStr(config.native_pin))
        end_str = 'Finished running application with Pin only (no pintools) ' + config.PhaseStr(config.native_pin)
        result = util.RunCmd(cmd, options, end_str, False)

        return result

    def Logger(self, logger_cmd, wp_log_dir, log_file_name, options):
        """Run the logger to generate whole program pinballs."""

        # Check to see if a whole program pinball directory already exists.
        # If so, exit with an error.
        #
        if os.path.isdir(wp_log_dir):
            msg.PrintMsg("\nERROR: Whole program pinball directory already exists: " +
                        wp_log_dir + "\nRemove this directory to proceed with generating "
                        "whole program pinballs.")
            return -1

        # Clear the parameter which stores the name of any whole program pinballs which
        # have been relogged with a filter.  When generating new log files, we want to
        # start off fresh.
        #
        # import pdb;  pdb.set_trace()
        self.Config.ClearCfgParameter('relog_dir')
        config.relog_dir = ''

        # Format the command and execute it.
        #
        cmd = logger_cmd
        if options.log_options != '':
            cmd += ' "--log_options=%s" ' % options.log_options 
        cmd += ' --log_file ' + os.path.join(wp_log_dir, log_file_name)

        # If the command is not already in double quotes, then quote it now.
        # This takes care of cases where the command may redirect input or output
        # or the command has options which contain the char '-'.
        #
        # Assume if there is one double quote, then a 2nd double quote should also
        # already be in the command.
        #
        if config.command.find('"') == -1:
            cmd += ' "' + config.command + '" '
        else:
            cmd += ' ' + config.command
        cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd += util.AddCfgFile(options)
        msg.PrintMsgDate('Generating whole program pinballs %s' % config.PhaseStr(config.log_whole))
        end_str = 'Finished generating whole program pinballs %s' % config.PhaseStr(config.log_whole)
        # import pdb;  pdb.set_trace()
        result = util.RunCmd(cmd, options, end_str, False)

        return result

    def Replay(self, replay_cmd, wp_log_dir, options):
        """Replay the whole program pinballs."""

        # import pdb;  pdb.set_trace()
        cmd = replay_cmd + ' --replay_dir ' + wp_log_dir
        cmd += util.AddNoGlob(options)
        if options.replay_options != '':                 # Add any user defined replay options
            cmd += ' --replay_options "' + options.replay_options + '"'
        cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd += util.AddCfgFile(options)
        msg.PrintStart(options, 'Replaying the set of pinballs in: ' + wp_log_dir)
        end_str   = 'Finished replaying the set of pinballs in: ' + wp_log_dir
        # import pdb;  pdb.set_trace()
        result = util.RunCmd(cmd, options, end_str, False)

        return result

    def RelogWhole(self, replay_cmd, old_wp_dir, new_wp_dir, extra_options, options):
        """
        Relog the old whole program pinballs with options which modify the new
        whole program pinballs in some manner.
        """

        # import pdb;  pdb.set_trace()
        cmd = replay_cmd + ' --replay_dir ' + old_wp_dir
        cmd += util.AddNoGlob(options)
        if options.replay_options != '':           # Add any user defined replay options
            cmd += ' ' + options.replay_options

        cmd += ' --log_options '
        cmd += '"'
        if options.log_options != '':              # Add any user defined log options
            cmd += ' ' + options.log_options
        if extra_options != '':                    # Add the extra relogging options
            cmd += ' ' + extra_options
        cmd += ' -log -xyzzy'
        cmd += util.AddCompressed(options)
        cmd += '"'

        cmd += ' --wp_relog_dir ' + new_wp_dir     # Option which causes replayer to add output file name for relogging
        cmd  += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd  += util.AddCfgFile(options)
        end_str = ''
        result = util.RunCmd(cmd, options, end_str, False)

        return result

    def RelogWholeName(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs with a user defined name.

        No need for extra options here as the knobs required for the users
        desired behavior are (hopefully) contained in the 'log_options' given
        by the user.
        """

        extra_options = ''
        result = self.RelogWhole(replay_cmd, old_wp_dir, new_wp_dir, extra_options, options)

        return result

    def RelogWholeFocus(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs with a focus thread.
        """

        extra_options = '-log:focus_thread ' + str(config.focus_thread)
        result = self.RelogWhole(replay_cmd, old_wp_dir, new_wp_dir, extra_options, options)

        return result

    def RelogWholeSSCMark(self, replay_cmd, old_wp_dir, new_wp_dir, start_mark, stop_mark, options):
        """
        Relog the whole program pinballs to remove instructions between SSC marks.
        """

        if not options.list:
            msg.PrintMsgPlus('Using start SSC mark: ' + str(start_mark))
            msg.PrintMsgPlus('Using stop SSC mark:  ' + str(stop_mark))
        extra_options  = '-log:exclude_code '
        extra_options  += '-log:exclude:start_ssc_mark ' + str(start_mark) + ':repeat '
        extra_options += '-log:exclude:stop_ssc_mark ' + str(stop_mark) + ':repeat '
        result = self.RelogWhole(replay_cmd, old_wp_dir, new_wp_dir, extra_options, options)

        return result

    def RelogWholeRemoveInit(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs to remove initialization instructions.
        """

        # Marks used for Hugh's older library.
        #
        # start_mark = 100
        # stop_mark  = 101

        start_mark = 220
        stop_mark  = 221
        result = self.RelogWholeSSCMark(replay_cmd, old_wp_dir, new_wp_dir, start_mark, stop_mark, options)

        return result

    def RelogWholeRemoveCleanup(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs to remove cleanup instructions.
        """

        start_mark = 330
        stop_mark  = 331
        result = self.RelogWholeSSCMark(replay_cmd, old_wp_dir, new_wp_dir, start_mark, stop_mark, options)

        return result

    def RelogWholeRemoveOMPSpin(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs to remove OpenMP spin instructions.
        """

        start_mark = 4376
        stop_mark  = 4377
        result = self.RelogWholeSSCMark(replay_cmd, old_wp_dir, new_wp_dir, start_mark, stop_mark, options)

        return result

    def RelogWholeRemoveMPISpin(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs to remove MPI spin instructions.
        """

        start_mark = 1000
        stop_mark  = 1001
        result = self.RelogWholeSSCMark(replay_cmd, old_wp_dir, new_wp_dir, start_mark, stop_mark, options)

        return result

    def RelogWholeCodeExclude(self, replay_cmd, old_wp_dir, new_wp_dir, options):
        """
        Relog the whole program pinballs with code exclusion using sets of
        start/stop addresses given in a file.

        Each line in the file contains two addresses.  The first address is the
        initial instruction to be excluded.  The second is the address of the
        first instruction which will be included in the log file.  (I.E.
        instructions are skipped between the 1st address and the instruction
        BEFORE the 2nd address.) Multiple sets of address are allowed, one set
        per line.

        @param options List of command line options from user
        @param xxx     All other options are just passed along to method self.RelogWhole()

        @return Exit code from relogging
        """

        try:
            fp = open(options.relog_code_exclude, 'r')
        except:
            msg.PrintMsg('ERROR: Failed to open code exclusion filtering file:\n'
                '   ' + options.relog_code_exclude)
            return -1

        # Add each set of start/stop address to exclude.
        #
        extra_options = '-log:exclude_code '
        for line in fp.readlines():
            line = line.split()
            if len(line) != 2:
                msg.PrintMsg('ERROR: Code exclusion file must contain exactly two addresses.\n'
                    'First address is initial instruction to exclude.  Second is address of \n'
                    'initial instruction which is not excluded (i.e. where logging should continue).\n'
                    '   ' + ' '.join(line))
                return -1
            start = line[0]
            stop = line[1]
            msg.PrintMsgPlus('Excluding instructions between addresses: %s, %s' % \
                (start, stop))
            extra_options += '-log:exclude:start_address %s:repeat ' % start
            extra_options += '-log:exclude:stop_address %s:repeat ' % stop

        result = self.RelogWhole(replay_cmd, old_wp_dir, new_wp_dir, extra_options, options)

        return result

    def BasicBlockVector(self, replay_cmd, wp_log_dir, options):
        """Generate the basic block vectors for the whole program pinballs."""

        cmd = replay_cmd + ' --replay_dir ' + wp_log_dir
        cmd += util.AddNoGlob(options)
        if options.replay_options != '':                 # Add any user defined replay options
            cmd += ' ' + options.replay_options
        cmd += ' --log_options '
        cmd += '"'
        if options.log_options != '':                  # Add any user defined log options
            cmd += ' ' +options.log_options + ' '
        # import pdb;  pdb.set_trace()
        cmd += '-bbprofile -slice_size ' + str(config.slice_size)
        cmd += '"'
        cmd += ' --bb_add_filename '                     # Option which causes replayer to add output file name for BBV
        cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd += util.AddCfgFile(options)
        end_str   = 'bbv generation'
        result = util.RunCmd(cmd, options, end_str, True)

        return result


    def RunSimPoint(self, param, dirname, file_name):
        """
        Run Simpoint with the basic block vectors for a whole program pinball.

        'param' is a dictionary of objects this method may need.
        'dirname' is the name of the pinball to process.

        Return: exit code from Simpoint
        """


        # Get items from the param dictionary.
        #
        try:
            options = param['options']
        except KeyError:
            msg.PrintMsg('ERROR: method phases.RunSimPoint() failed to get param \'options\'')
            return -1

        # Get the name of the files needed to run simpoints.
        ## 
        basename = util.RemoveTID(file_name)
        data_dir = basename + '.Data'

        if not os.path.isdir(data_dir):
            if not options.debug:
                msg.PrintMsg('ERROR: Can\'t run Simpoints because directory does not exit: ' + data_dir)
                return -1

        # Different behavior if the WP pinballs have been relogged.
        #
        if not options.use_relog_focus:
            # If there is a focus_thread, then use the BB vector file for that TID.
            # Otherwise, use the BBV file for thread 0.
            #
            # NOTE: Code here may need to be changed if/when Simpoints can take more
            # than one BB vector to generate regions.
            #
            # import pdb;  pdb.set_trace()
            if config.focus_thread >= 0:
                if not options.list:
                    msg.PrintMsgPlus('Using BB vector file for thread: ' + str(config.focus_thread))
                path_bb_file  = os.path.join(data_dir, basename) + '.T.' + str(config.focus_thread) + '.bb'
            else:
                if not options.list:
                    msg.PrintMsgPlus('Using BB vector file for thread: 0')
                path_bb_file  = os.path.join(data_dir, basename) + '.T.0.bb'
        else:
            # User has relogged whole program pinballs with a focus thread.  WP
            # pinballs are now per thread, thus always use BB vector file for
            # thread 0.
            if not options.list:
                msg.PrintMsgPlus('Using BB vector file for thread: 0')
            path_bb_file  = os.path.join(data_dir, basename) + '.T.0.bb'

        bb_file  = os.path.basename(path_bb_file)                      # Remove directory name
        sim_out_file  = basename + '_simpoint_out.txt'
        sim_in_file   = 'simpoint_in.txt'

        # Check to make sure the basic block vector file exists.
        #
        if not os.path.isfile(path_bb_file) and not options.list:
            msg.PrintMsgPlus('WARNING: Can\'t open basic block vector file: ' + bb_file)

            # If running in MPI_MT_MODE, then it's possible for one process to
            # not have a thread corresponding to the the current focus thread.
            # However, another process might have this thread.
            # Thus, only return an error if not tracing a MPI_MT application.
            #
            if options.mode == config.MPI_MT_MODE:
                msg.PrintMsg('Since tracing mode is \'mpi_mt\', this may be OK.')
                return 0
            else:
                return 1
        # Format the command to run simpoints.
        #
        cmd = 'simpoint.py'
        cmd += ' --bbv_file ' + bb_file
        cmd += ' --data_dir ' + data_dir
        cmd += ' --simpoint_file ' + basename
        if config.focus_thread >= 0:
            cmd += ' -f ' + str(config.focus_thread)
        else:
            cmd += ' -f 0'

        # Add either the default options used to configure Simpoints or the
        # Simpoint options from the user. 
        #
        # import pdb;  pdb.set_trace()
        if options.simpoint_options == '':
            cmd += ' --maxk ' + str(config.maxk)
            cmd += ' --cutoff ' + str(config.cutoff)
        else:
            cmd += ' --simpoint_options "' + options.simpoint_options  + '"'

        result = 0
        # import pdb;  pdb.set_trace()
        if options.list:
                msg.PrintMsg(cmd)
        else:
            msg.PrintMsgDate('Running Simpoints for: ' + basename)
            if not config.debug:
                # import pdb;  pdb.set_trace()
                msg.PrintMsg(cmd)
                cmd = 'time ' + cmd                     # Add "time" to get timing info

                # Run the script sequentially, not concurrently.
                #
                p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                (stdout, stderr) = p.communicate()
                result = p.returncode
                f = open(sim_out_file, 'w')
                f.write(stdout)
                f.write(stderr)
                f.close()
                msg.PrintMsgDate('Finished running Simpoint for: ' + basename)

                # Encountered problems here, so run sequentially, at least for now.
                # This code runs the cmd concurrently & must be fixed.  The problem is
                # doing the error checking during the parallel runs.  Don't have a way
                # to get the stdout to check for errors when running concurrently.
                #
                # cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
                # cmd += util.AddCfgFile(options)
                # result = util.RunCmd(cmd, options, end_str, True)        # Run concurrent jobs here
                # print stdout

                # Check to make sure the script that runs Simpoints ran correctly.
                #
                if os.path.isfile(sim_out_file):
                    try:
                        f_stdout = open(sim_out_file, 'r')
                    except:
                        msg.PrintMsg('ERROR: Can\'t open Simpoint output file to look for errors.\n'
                            'Missing file: ' + sim_out_file)
                        return -1

                    # Print the output file and look for errors.
                    #
                    error_found = False
                    for line in f_stdout.readlines():
                        msg.PrintMsgNoCR(line)
                        if line.find('ERROR') != -1:
                            error_found = True

                    if error_found:
                        msg.PrintMsg('ERROR: Simpoints failed with an error')
                        return -1

            else:
                # Debugging, so just print cmd.
                #
                msg.PrintMsg(cmd)

        # Clean up the input file.
        #
        if os.path.isfile(sim_in_file):
            os.remove(sim_in_file)
        return result


    ##################################################################
    #
    # Methods to generate region pinballs.
    #
    ##################################################################

    # Maximum number of clusters for this tracing instance.
    #
    max_num_clusters = 0
    region_CSV_file = ''

    # Initial list of WP pinballs to process.
    #
    pb_list = []

    # List of WP pinballs which need to be relogged again because there were
    # overlaps in the previous relogging run.
    #
    relog_pb_list = []

    def GetCSVFiles(self, file_name):
        """Get the region CSV files required to copy the files."""

        # import pdb;  pdb.set_trace()
        basename = util.RemoveTID(file_name)

        data_dir = basename + '.Data'
        region_file  = os.path.join(data_dir, basename) + '.pinpoints.csv'

        csv_file = os.path.basename(region_file)
        base_name = csv_file.replace('.csv', '')

        in_file = base_name + '.in.csv'
        out_file = base_name + '.out.csv'

        # import pdb;  pdb.set_trace()
        return [region_file, in_file, out_file]

    def CountClusters(self, file_name):
        """
        Count the clusters in a region CSV file.

        The information for one cluster is contained in a line with 6 fields,
        separated by commas ','.

        Need to skip comments denoted by '#'. Also need to skip the 2nd line in
        the region CSV file generated by the Perl script.  This line is a header
        describing the various files.  As such, it matches the format of a cluster,
        but isn't a cluster specification.

        Here's the format of the first 4 lines of the Perl generated file:

            # Regions based on 'create_region_file.pl -seq_region_ids -tid 0 -region_file t.simpoints -weight_file t.weights t.bb':
            comment,thread-id,region-id,simulation-region-start-icount,simulation-region-end-icount,region-weight
            # Region = 1 Slice = 88 Icount = 308000214 Length = 3500002 Weight = 0.5432
            cluster 0 from slice 88,0,1,308000214,311500216,0.543210

        @return number of valid clusters
        """

        count = 0

        # If file_name is not a CSV file, then need to get the CSV
        # file corresponding to file_name.
        #
        # import pdb;  pdb.set_trace()
        in_pos  = file_name.find('.in.csv')
        out_pos = file_name.find('.out.csv')
        if in_pos == -1 and out_pos == -1:
            [region_file, in_file, out_file] = self.GetCSVFiles(file_name)
            file_name = region_file
            self.region_CSV_file = region_file    # Save name of region CSV file

        if os.path.isfile(file_name):
            try:
                f = open(file_name)
            except:
                msg.PrintAndExit('method phases.CountClusters() can\'t open file: ' + file_name)

            for line in f.readlines():
                line = line.partition('#')[0]      # Remove any comments
                field = re.split(',', line)
                if len(field) == 6 and field[0] != 'comment' and field[1] != 'thread-id':
                    count += 1
            f.close()

        return count

    def GetMaxClusters(self, param, dirname, file_name):
        """
        If number of clusters for this file > max_num_clusters
        then use it as the new max value.
        """

        count = self.CountClusters(file_name)

        if count > self.max_num_clusters:
            self.max_num_clusters = count

        # Always return 0 as there is no error detection in this method.
        #
        return 0

    def GetFirstRegionCSV(self, param, dir_string, file_name):
        """
        Get the first set of region CVS files from the *.Data directories.

        As a side effect, it also generates the inital list of pinballs to be
        processed.
        """

        import shutil

        try:
            options = param['options']
        except KeyError:
            msg.PrintAndExit('method phases.GetFirstRegionCSV() failed to get param \'options\'')

        # import pdb;  pdb.set_trace()
        [region_file, in_file, out_file] = self.GetCSVFiles(file_name)

        # Error check to make sure the regions CSV file exists.  Print a msg
        # and just return if it doesn't exist.  By returning without an error,
        # this will allow other pinballs to be processed.
        # However, because this pinball will not be put on the 'pb_list'
        # it will not be processed.
        #
        if not os.path.isfile(region_file):
            if not options.list:
                msg.PrintMsgPlus('WARNING: regions CSV file does not exist:\n' +\
                    '         ' + region_file)
                msg.PrintMsg('Pinball will not be processed:\n' +\
                    '         ' + file_name)
                if options.mode == config.MPI_MT_MODE:
                    msg.PrintMsg('Since tracing mode is \'mpi_mt\', this may be OK.')
            return 0

        # Copy the region CSV file.
        #
        shutil.copy(region_file, in_file)

        # Check if need to increase max_num_clusters.
        #
        count = self.CountClusters(in_file)
        if count > self.max_num_clusters:
            self.max_num_clusters = count

        # Add this file to the initial list of pinballs to be processed.
        #
        self.pb_list.append(os.path.join(dir_string, file_name))

        # At this point, all errors have already returned.
        #
        return 0

    def GetNextRegionCSV(self, param, dir_string, file_name):
        """
        Get the 'next' set of region CVS files names.

        Use the output file from the previous run as the input file for this
        run.  As a side effect, it also generates the list of pinballs which
        need to be relogged again.
        """

        import shutil

        # Define a lambda function to print a standard error msg.
        #
        err_msg = lambda string: msg.PrintMsg('ERROR: method phases.GetNextRegionCSV() failed to get '
                        'field: ' + string)

        # Get local copies of items in param.
        #
        try:
            count = param['count']
        except KeyError:
            err_msg('count')
            return -1

        # If the previous output file is non-zero, then it probably needs to
        # be relogged again.
        #
        # import pdb;  pdb.set_trace()
        [region_file, in_file, out_file] = self.GetCSVFiles(file_name)

        # Check to see if the file exists.
        #
        if not os.path.isfile(region_file):
            # Since a warning has already been printed the first time the
            # file was not found.  Just return this time.
            #
            return 0

        if os.path.isfile(out_file) and os.path.getsize(out_file) > 0:

            # Double check to see if there are clusters in the old output file.
            # If so, this means there were overlaps in the last relogging run.
            #
            if self.CountClusters(out_file) > 0:

                # Add this pinball to the list to be relogged again.
                #
                self.relog_pb_list.append(os.path.join(dir_string, file_name))

                # Setup some file names.
                #
                data_dir = os.path.dirname(region_file)
                basename = out_file.replace('.out.csv', '')
                missing_file = os.path.join(data_dir, 'run-' + str(count) + '_missing_' + basename + '.txt')
                msg.PrintMsgDate('Cluster overlap detected, regenerating: ' + \
                        basename.replace('.pinpoints', ''))

                # Copy the old out file to the new in file.  Move the old out file
                # to the *.Data directory to help with debugging.
                #
                shutil.copy(out_file, in_file)          # Overwrite the old input file.
                shutil.move(out_file, missing_file)     # Save the old output file
        return 0

    def GenRegionPinballs(self, replayer_cmd, file_name, options, count):
        """
        Generate a set of region pinballs for one whole program pinball.

        This method may not generate all region pinballs if there is overlap
        between between two representative regions.  Hence, it may be called
        multiple times for a given WP pinball.
        """

        # The basename is needed to get the CSV regions file and other
        # files/directories.
        #
        basename = util.RemoveTID(file_name)

        # Generate the name of the pp directory.
        #
        [region_file, in_file, out_file] = self.GetCSVFiles(file_name)
        name = os.path.basename(basename)
        pp_dir = os.path.join(name + '.pp')
        pp_file = os.path.join(pp_dir, name)

        # Make the directory where the pinballs will be written.
        #
        # import pdb;  pdb.set_trace()
        if not os.path.isdir(pp_dir):
            os.mkdir(pp_dir)

        # Format the command to relog.
        #
        cmd = replayer_cmd + ' --replay_file ' + file_name
        if options.replay_options != '':                 # Add any user defined replay options
            cmd += ' ' + options.replay_options
        cmd += ' --log_options '
        if (options.log_options) != '':                  # Add any user defined log options
            cmd += ' ' + options.log_options
        cmd += '"'
        cmd += ' -log'
        cmd += ' -xyzzy'
        cmd += ' ' + self.kit_obj.knob_regions_in + ' ' + in_file
        cmd += ' ' + self.kit_obj.knob_regions_out + ' ' + out_file
        cmd += ' ' + self.kit_obj.knob_regions_warmup + ' ' + str(config.warmup_length)
        cmd += ' ' + self.kit_obj.knob_regions_prolog + ' ' + str(config.prolog_length)
        cmd += ' ' + self.kit_obj.knob_regions_epilog + ' ' + str(config.epilog_length)
        cmd += ' -log:basename ' + pp_file
        cmd += util.AddCompressed(options)

        # If (usr_relog_focus == True), then we are using WP pinballs which
        # were relogged with a focus thread.  Thus, don't want to use a focus
        # thread because the WP pinballs are already single threaded.
        #
        # import pdb;  pdb.set_trace()
        if not options.use_relog_focus:

            # If user wants no_focus_thread or coop_pinballs, then
            # don't add a focus thread
            #
            if not config.no_focus_thread and not config.coop_pinball:
                if config.focus_thread >= 0:
                    cmd += ' -log:focus_thread ' + str(config.focus_thread)
                else:
                    # Since use_relog_focus != True, this means the WP pinballs
                    # are cooperative.  Because the default is per thread
                    # region pinballs, need to set a default focus thread of 0
                    # to generate per thread pinballs.
                    #
                    cmd += ' -log:focus_thread 0'
        cmd += '"'

        # import pdb;  pdb.set_trace()
        if not options.list:
            msg.PrintMsgDate('Generating pinballs for: (pass ' + str(count) + ') ' + basename)
        if not options.list and config.no_focus_thread:
            msg.PrintMsgPlus('NOTE: Not using focus thread\n')

        # Dump the global vars to a pickle file and add this option
        # to the command. Then do it.
        #
        end_str = basename
        cmd += util.AddGlobalFile(self.gv.DumpGlobalVars(), options)
        cmd += util.AddCfgFile(options)
        if hasattr(options, 'verbose') and options.verbose and not options.list:
            msg.PrintMsg('GenRegionPinballs, calling RunCmd()')
        result = util.RunCmd(cmd, options, end_str, True)  # Run concurrent jobs here

        return result

    def GenAllRegionPinballs(self, dirname, replayer_cmd, options):
        """
        Generate all region pinballs for a set of whole program pinball directories.

        If there are overlap in region pinballs, the method GenRegionPinballs()
        is called again until either there are no more overlaps or it has been
        called 'self.max_num_clusters' times.

        A region consists of the following:
            warmup instructions
            epilog instructions
            region instructions
            epilog instructions
        """

        # Get the maximum number of clusters in each CSV file in
        # 'self.max_num_clusters'.  Call with no_glob = True
        #
        # import pdb;  pdb.set_trace()
        param = {'options': options}
        result = util.RunAllDir(dirname, self.GetMaxClusters, True, param)
        if result != 0:
            msg.PrintMsg('Error found during region pinball generation (1)')
            return result

        # Make sure there is at least one cluster in the CSV file.
        #
        if self.max_num_clusters < 1:
            msg.PrintMsg('ERROR: No clusters were found in the CSV file.\n'
            '   ' + self.region_CSV_file)
            return -1

        # Get the first set of region CSV files from the *.Data directories.
        # This method generates the list of pinballs to be processed in
        # 'self.pb_list'.
        # Call with no_glob = True
        #
        # import pdb;  pdb.set_trace()
        result = util.RunAllDir(dirname, self.GetFirstRegionCSV, True, param)
        if result != 0:
            msg.PrintMsg('Error found during region pinball generation (2)')
            return result

        # Loop 'self.max_num_clusters' times, or until there are no clusters
        # left for any process.
        #
        # import pdb;  pdb.set_trace()
        count = 1
        while count <= self.max_num_clusters:
            self.relog_pb_list = []             # Empty list of pinballs which have region overlaps

            # Generate region pinballs for each WP pinball.  Then wait for all
            # concurrent jobs to finished.
            #
            for pinball in self.pb_list:
                self.GenRegionPinballs(replayer_cmd, pinball, options, count)
            if not options.list:
                msg.PrintMsgPlus('Waiting on concurrent region pinball generation')
            result = util.WaitJobs(options)

            # If just listing the command, then return now
            #
            if options.list:
                 return 0

            # Now check for errors, after the check for just listing. Don't check
            # before now because if listing the commands there will be errors.
            #
            # import pdb;  pdb.set_trace()
            if result != 0:
                msg.PrintMsg('Error found during region pinball generation (3)')
                return result

            # See if there are pinballs which need to be relogged again because of
            # overlapping clusters in the previous relogging run.
            # Call with no_glob = True
            #
            # import pdb;  pdb.set_trace()
            param['count'] =  count
            result = util.RunAllDir(dirname, self.GetNextRegionCSV, True, param)
            if result != 0:
                return result   # Error msg already printed in GetNextRegionCSV()
            if self.relog_pb_list != []:
                self.pb_list = self.relog_pb_list
            else:
                break       # No more pinballs to relog, exit loop

            count += 1

        # Check to see if there were still pinballs to relog when the loop was
        # executed 'self.max_num_clusters' times.  If so, then is an error.
        #
        if count > self.max_num_clusters and self.relog_pb_list != []:
            msg.PrintMsg("ERROR: Too many iterations in method phases.GenAllRegionPinballs().\n"
                "   Problems encountered during region pinball generation.")
            return -1

        # Clean up any remaining *.csv files.
        #
        files = util.GetLogFile()
        files = glob.glob(files + '*.csv')
        for f in files:
            os.remove(f)

        # If there was a problem generating region pinballs, it was already
        # detected and the script has exited with an error.
        #
        return 0

    ###################################################################
    #
    # Methods to get the prediction error.
    #
    ###################################################################


    def GetPredictMetric(self, dirname, sim_kit, options):
        """
        Get the predicted value for a metric for the pinballs in a directory.

        The predicted metric is calculated as the sum of the metric for each
        pinball multiplied by it's weight.

        """

        # Get a list of the simulator output files in the directory.
        #
        # import pdb;  pdb.set_trace()
        files = glob.glob(os.path.join(dirname, '*' + sim_kit.file_ext + '*'))
        files.sort()

        # Check to make sure there is at least one simulator output file.  If
        # not, this is an error.
        #
        if files == []:
            msg.PrintMsgPlus('WARNING: No simulator data files found in dir: ' + dirname)
            return -1.0

        # Define a lambda function to print an error message. This time include file name.
        #
        err_msg = lambda string, fname: msg.PrintMsg('ERROR: method phases.GetPredictMetric() failed to '
                    'get field: ' + string + '\nfrom file: ' + fname)

        # Get the metric and weight for each simulator data file and calculate the
        # weighted sum metric for the process.
        #
        # import pdb;  pdb.set_trace()
        predict_metric = 0.0
        if hasattr(options, 'verbose') and options.verbose:
            print 'Metric:\t\t    Weight:\tFile:'
        for name in files:
            # Get the fields from the file name.
            #
            # import pdb ; pdb.set_trace()
            fields = util.ParseFileName(name)
            try:
                warmup = fields['warmup']
            except:
                err_msg('warmup', name)
                return -1.0
            try:
                weight = fields['weight']
            except:
                err_msg('weight', name)
                return -1.0

            # Get the metric of interest for just the region for this data file.
            #
            if config.focus_thread >= 0:
                metric = sim_kit.GetRegionMetric(name, warmup, config.focus_thread, options)
            else:
                metric = sim_kit.GetRegionMetric(name, warmup, 0, options)
            if hasattr(options, 'verbose') and options.verbose:
                print '%10.5f \t%10.4f \t%s' % (metric, weight, os.path.basename(name))

            if metric == -1.0:
                # An error was found. Print a warning message, but continue processing.
                #
                msg.PrintMsgPlus('WARNING: There was a problem with simulator data for pinball:\n'
                    '         ' + name)
                continue
            else:
                predict_metric += metric * weight

        return predict_metric

    def GetMeasurePredictMetric(self, sim_kit, options):
        """
        Get measured metric of interest from the WP pinballs and predicted
        metric from the region pinballs for all processes.

        Return a list of tuples.  Each tuple contains: PID, measured metric, predicted metric
        """

        import re, locale

        # List of lists which contain the base filename and measured metric of interest for each WP pinball.
        #
        name_metric = []

        # Get the whole program pinballs simulator data files.
        #
        wp_pb = util.GetWPPinballs()
        sim_files = [glob.glob(w + '*' + sim_kit.file_ext + '*') for w in wp_pb]

        # import pdb;  pdb.set_trace()
        for pb_name in sim_files:

            # Check to make sure there really is a file.
            #
            if pb_name == []:
                continue

            # Remove directory, TID and file extension to get the base WP pinball name.
            #
            pb_name = pb_name[0]
            basename = os.path.basename(pb_name)
            basename = re.split(sim_kit.file_ext + '*', basename)[0]
            basename = util.RemoveTID(basename)

            # If there is a focus thread, then get the metric from the WP pinballs
            # for this thread.  If no focus thread, then use TID=0.
            #
            if config.focus_thread >= 0:
                value = sim_kit.GetLastMetric(pb_name, config.focus_thread, options)
            else:
                value = sim_kit.GetLastMetric(pb_name, 0, options)

            if value == -1.0:
                # An error was found. Don't put this file in the list to be
                # processed.  However, this may be OK, so go on the next WP
                # pinball.
                msg.PrintMsgPlus('WARNING: There was a problem with simulator data for pinball:\n' 
                    '        ' + pb_name)
                msg.PrintMsg('Prediction error correlation will not be calculated for this process.')
                continue

            # Add the name/metric to the list.
            #
            msg.PrintMsg(basename)
            msg.PrintMsg('  Intermediate result, measured CPI:            ' + \
                str(locale.format('%7.4f', value, True)))
            name_metric.append([basename, value])

        # Check to make sure at least one whole program pinball had simulator data.
        #
        if name_metric == []:
            if not options.list:
                msg.PrintMsg('Unable to get simulator data for any whole program pinballs.\n'
                    'Check to make sure you have generated the files using either\n'
                    'option --whole_sim or the appropriate option for your simulator.')
            return None

        # result contains a tuple of three items for each process:
        #   WP pinball basename, measured metric, predicted metric
        #
        result = []

        # For each process with a metric for the WP pinballs, get the predicted metric from
        # the simulator data for the region pinballs.
        #
        # import pdb;  pdb.set_trace()
        for p in name_metric:
            basename = p[0]
            measure_metric = p[1]
            pp_dir = basename + '.pp'
            predict_metric = self.GetPredictMetric(pp_dir, sim_kit, options)
            msg.PrintMsg(basename)
            msg.PrintMsg('  Intermediate result, predicted CPI:           ' + \
                str(locale.format('%7.4f', predict_metric, True)))
            if predict_metric > 0.0:
                result.append((basename, measure_metric, predict_metric))

        # Check to make sure at least one whole program pinball had CMSim data.
        #
        if result == []:
            if not options.list:
                msg.PrintMsg("Unable to get simulator data for any region pinballs.  Check to make\n"
                    "sure you have generated these files using either the option --region_sim\n"
                    "or the appropriate option for your simulator.")
            return None

        return result

    def CalcPredError(self, dirname, sim_kit, options):
        """
        Calculate the prediction error correlation for a set of whole program
        pinballs and the associated representative regions.

        Prediction error is defined as the ratio of the predicted metric
        of interest, calculated from the weighted sum of the metric for the
        regions, compared to this metric measured for the entire WP pinball.
        It's used to determine how representative the regions are of
        application behavior.  As the ratio gets closer to 1.0, the more
        representative the regions are of application behavior.

        """

        import locale
        # If in debug mode, just return.
        #
        if options.debug:
            return 0

        # Get a list of tuples with the required data.  Each tuple contains:
        #    PID, measured MPI, predicted MPI
        #
        # import pdb;  pdb.set_trace()
        mpi_list = self.GetMeasurePredictMetric(sim_kit, options)

        # Check for any errors.
        #
        if mpi_list == None:
            return -1

        for item in mpi_list:

            # Print the MPI values and the prediction error.
            #
            name = item[0]
            measure_mpi = item[1]
            predict_mpi = item[2]
            msg.PrintMsg('')
            msg.PrintMsg(name)
            msg.PrintMsg('  Predicted metric:          ' + str(locale.format('%7.4f', predict_mpi, True)))
            msg.PrintMsg('  Measured metric:           ' + str(locale.format('%7.4f', measure_mpi, True)))
            msg.PrintMsg('  Prediction error:          ' + str(locale.format('%7.4f', 1-(predict_mpi/measure_mpi), True)) + ' 1-(p/m)')
            msg.PrintMsg('  [Functional correlation:   ' + str(locale.format('%7.4f', predict_mpi/measure_mpi, True)) + ' (p/m)]')

        return 0
