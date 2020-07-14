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
# $Id: logger.py,v 1.71 2014/06/01 16:47:28 tmstall Exp tmstall $

import sys
import os
import random
import subprocess
import optparse

# Local modules
#
import cmd_options
import config
import kit
import msg
import util

class Logger(object):

    """
    Generate log files for an application

    This class is the low level primative which runs an application with the
    logger to generate pinballs (log files).  It works with 4 classes of
    applications:

        single-thread, multi-thread, MPI (multi-process) and multi-threaded MPI

    It currently does NOT work with multi-process apps which are not MPI.
    """

    def ParseMode(self, mode):
        """
        Parse logging mode, exiting with error msg if mode not valid.

        @return Mode type
        """

        try:
            return {'st'     : config.ST_MODE,
                    'mt'     : config.MT_MODE,
                    'mpi'    : config.MPI_MODE,
                    'mpi_mt' : config.MPI_MT_MODE}[mode]
        except:
                msg.PrintHelpAndExit('Invalid mode \''+ mode +'\' passed to --mode')

    def AddOptionIfNotPresent(self, options, opt, arg):
        """
        This function adds an option to the tool if the option was not already
        passed in the --log_options switch

        @param options List of command line options
        @param opt     Option to add
        @param arg     Argument for option

        @return String containing option and argument
        """

        # import pdb;  pdb.set_trace()
        raw_options = options.log_options

        # option was not passed in the command line
        #
        if raw_options.find(opt) == -1:
                return ' ' + opt + ' ' + arg + ' '
        return ''

    def MpModeOptions(self, options):
        """
        Add multi-process logging mode options.

        @param options List of command line options

        @return String of knobs required for MT apps
        """

        pintool_options = self.AddOptionIfNotPresent(options,'-log:mp_mode','')

        # print out information about shared-segments
        pintool_options += self.AddOptionIfNotPresent(options,'-log:mp_verbose','1')

        # attach to a pre-existing run of related processes
        if (options.attach):
                pintool_options += self.AddOptionIfNotPresent(options,'-log:mp_attach','1')

        return pintool_options

    def ParseCommandLine(self):
        """
        Parse command line arguments and returns pin and tools options and app command line.

        @return List containing: options, pin_options, pintool_options, prg_cmd_line, mpi_cmd_line, kit_obj
        """

        # command line options for the driver
        #
        version = '$Revision: 1.71 $';      version = version.replace('$Revision: ', '')
        ver = version.replace(' $', '')
        us = '%prog [options] --log_file FILE application app_arguments\nVersion: ' + ver
        desc = 'Runs application with the logger Pintool and generates whole program '\
               'pinballs. Required arguments include the application to run and any of it\'s arguments. '\
               'Must also supply the option "--log_file FILE". This option gives the '\
               'name of the pinball the logger generates. ' \
               'This name can include a directory as well as a file.' \

        parser = optparse.OptionParser(usage=us, description=desc, version=ver)

        # Define the command line options which control the behavior of the
        # script.  Some of these methods take a 2nd argument which is the empty
        # string ''.   If the script uses option groups, then this parameter is
        # the group.  However, this script does not use option groups, so the
        # argument is empty.
        #
        cmd_options.attach(parser)
        cmd_options.compressed(parser, '')
        cmd_options.config_file(parser)
        cmd_options.debug(parser)
        cmd_options.focus_thread(parser, '')
        cmd_options.global_file(parser)
        cmd_options.list(parser, '')
        cmd_options.log_file(parser)
        cmd_options.log_options(parser)
        cmd_options.mode(parser, '')
        cmd_options.mpi_options(parser, '')
        cmd_options.msgfile_ext(parser)
        cmd_options.no_log(parser)
        cmd_options.num_proc(parser, '')
        cmd_options.pid(parser)
        cmd_options.pinplayhome(parser, '')
        cmd_options.pin_options(parser)
        cmd_options.save_global(parser)
        cmd_options.sdehome(parser, '')
        cmd_options.verbose(parser)

        # import pdb;  pdb.set_trace()
        (options, args) = parser.parse_args()

        # Read in configuration files and set global variables.
        # No need to read in a config file.
        #
        config_obj = config.ConfigClass()
        config_obj.GetCfgGlobals(options, False)    # No, don't need required parameters

        # Once the tracing configuration parameters are read, get the kit in
        # case pinplayhome was set on the command line.
        #
        # import pdb;  pdb.set_trace()
        kit_obj = self.GetKit()

        # Error check to make sure user gave application mode.
        #
        if options.mode != '':
            mode = options.mode
        else:
            if config.mode != '':
                mode = config.mode
            else:
                msg.PrintAndExit('Application mode was not given.\n' \
                    'Use --mode with one of these arguments: st|mt|mpi|mpi_mt')
        mode = self.ParseMode(mode)

        pin_options = options.pin_options
        pintool_options = ''

        # Get the appropriate pintool options for the current application mode.
        #
        mpi_cmd_line = ''
        if mode == config.MPI_MODE or mode == config.MPI_MT_MODE:
            # Need to add the MPI options to the existing
            # MT options already in 'pintool_options'.
            #
            pintool_options += self.MpModeOptions(options)
            mpi_cmd_line = util.MPICmdLine(options)

        # Log file name must be given.
        #
        # import pdb;  pdb.set_trace()
        if options.log_file == '':
            msg.PrintAndExit('Log file basename was not given.\n' \
                'Must give basename with option: --log_file FILE')
        else:
            pintool_options += self.AddOptionIfNotPresent(options, '-log:basename', options.log_file)
        pintool_options += util.AddMt(options)
        pintool_options += util.AddCompressed(options)
        pintool_options += util.GetMsgFileOption(options.log_file)

        # Add the user logging options.
        #
        pintool_options += options.log_options

        # Get the application command line & it's options.
        #
        # NOTE: Everything which is not a legal option is assumed to be part of
        # the application command line. If the user gives an "ilegal" option
        # which the script does not recognize, this option will be passed to
        # the application being traced!  This may cause unusual behavoir in the
        # application.
        #
        # import pdb;  pdb.set_trace()
        prg_cmd_line = " ".join(args)

        return [options, pin_options, pintool_options, prg_cmd_line, mpi_cmd_line, kit_obj]

    def GetKit(self):
        """
        Get the PinPlay kit.

        @return PinPlay kit
        """

        return kit.Kit()

    def RunMPCreate(self, kit_obj, mpi_cmd_line):
        """
        Create mp_pool when logging MPI apps.

        @param kit_obj      Kit
        @param mpi_cmd_line Current MPI command line

        @return String with MP key and a knob required for mp_pools, or null string
        """

        # import pdb;  pdb.set_trace()
        if mpi_cmd_line != '':

            # Start command with pin and pintool.
            #
            # import pdb;  pdb.set_trace()
            cmd  = os.path.join(kit_obj.path, kit_obj.pin)
            cmd += kit_obj.GetPinToolKnob()

            # Logging mp_pool creation knobs.
            #
            log_key = ' -log:mp_key ' + str(random.randint(0,32728))
            cmd += ' -log '
            cmd += log_key
            cmd += ' -log:mp_create_pool '
            cmd += ' -- echo'

            # Execute the cmd
            #
            msg.PrintMsgPlus('Creating mp_pools for MPI tracing')
            msg.PrintMsg(cmd)
            if not config.debug:
                p = subprocess.Popen(cmd, shell=True)
                p.communicate()
                del p

            # Add this because it's needed by SDE for logging,
            # but not for PinPlay.
            #
            return log_key + ' -log:mp_attach '

        return ''

    def RunMPDelete(self, kit_obj, mpi_cmd_line, log_key):
        """
        Delete mp_pool when logging MPI apps.

        @param kit_obj      Kit
        @param mpi_cmd_line Current MPI command line
        @param log_key      Key to mp_pool to delete

        @return No return value
        """

        # If required, format and execute the MPI command to destroy mp_pools.
        #
        # import pdb;  pdb.set_trace()
        if mpi_cmd_line != '':

            # Start command with pin and pintool.
            #
            # import pdb;  pdb.set_trace()
            cmd  = os.path.join(kit_obj.path, kit_obj.pin)
            cmd += kit_obj.GetPinToolKnob()

            # Remove the string '-log:mode_attach' because it's only
            # used for logging.
            #
            pos = log_key.find('-log:mode_attach')
            if pos != -1:
                log_key = log_key[0:pos]

            # Logging mp_pool deletion knobs.
            #
            cmd += ' -log '
            cmd += log_key
            cmd += ' -log:mp_delete_pool '
            cmd += ' -- echo'

            # Execute the cmd
            #
            msg.PrintMsgPlus('Deleting mp_pools for MPI tracing')
            msg.PrintMsg(cmd)
            if not config.debug:
                p = subprocess.Popen(cmd, shell=True)
                p.communicate()
                del p

        return

    def Run(self):
        """
        Get all the user options and run the logger.

        @return Exit code from the logger pintool
        """

        # import pdb;  pdb.set_trace()
        [options, parsed_pin_opts, parsed_pintool_opts, prg_cmd_line, \
            mpi_cmd_line, kit_obj] = self.ParseCommandLine()

        # Error check for application command line
        #
        if prg_cmd_line == '':
            if config.command != '':
                prg_cmd_line = config.command
            else:
                string = 'no program command line specified.\nUsage: ' + os.path.basename(sys.argv[0]) + \
                      ' [options] --log_file FILE binary arguments\n' \
                      'Need to add binary and it\'s arguments.'
                msg.PrintAndExit(string)

        # Set the binary type in the kit.  Assume the first string in
        # 'prg_cmd_line' is the binary. 
        #
        # import pdb;  pdb.set_trace()
        binary = prg_cmd_line.split()[0]
        kit_obj.SetBinaryType(binary)
        if kit_obj.binary_type == config.ARCH_INVALID:
            msg.PrintMsg('\nWARNING: Unable to determine binary file type.\n'
                'Perhaps the string assumed to be the binary is incorrect.\n'
                '   Command line:     ' + prg_cmd_line + '\n'
                '   Binary: (assumed) ' + binary + '\n'
                'Setting binary type to \'Intel64\' as the default value.\n')

        # Print out the version number
        #
        if config.debug:
            msg.PrintMsg(' $Revision: 1.71 $')

        # Get path to the kit pin binary and the appropriate pintool name
        #
        cmd = os.path.join(kit_obj.path, kit_obj.pin)

        # Print out all the parsed options
        #
        if config.verbose:
            msg.PrintMsg('parsed_pin_opts:     ' + parsed_pin_opts)
            msg.PrintMsg('parsed_pintool_opts: ' + parsed_pintool_opts)
            msg.PrintMsg('prg_cmd_line:        ' + prg_cmd_line)
            msg.PrintMsg('mpi_cmd_line:        ' + mpi_cmd_line)

        # Kit tool options

        pin_options  = ''
        pin_options  = pin_options + parsed_pin_opts

        # Pintool options, including the base logging options for all runs.
        #
        pintool_options  = ''
        pintool_options = ' -log -xyzzy -log:syminfo -log:pid '
        pintool_options = pintool_options + parsed_pintool_opts

        # Build command line, including MPI cmd (if present).  Then kit tool arguments.
        #
        cmd = mpi_cmd_line + ' ' + cmd + ' ' + pin_options

        # If logging, then add the PinTool options to the command and
        # generate the mp_pool.
        #
        # import pdb;  pdb.set_trace()
        if not options.no_log:
            cmd += kit_obj.GetPinToolKnob()
            cmd += pintool_options
            log_key = self.RunMPCreate(kit_obj, mpi_cmd_line)
            cmd += log_key
        else:
            cmd += kit_obj.GetPinToolKnob()

        # Add program and arguments 
        #
        cmd += ' -- ' + prg_cmd_line

        # Print out command line used for pin and pintool
        #
        string = '\n' + cmd
        msg.PrintMsg(string)

        # Finally execute the command line and gather stdin and stdout.
        # Exit with the return code from executing the logger.
        #
        result = 0
        # import pdb;  pdb.set_trace()
        if not config.debug:
            cmd = 'time ' + cmd
            p = subprocess.Popen(cmd, shell=True)
            p.communicate()
            result = p.returncode

        # If logging, delete the mp_pool.
        #
        if not options.no_log:
            self.RunMPDelete(kit_obj, mpi_cmd_line, log_key)

        return result

def main():
       """
       This method allows the script to be run in stand alone mode.

       @return Exit code from running the script
       """

       logger = Logger()
       result = logger.Run()
       return result

# If module is called in stand along mode, then run it.
#
if __name__ == "__main__":
    result = main()
    sys.exit(result)

