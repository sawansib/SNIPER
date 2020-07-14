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
# $Id: kit.py,v 1.45 2014/06/01 16:47:28 tmstall Exp tmstall $

# Print out messages, including error messages
#
#

import sys
import os


# Local modules
#
import config
import msg
import util

class Kit(object):
    """Setup the path and pintools for the PinPlay kit."""

    # First, initalize all the variables in the kit to default values.
    #

    # Path to the top level directory of the kit.
    #
    path = ''

    # What type of a kit is this.
    #
    kit_type = config.PINPLAY

    # Some definitions for the kit.
    #
    default_dir  = 'pinplay'
    pintool      = 'pinplay-driver.so'
    pin          = 'pin'
    type         = 'PinPlay'
    prefix       = ''

    # In case there are any default knobs needed for this pintool.
    #
    default_knobs = ''

    # Path to the Pin binary itself for both architectures.
    #
    pin_dir = os.path.join('extras', 'pinplay', 'bin')

    # Paths to the PinPlay driver for both architectures.
    #
    pinbin_intel64 = os.path.join('intel64', 'bin', 'pinbin')
    pinbin_ia32    = os.path.join('ia32', 'bin', 'pinbin')

    # Paths to the Pin binary itself for both architectures.
    #
    driver_intel64 = os.path.join(pin_dir, 'intel64', 'pinplay-driver.so')
    driver_ia32    = os.path.join(pin_dir, 'ia32', 'pinplay-driver.so')

    # Path to the shell scripts.
    #
    script_path = os.path.join('extras', 'pinplay','PinPoints', 'scripts')

    # Path to simpoint
    #
    simpoint_path = os.path.join('extras', 'pinplay','PinPoints', 'bin')

    # Path to scripts to make alternative region CSV files.
    #
    alt_simpoint_path = os.path.join('source', 'tools','PinPoints', 'bin')

    # Knobs which have the same behavior in the various kits, but a different
    # name in each kit.
    #
    knob_length = '-log:length'
    knob_skip   = '-log:skip'
    knob_regions_epilog = '-log:regions:epilog'
    knob_regions_in     = '-log:regions:in'
    knob_regions_out    = '-log:regions:out'
    knob_regions_prolog = '-log:regions:prolog'
    knob_regions_warmup = '-log:regions:warmup'

    # Is the binary 32-bit or 64-bit?  Only needed for the logging phase.
    #
    binary_type = config.ARCH_INVALID

    def SetBinaryType(self, binary):
        """
        Set the file type: either 32-bit or 64-bit.

        @return No return value
        """

        self.binary_type = util.FileType(binary)

    def ValidDriver(self, path):
        """
        Is this a path to a kit with a valid pinplay driver? 

        @param path Path to kit to be validated

        @return True if valid drivers found, otherwise exit with an error msg
        """

        # See if the 64-bit driver exists
        #
        arch = 'intel64'
        if os.path.isfile(os.path.join(path, self.driver_intel64)):

            # See if the 32-bit driver exists
            #
            arch = 'ia32'
            if os.path.isfile(os.path.join(path, self.driver_ia32)):
                return True

        # There is a valid 'pinbin' binary, or this method wouldn't get called, but
        # there isn't a valid pinplay-driver.
        # 
        msg.PrintMsg('ERROR: The required PinTool \'' + self.pintool + '\' for arch \'' + arch + '\' was not found.')
        msg.PrintMsg('Perhaps the PinPlay kit installation was incomplete. Check to make sure\n' \
            'there weren\'t any errors during the install.') 
        sys.exit(1)

    def ValidKit(self, path):
        """
        Is this a path to a valid kit?

        A valid kit must contain both the binary 'pinbin' and the
        PinPlay driver 'pinplay-driver.so' for both intel64 and ia32.

        @param path Path to kit to be validated

        @return False if kit not valid, else the return value from self.ValidDriver()
        """

        if os.path.isdir(path):

            # See if the 64-bit pinbin binary exists
            #
            if os.path.isfile(os.path.join(path, self.pinbin_intel64)):

                # See if the 32-bit pinbin binary exists
                #
                if os.path.isfile(os.path.join(path, self.pinbin_ia32)):
                    return self.ValidDriver(path)
        return False

    def GetDefaultDir(self):
        """
        Look for a PinPlay kit in several locations, including 'pinplayhome' if
        it's defined.

        @return Path to PinPlay kit
        """

        # Get path to the default version of the kit in users
        # home directory.
        #
        # import pdb;  pdb.set_trace()
        home = os.path.expanduser("~")
        path = os.path.join(home, self.default_dir)

        # If default dir not found in home directory, then try the default
        # in the current directory.
        #
        if not os.path.exists(path):
            path = os.path.join(os.getcwd(), self.default_dir)

        # If the path is set in the tracing configuration file, then override the default
        # value and use this instead.
        #
        # import pdb;  pdb.set_trace()
        if config.pinplayhome:
            if config.pinplayhome[0] == os.sep:
                # Absolute path name, use as is.
                #
                path = config.pinplayhome
            else:
                # Else assume it's a directory in the users home directory.
                #
                path = os.path.join(home, config.pinplayhome)

        return path

    def InitKit(self):
        """
        Get the path to a valid kit, the appropriate tool name and add several paths
        to the environment variable PATH required to find script/utilities.

        @return No return value
        """

        # import pdb;  pdb.set_trace()
        self.path = self.GetDefaultDir()

        # Check to see if it's a valid kit. If not, exit with an error.
        #
        if not self.ValidKit(self.path):
            msg.PrintMsg('ERROR: Path to the ' + self.type + ' kit was not found.')
            msg.PrintMsg('Default kit location is: ' + \
                os.path.realpath(os.path.join(os.path.expanduser("~"), self.default_dir)))
            sys.exit(1)

        # Add several directories in the PinPlay kit to the environment variable PATH.
        #
        os.environ["PATH"] += os.pathsep + os.path.join(self.path, self.script_path)
        os.environ["PATH"] += os.pathsep + os.path.join(self.path, self.simpoint_path)
        os.environ["PATH"] += os.pathsep + os.path.join(self.path, self.alt_simpoint_path)

    def __init__(self):
        """
        Method called when object is instantiated to initalize object.

        @return No return value
        """

        self.InitKit()

    def GetPinTool(self):
        """
        Get the path to the pintool for the required architecture.

        This version must figure out the correct architecture for the pintool
        without looking at any pinballs. Used by the logger.

        @return Explicit path to the pintool for this kit
        """

        pintool_path = self.path
        pintool_path = os.path.join(self.path, self.pin_dir)
        if self.binary_type == config.ARCH_INTEL64:
            pintool_path = os.path.join(pintool_path, 'intel64', self.pintool)
        elif self.binary_type == config.ARCH_IA32:
            pintool_path = os.path.join(pintool_path, 'ia32', self.pintool)
        else:
            msg.PrintAndExit('Could not identify the architecture of the binary during logging.')

        return pintool_path

    def GetPinToolFile(self, basename):
        """
        Get the path to the pintool for the required architecture.

        This version figures out the correct architecture for the pintool by
        looking at the pinballs. Used by the replayer.

        @return Path to the pintool for this kit
        """

        # Get the explicit path to the correct nullapp.
        #
        # import pdb;  pdb.set_trace()
        pintool_path = self.path
        pintool_path = os.path.join(self.path, self.pin_dir)
        arch = util.FindArchitecture(basename)
        if arch == config.ARCH_IA32:
                pintool_path = os.path.join(pintool_path, 'ia32', self.pintool)
        elif arch == config.ARCH_INTEL64:
                pintool_path = os.path.join(pintool_path, 'intel64', self.pintool)
        else:
                msg.PrintAndExit('Could not identify the architecture of a pinball:\n'
                    '   ' + basename)

        return pintool_path

    def GetPinToolKnob(self, pinball=''):
        """
        Get the knob required to add the pintool for this kit to the Pin command line.

        Some kits don't required a pintool knob.  If that the case, just return an empty string.
        Pin based kits require a pintool knob, so return it.

        @return String, including '-t', which defines explict path to pintool
        """

        # If there is a pinball name, assume in a phase to replay a pinball.  Otherwise
        # in the logging phase.
        #
        if pinball != '':
            return ' -t ' + self.GetPinToolFile(pinball)
        else:
            return ' -t ' + self.GetPinTool()

    def GetNullapp(self, basename):
        """
        Get the path to the nullapp for the required architecture.

        @return Explicit path to nullapp
        """

        # Get the explicit path to the correct nullapp.
        #
        nullapp_path = self.path
        nullapp_path = os.path.join(self.path, self.pin_dir)
        arch = util.FindArchitecture(basename)
        if arch == config.ARCH_IA32:
                nullapp_path = os.path.join(nullapp_path, 'ia32', 'nullapp')
        elif arch == config.ARCH_INTEL64:
                nullapp_path = os.path.join(nullapp_path, 'intel64', 'nullapp')
        else:
                msg.PrintAndExit('Could not identify the architecture of the pinballs')

        return nullapp_path

