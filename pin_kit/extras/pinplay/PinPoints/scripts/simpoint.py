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
# Script to run Simpoint then generate region CSV files.
#
# $Id: simpoint.py,v 1.20.1.6 2014/06/01 17:05:18 tmstall Exp tmstall $

import os
import sys
import shutil
import optparse

import cmd_options
import msg
import util


class SimPoint(object):

    simpoint_bin = 'simpoint'
    csv_bin = 'regions.py'
    generic_name = 't.bb'
    proj_bbv_file = 'projected_t.bb'

    def ParseCommandLine(self):
        """Get the options from the command line and check for errors."""

        # Define and get command line options.
        #
        version = '$Revision: 1.20.1.6 $';      version = version.replace('$Revision: ', '')
        ver = version.replace(' $', '')
        us = '%prog --bbv_file FILE --data_dir DIR FILE --simpoint_file FILE [options]'
        desc = 'Runs Simpoint and then generates the region CSV file.' \
                '                                                                    ' \
                'Required options: --bbv_file, --data_dir, --simpoint_file'

        parser = optparse.OptionParser(usage=us, version=ver, description=desc)

        cmd_options.debug(parser)
        cmd_options.list(parser, '')
        cmd_options.bbv_file(parser, '')
        cmd_options.data_dir(parser)
        cmd_options.simpoint_file(parser)
        cmd_options.cutoff(parser, '')
        cmd_options.focus_thread(parser, '')
        cmd_options.maxk(parser, '')
        cmd_options.simpoint_options(parser, '')

        # import pdb;  pdb.set_trace()
        (options, args) = parser.parse_args()

        # Error check input to make sure all required options are on the command line.
        #
        if options.bbv_file == '':
            msg.PrintAndExit('Basic block vector file must be defined with option: --bbv_file FILE')
        if options.data_dir == '':
            msg.PrintAndExit('Simpoint data directory must be defined with option: --data_dir DIR')
        if options.simpoint_file == '':
            msg.PrintAndExit('Simpoint output must be defined with option: --simpoint_file FILE')

        # The data_dir should exist and contain the BBV file.
        #
        if not os.path.isdir(options.data_dir):
            msg.PrintAndExit('Data directory exist: ' + options.data_dir)
        if not os.path.isfile(os.path.join(options.data_dir, options.bbv_file)):
            msg.PrintAndExit('Basic block vector file does not exist: ' + options.bbv_file)

        return (options, args)

    def NormProjectBBV(self, options):
        """
        Normalize and project the basic block vector file instead of doing this in Simpoint.

        This is required so we can combine BBV and LDV files as frequency vector file given
        to Simpoint.

        @return result of command to generating CSV file
        """

        # Format the command and run it.
        #
        # import pdb;  pdb.set_trace()

        # Use options for the Python script to generate the CSV file.
        #
        output_file = 'normalize_project.out'
        cmd  = self.csv_bin
        cmd += ' --project_bbv'
        cmd += ' ' + self.generic_name
        cmd += ' > ' + self.proj_bbv_file + ' 2> ' + output_file

        # msg.PrintMsg('')
        # print 'cmd: ' + cmd
        # import pdb;  pdb.set_trace()
        result = util.RunCmd(cmd, options, '', False)

        return result

    def RunSimpoint(self, options):
        """
        Format and execute the command to run Simpoint.

        @return result of running Simpoint
        """

        # Format the Simpoint command and run it.  Can use either the
        # original set of options which used t.bb as the input, or
        # the new set of options which consumes normalized, projected
        # BBV files.
        #
        # orig_simp_options = False     # Use new Simpoint options
        orig_simp_options = True        # Use original Simpoint options
        cmd  = self.simpoint_bin
        if orig_simp_options:
            cmd += ' -loadFVFile ' + self.generic_name
        else:
            cmd += ' -fixedLength on -loadVectorsTxtFmt ' + self.proj_bbv_file

        # Add either the default options used to configure Simpoints or the
        # Simpoint options from the user.
        #
        if options.simpoint_options == '':
            cmd += ' -coveragePct ' + str(options.cutoff)
            cmd += ' -maxK ' + str(options.maxk)
        else:
            cmd += ' ' + options.simpoint_options

        cmd += ' -saveSimpoints ./t.simpoints -saveSimpointWeights ./t.weights -saveLabels t.labels'
        cmd += ' > simpoint.out 2>&1'
        # import pdb;  pdb.set_trace()
        result = util.RunCmd(cmd, options, '', False)

        return result

    def GenRegionCSVFile(self, options):
        """
        Format and execute the command to generate the regions CSV file.

        @return result of command to generating CSV file
        """
        # Setup some stuff for generating regions CSV files.
        #
        # import pdb;  pdb.set_trace()
        cutoff_suffix = ''
        if options.cutoff < 1.0:
            cutoff_suffix = '.lpt' + str(options.cutoff)
        pos = options.data_dir.find('.Data')
        regions_csv_file = options.data_dir[:pos] + '.pinpoints.csv'
        output_file = 'create_region_file.out'

        # Format the command to generate the region CSV file and run it.
        #
        # import pdb;  pdb.set_trace()
        if options.focus_thread < 0:
            tid = 0
        else:
            tid = options.focus_thread

        # orig_perl_script = True  # Use Chuck's original Perl script
        orig_perl_script = False   # Use regions.py script
        if orig_perl_script == True:
            # Use Chuck's Perl script to generate the CSV file.
            #
            cmd = 'create_region_file.pl'
            cmd += ' ' + self.generic_name
            cmd += ' -seq_region_ids -tid ' + str(tid)
            cmd += ' -region_file t.simpoints' + cutoff_suffix
            cmd += ' -weight_file t.weights' + cutoff_suffix
        else:
            # Use the new Python script to generate the CSV file.
            #
            cmd  = self.csv_bin
            cmd += ' ' + self.generic_name
            cmd += ' -f ' + str(tid)
            cmd += ' --region_file t.simpoints' + cutoff_suffix
            cmd += ' --weight_file t.weights' + cutoff_suffix
        cmd += ' > ' + regions_csv_file + ' 2> ' + output_file
        result = util.RunCmd(cmd, options, '', False)

        return result, regions_csv_file

    def Run(self):
        """Run the scripts required to run simpoint and generate a region CSV file with the results."""

        msg.PrintMsg('')

        # Get the command line options
        #
        (options, args) = self.ParseCommandLine()

        # Make sure required utilities exist and are executable.
        #
        # import pdb;  pdb.set_trace()
        if util.Which(self.simpoint_bin) == None:
            msg.PrintAndExit('simpoint binary not in path.\n'
                'Add directory where it exists to your path.')
        if util.Which(self.csv_bin) == None:
            msg.PrintAndExit('script to generate the region CSV file not in path.\n'
                'Add directory where it exists to your path.')

        # Go to the data directory. Both utilities should be run in this directory.
        #
        os.chdir(options.data_dir)

        # Copy the specific BBV file to the generic name used by simpoint.
        #
        if os.path.isfile(self.generic_name):
            os.remove(self.generic_name)
        shutil.copy(options.bbv_file, self.generic_name)

        # Get the instruction count and slice_size from the BBV file.
        #
        try:
            f = open(self.generic_name)
        except:
            msg.PrintAndExit('problem opening BBV file: ' + self.generic_name)
        instr_count = 0
        slice_size = 0
        for line in f.readlines():
            if line.find('Dynamic') != -1:
                tmp = line.split()
                count = tmp[len(tmp)-1]
                if count > instr_count:
                    instr_count = int(count)
            if line.find('SliceSize') != -1:
                tmp = line.split()
                size = tmp[len(tmp)-1]
                if size > slice_size:
                    slice_size = int(size)

        # Check to make sure instruction count > slice_size.
        #
        if slice_size > instr_count:
            import locale
            locale.setlocale(locale.LC_ALL, "")
            msg.PrintAndExit('Slice size is greater than the number of instructions.  Reduce parameter \'slice_size\'.' + \
                '\nInstruction count: ' + locale.format('%14d', int(instr_count), True) + \
                '\nSlice size:        ' + locale.format('%14d', int(slice_size), True))

        # Run the scripts to generate the regions CSV file.
        #
        # When using Chuck's original Perl scripts, don't generated a
        # normalized, projected BBV file.
        #
        # result = self.NormProjectBBV(options)
        # util.CheckResult(result, options, 'normalizing and projecting BBV with: ' + self.csv_bin)
        # import pdb;  pdb.set_trace()
        result = self.RunSimpoint(options)
        util.CheckResult(result, options, 'running Simpoint with: ' + self.simpoint_bin)
        result, regions_csv_file = self.GenRegionCSVFile(options)
        util.CheckResult(result, options, 'creating regions CSV file with: ' + self.csv_bin)
        msg.PrintMsg('\nRegions CSV file: ' + os.path.join(options.data_dir, regions_csv_file))

        return result

def main():
    """ Process command line arguments and run the script """

    f = SimPoint()
    result = f.Run()
    return result

# If module is called in stand along mode, then run it.
#
if __name__ == "__main__":
    result = main()
    sys.exit(result)

