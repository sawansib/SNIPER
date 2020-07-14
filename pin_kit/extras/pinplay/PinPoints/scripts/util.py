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
# $Id: util.py,v 1.86 2014/06/26 15:14:05 tmstall Exp tmstall $
#
# This module contains various utility functions used in the tracing script.


import datetime
import glob
import os
import re
import subprocess
import sys
import time

# Local modules
#
import config
import msg

Config = config.ConfigClass()

#######################################################################
#
# These are global variables because there can only be one copy of these
# variables even when there are multiple instances of Util objects.
#
#######################################################################

# Number of concurrent jobs running.
#
jobs = 0

# The list of PIDs for the running processes.
#
running_pid = []

# The strings which are printed when each process is finished.  The strings in this
# list are in the same order as the processes which are running.
#
end_str = []


def onWindows():
    """ Are we running on Windows? """

    WindowsHost = (os.name == 'nt')
    return WindowsHost

#################################################################
#
# Functions to run a job either in the foreground, or in the background.
# When jobs are run in the background, then need to wait for a given number
# of jobs to complete before starting more jobs.  Don't want to over
# subscribe the cores, only one job/core.
#
#################################################################

def JoinOptionsList(cmd):
    """
    For spawning processes using os.spawnv() to call Python, the options
    between double quotes (") must be put into just one element of the
    list. Turn the 'cmd' string into a list and consolidate all options
    between double quotes into one element.

    Currently not used, but kept in case it might be needed.
    """

    cmd = cmd.split()
    new_cmd = []
    in_quote = False
    quote_elem = ''
    for elem in cmd:
        pos = elem.find('"')
        if pos != -1:
            # Found the char "
            #
            if in_quote:
                # Found 2nd char "
                #
                quote_elem += ' ' + elem + ' '
                new_cmd.append(quote_elem)
                in_quote = False
            else:
                # Found 1st char "
                #
                quote_elem = elem
                in_quote = True
        else:
            # Did not find the char "
            #
            if in_quote:
                # Add to exising quoted element.
                #
                quote_elem += ' ' + elem + ' '
            else:
                # Add to the new cmd list.
                #
                new_cmd.append(elem)

    return new_cmd

def GetJob(options):
    """Wait for a job to complete. Then remove it from the lists."""

    global jobs, running_pid, end_str

    # Decode the tuple 'status' and get the corresponding end string.
    # status is a 3-element tuple containing:
    #   child's PID
    #   exit status info
    #   resource usage info
    #
    status = os.wait3(0)    # Block and wait for a job to complete
    pid = status[0]
    result = status[1] >>  8
    try:
        num = running_pid.index(pid)
        string = end_str[num]          # Get end_str for the PID
    except ValueError:
        msg.PrintMsgPlus('WARNING: util.GetJob() unable to find running PID: %d' % pid)
        string = ''
        result = -1

    # If there is an end string, then print it.
    #
    # import pdb;  pdb.set_trace()
    if string != '':
        msg.PrintMsgPlus('Finished processing: ' + string)
    if hasattr(options, 'verbose') and options.verbose:
        msg.PrintMsg('Concurrent job finished, PID: ' + str(pid))

    # Remove values from the lists & decrement the number of
    # running jobs.
    #
    # import pdb;  pdb.set_trace()
    try:
        running_pid.remove(pid)
    except ValueError:
        pass    # Do nothing. Warning already printed out 
    try:
        end_str.remove(string)
    except ValueError:
        pass
    jobs -= 1

    return result

def WaitJobs(options, wait_all=True):
    """
    Wait for either one or all processes concurrently running to complete based on
    the boolean wait_all.
    """

    global jobs, running_pid

    if hasattr(options, 'verbose') and options.verbose:
        msg.PrintMsgPlus('Waiting for background job(s) to finish: ' + str(jobs))

    if wait_all:

        # While there are still jobs running, wait for all them to complete.
        #
        # import pdb;  pdb.set_trace()
        result = 0
        while jobs > 0:

            # For each job left in the list of running jobs, see if it's finished.
            #
            # import pdb;  pdb.set_trace()
            while running_pid != []:

                # Wait for one of the running processes to finish. Then remove
                # it from the list of running jobs.  If the job ended in an
                # error, print a message and return an error.
                #
                # import pdb;  pdb.set_trace()
                result = GetJob(options)
                if result != 0:
                    msg.PrintMsg('WaitJobs() unexepected error occurred: non-zero exit code')
                    return result

            # Wait a while before checking again for finished jobs.
            #
            time.sleep(1)

        # All jobs should have finished by this point. Check to make sure
        # the number of jobs is indeed 0.
        #
        if jobs > 0:
            msg.PrintAndExit('WaitJobs() unexepected error occurred: number of jobs runing > 0')
    else:

        # Only wait for one job to finish before returning. Remove it from the
        # list of running jobs.  If the job ended in an error, print a message
        # and return an error.
        #
        # import pdb;  pdb.set_trace()
        result = GetJob(options)
        if result != 0:
            msg.PrintMsg('WaitJobs() unexepected error occurred: non-zero exit code')
            return result

    return result

def RunCmd(cmd, options, string, concurrent, **param):
    """
    Execute a command and return the exit code.

    The boolean variable 'concurrent' controls if the job(s) should be run
    in the background.

        If it's false, then just run the job in the foreground.  This
        method will not return until the job is finished.

        If the job is to be run concurrently, check to see if there is an
        unused core on which to run the job.  If there is a free core on
        which to run a job, run it in the background. Return once the job
        is started in the background.

        If a core is not available, then wait until there is a core available
        and then run the job.

    The argument 'param' is a optional paramater. It is a dictionary containing any
    additional arguments required by the called method besides the default arguments.

    @result Non-zero if an error occurs, otherwise 0
    """

    global jobs, running_pid, end_str

    # If just listing the command or debugging, then print it, but
    # don't execute it.
    #
    result = 0
    if options.list or options.debug:
        msg.PrintMsg(''.join(cmd))
    else:
	# If user specific num_cores, use it.  Else use the
	# number of cores in the system.
	#
	# import pdb;  pdb.set_trace()
	if config.num_cores > 0:
            max_cores = config.num_cores
	else:
            max_cores = NumCores()

        # If the user has specified to only use one core (or there really is
        # only one core) then run the job serially.
        #
        # import pdb;  pdb.set_trace()
        if concurrent and max_cores > 1:
            # If running concurrently, either run the job or wait
            # until it can be run.
            #
            if jobs >= max_cores:
                if hasattr(options, 'verbose') and options.verbose:
                    msg.PrintMsg('Calling WaitJobs() from RunCmd()')
                result = WaitJobs(options, wait_all=False)

            # There is a free core, so start the current job and add it to
            # the list 'running_pid'.  Also add the string to list 'end_str'.
            #
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsgPlus('Running job in background')
            msg.PrintMsgPlus('Processing: ' + string)
            jobs += 1
            end_str.append(string)

            # Do different things on Windows and Linux.
            #
            if onWindows():
                # Use os.spawnv() to run python to execute the script.
                #
                # First, must turn the string cmd into a list, consolidating
                # all options between double quotes into one element in the
                # list.  Then prepend the string 'python' to the list as this
                # needs to be the first string passed to os.spawnv().
                #
                # import pdb;  pdb.set_trace()
                tmp = JoinOptionsList(cmd)
                cmd_list = ['python'] + tmp
                if hasattr(options, 'verbose') and options.verbose:
                    msg.PrintMsgNoCR('Starting concurrent job: ')
                pid = os.spawnv(os.P_NOWAIT, sys.executable, cmd_list)
                if hasattr(options, 'verbose') and options.verbose:
                    msg.PrintMsg('Job PID: %d' % pid)
                running_pid.append(pid)
            else:
                # Add time to the command string.  os.spawnvp() uses bash to run
                # the command 'time' which then executes the command.  It's assumed
                # that all Linux machines have bash.
                #
                # import pdb;  pdb.set_trace()
                cmd_str = ''.join(cmd)
                cmd = 'time ' + cmd
                cmd_list = ['bash', '-c', cmd]
                if hasattr(options, 'verbose') and options.verbose:
                    msg.PrintMsgNoCR('Starting concurrent job: ')
                msg.PrintMsg(cmd_str)
                pid = os.spawnvp(os.P_NOWAIT, 'bash', cmd_list)
                if hasattr(options, 'verbose') and options.verbose:
                    msg.PrintMsg('Job PID: %d' % pid)
                running_pid.append(pid)
        else:

            # Run the process in the foreground.  The method communicate()
            # waits until the process completes.
            #
            # import pdb;  pdb.set_trace()
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsgNoCR('Starting serial job: ')
            msg.PrintMsg(''.join(cmd))
            p = subprocess.Popen(cmd, shell=True)
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsg('Job PID: %d' % p.pid)
            p.communicate()
            if string != '':
                msg.PrintMsgDate(string)
            result = p.returncode
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsg('Serial job finished, PID: %d ' % p.pid)

    return result

#################################################################
#
# Functions used to execute a given method on all pinballs in a set of
# directories.  These directories all contain a the same string.
#
#################################################################

def GetAllIcount(dirname, file_name):
    """
    Get the instruction count for all threads in a pinball.

    Use the result file from the pinball to get 'inscount'.

    Return: list of icounts for all threads, 'None' if an error is detected
    """

    # If the file name contains the extension '.address', then remove it.
    #
    file_name = ChangeExtension(file_name, '.address', '')

    # Get the result file(s) for the pinball and the icount for each thread.
    #
    # import pdb ; pdb.set_trace()
    all_icount = []
    files = glob.glob(os.path.join(dirname, file_name + '*' + '.result'))
    for pfile in files:
        field = FindResultString(pfile, 'inscount:')
        icount = field[0]
        pid = field[1]
        tid = field[2]
        if icount:
            all_icount.append(int(icount))
        else:
            # The icount was not found.
            #
            msg.PrintMsg('\nERROR: util.GetAllIcount(), string \'inscount\' not found, possible corruption in pinball:\n' + '   ' + pfile)
            all_icount = None
            break

    return all_icount

def GetMaxIcount(dirname, file_name):
    """
    Get the maximum instruction count for a pinball.

    Use the result file from the pinball to get 'inscount'.  For multi-threaded
    pinballs, get the icount for the thread with the most instructions.

    Return: pinball instruction count, or 0 if an error occurs
    """

    # If the file name contains the extension '.address', then remove it.
    #
    file_name = ChangeExtension(file_name, '.address', '')

    # Get the result file(s) for the pinball and find the max icount.
    #
    # import pdb ; pdb.set_trace()
    max_icount = 0
    files = glob.glob(os.path.join(dirname, file_name + '*' + '.result'))
    for pfile in files:
        field = FindResultString(pfile, 'inscount:')
        icount = field[0]
        pid = field[1]
        tid = field[2]
        if icount:
            icount = int(icount)
        else:
            # The icount was not found.
            #
            msg.PrintMsg('\nERROR: util.GetMaxIcount(), string \'inscount\' not found, possible corruption in pinball:\n' + '   ' + pfile)
            max_icount = 0
            break
        if icount > max_icount:
            max_icount = icount

    return max_icount

def GetMinIcount(dirname, file_name):
    """
    Get the minimum instruction count for a pinball.

    Use the result file from the pinball to get 'inscount'.  For multi-threaded
    pinballs, get the icount for the thread with the least number of instructions.

    Return: pinball instruction count, or 0 if an error occurs
    """

    # If the file name contains the extension '.address', then remove it.
    #
    file_name = ChangeExtension(file_name, '.address', '')

    # Get the result file(s) for the pinball and find the minimum icount.
    #
    # import pdb ; pdb.set_trace()
    min_icount = sys.maxint
    files = glob.glob(os.path.join(dirname, file_name + '*' + '.result'))
    for pfile in files:
        field = FindResultString(pfile, 'inscount:')
        icount = field[0]
        pid = field[1]
        tid = field[2]
        if icount:
            icount = int(icount)
        else:
            # The icount was not found.
            #
            msg.PrintMsg('\nERROR: util.GetMinIcount(), string \'inscount\' not found, possible corruption in pinball:\n' + '   ' + pfile)
            min_icount = 0
            break
        if icount < min_icount:
            min_icount = icount

    # Check to make sure we really found an icount.  If not, this is
    # an error.
    #
    if min_icount == sys.maxint:
        min_icount = 0

    return min_icount

# Return code because the callback for os.path.walk() doesn't handle return values.
#
_util_result = 0

def walk_callback(param, dirname, fnames):
    """
    Callback used when walking the files in the directory 'dirname' to
    execute a method on each pinball.  Use the '.adress' file for each
    pinball to identify the pinball.

    'fnames' is the list of file names in the directory.

    The method to be run and the options object are in passed as members of
    the list 'param'.

    If the option 'replay_filter' is present, then skip any files which match
    this string, do not run the method on these files.
    """

    # Get items from the param dictionary.
    #
    # import pdb ; pdb.set_trace()
    try:
        options = param['options']
    except KeyError:
        msg.PrintAndExit('method util.walk_callback() failed to get param \'options\'')
    try:
        method = param['method']
    except KeyError:
        msg.PrintAndExit('method util.walk_callback() failed to get param \'method\'')

    # Need to use the global _util_result because the return values from the callback
    # are not passed back to the calling function.
    #
    global _util_result
    _util_result  = 0

    # Get just the address files.
    #
    file_list = []
    for addr_file in fnames:
        pos = addr_file.find(".address")
        if pos != -1:
            file_list.append(addr_file)

    # Sort the pinballs from high to low according to the icount given in
    # the pinball result file.  Use the icount as a 'decoration' to sort the
    # file names.
    #
    decor = []
    for f in file_list:
        tmp = (GetMaxIcount(dirname, f), f)
        if tmp[0] == 0:
            _util_result = -1
            return

        decor.append(tmp)
    decor.sort(reverse = True)
    sorted_list = []
    for tmp in decor:
        # Need to remove file extension '.address' before the file name
        # is put into the list.
        #
        sorted_list.append(ChangeExtension(tmp[1], '.address', ''))

    # import pdb ; pdb.set_trace()
    for basename_file in sorted_list:

        # Error check the results of the previous call to method().
        # If it had an error, then exit with the result code.
        #
        if _util_result != 0:
            return

        # See if this should be filtered out.
        #
        found = True
        if hasattr(options, 'replay_filter'):
            if options.replay_filter != "":
                if (basename_file.find(options.replay_filter) != -1):
                    found = False
                    if not options.list:
                        msg.PrintMsg('Filtering on string: ' + options.replay_filter + '\n' \
                                  'Ignoring pinball:    ' + os.path.join(dirname, basename_file))

        # Execute the method on the pinball.
        #
        if found:
            # import pdb ; pdb.set_trace()
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsg('calling method: ' + str(method))
            _util_result = method(param, dirname, basename_file)

def RunAllDir(dir_string, method, no_glob, param):
    """
    Run 'method' on the pinballs in all directories which start with the string 'dir_string'.

    Argument 'param' contains a dictionary of objects which are used by the Method 'method'.
    It must at least contain an 'options' object.

    If the parameter 'no_glob' is True, then do not expand the directory name to include
    all directories.  Only run on the directory 'dir_string'.

    Uses the os.path.walk() method to run the method on all pinballs in each directory
    for which this method is called.
    """

    # import pdb ; pdb.set_trace()
    if dir_string != '':

        # Generate a list of directories.
        #
        dir_list = []
        if no_glob:
            # Don't expand the directory name.
            #
            dir_list.append(dir_string)
        else:
            # Find each directory which starts with 'dir_string'.
            #
            for path in os.listdir(os.getcwd()):
                if os.path.isdir(path) and path.startswith(dir_string):
                    dir_list.append(path)

        # Get 'options' from  the dictionary 'param' and add 'method'.
        #
        # import pdb ; pdb.set_trace()
        try:
            options = param['options']
        except KeyError:
            msg.PrintAndExit('method util.walk_callback() failed to get param \'options\'')
        param['method'] = method

        # Walk each directory in the list.
        #
        for path in dir_list:
            # import pdb ; pdb.set_trace()
            if config.debug and hasattr(options, 'list') and not options.list:
                msg.PrintMsg('Processing pinballs in directory \'' + path + \
                                      '\' using method: ' + str(method))
            # import pdb ; pdb.set_trace()
            if hasattr(options, 'verbose') and options.verbose:
                msg.PrintMsg('Calling os.path.walk() with path: %s' % path)
            os.path.walk(path, walk_callback, param)

            # Need to use the global _util_result because the return values from the callback
            # are not passed back to the calling function.
            #
            if _util_result != 0:
                return _util_result
    else:
        msg.PrintAndExit('method util.RunAllDir() called with empty string \'dir_string\'')

    # If an error occurs, function already returned with the error code.
    #
    return 0

#################################################################
#
# Functions to search for a string in all the *.result files in a set
# of directories.
#
#################################################################

def FindResultString(filename, search_string, add_tid = False):
    """
    Get the value associated with 'search_string' from one result file.  If the boolean 'add_tid'
    is true, then add a TID to the file name before looking for the result file.

    Example files input names:
      whole_program.milc-test/milc.2.milc-test_68183.0.result
      milc.2.milc-test_68184.pp/milc.2.milc-test_68184_t0r7_warmup5000000_prolog346789_region2000017_epilog567890_007_0-06573.0.result

    The result files contain a key, value pair. For instance,
        inscount: 8002788
        focus_thread: 2

    Return: A list containing three items: [value, pid, tid].
    If an item is not found, then 'None' is returned as the value.
    """

    # See if the file name contains PID/TID information according
    # to the default naming convention for WP pinballs.
    #
    pid = None
    tid = None
    pattern = '_[0-9]*\.[0-9]*\.result'
    # import pdb ; pdb.set_trace()
    if re.search(pattern, filename):
        # Get the PID/TID info.
        #
        string = re.findall(pattern, filename)
        string = string[0][1:]               # Get pattern as a string & remove leading '_'
        field = string.split('.')
        pid = field[0]
        tid = field[1]

    # If the file name doesn't have the file extension '.result', then add it to the name.
    # Also add TID if this is indicated.
    #
    # import pdb ; pdb.set_trace()
    if filename.find('result') == -1:
        if add_tid:
            # Sort so the TID 0 result file will be first, if there are more than one.
            #
            names = sorted(glob.glob(filename + '*.result'))
            if names != []:
                filename = names[0]
        else:
            filename += '.result'

    # If 'search_string' does not have a trailing ':', then add it. We are looking for the
    # key 'search_string', not just this string.
    #
    if search_string.find(':') == -1:
        search_string += ':'

    # Look for string 'search_string' and add the value of this key to the list 'result'.
    #
    # import pdb ; pdb.set_trace()
    val = None
    if os.path.isfile(filename):
        try:
            f = open(filename, 'r')
        except:
            msg.PrintAndExit('method util.FindResultString(), can\'t open file: ' + filename)

        for line in f.readlines():
            if line.find(search_string) != -1:
                val = line.split()[1]

    return [val, pid, tid]

def ProcessAllFiles(options, dir_name, search_string, file_string, ignore_string, method):
    """
    Execute 'method' on all files in directory 'dir_name' which contain the
    string 'file_string', but not the string 'ignore_string'.

    Returns a list of return values from 'method'.  One for each file which matches the
    search criteria.
    """

    if (config.verbose):
         msg.PrintMsg('Processing all files in ' + dir_name + ' which contains '\
                'the string \'' + file_string + '\' but not the string \'' + \
                ignore_string + '\'')

    # Look for all files in directory 'dir_name' which contain string
    # 'file_string' but does not contain 'ignore_string'.
    #
    result = 0
    files = []
    for path in glob.glob(os.path.join(dir_name, '*' + file_string + '*')):
        if path.find(ignore_string) != -1:
            continue                # Don't want this file
        else:
            files.append(path)

    # Sort the list of file names.
    #
    files.sort()

    # Run the method on each file which matched the requirements.
    #
    result = []
    for f in files:
        if (config.verbose):
             msg.PrintMsg('Processing file ' + f)
        # import pdb ; pdb.set_trace()
        result.append(method(f, search_string))

    return result

def PrintInstrCount(dirname, options):
    """Print out the instruction counts for all whole program pinballs."""

    # Setup locale so we can print integers with commas.
    #
    import locale
    locale.setlocale(locale.LC_ALL, "")

    # Get a list which contains a set of lists. Each member of the list contains:
    #     instruction count, PID and TID
    #
    # import pdb;  pdb.set_trace()
    p_list = ProcessAllFiles(options, dirname, 'inscount:', 'result', 'result_play', \
                  FindResultString)

    # Print out the instruction counts.
    #
    if not options.list:
        old_pid = -1
        msg.PrintMsg('Instruction count')
        for field in p_list:
            icount = field[0]
            pid = field[1]
            tid = field[2]
            if icount:
                icount = int(icount)
            else:
                # The icount was not found.
                #
                msg.PrintMsg('\nWARNING: In PrintInstrCount() string ' \
                    '\'inscount\' not found.  Possible corruption in a pinball.')
                icount = 0
                continue
            # Format output based on pid and tid
            #
            if pid:
                if pid != old_pid:
                    msg.PrintMsg(' Process: ' + pid)
                    old_pid = pid
            if tid:
                msg.PrintMsg('   TID: ' + tid + ' ' + locale.format('%16d', int(icount), True))
            else:
                # Otherwise, just print the icount
                #
                msg.PrintMsg(locale.format('%16d', int(icount), True))


def GetNumThreads(options):
    """
    Get the number of threads for result files in the tracing instance WP pinball directory.

    If there are pinballs with different number of threads, return the maximum number of
    threads found.
    """

    # Get a list which contains a set of lists. Each member of the list contains:
    #     instruction count, PID and TID
    #
    p_list = ProcessAllFiles(options, GetWPDir(), 'num_static_threads:', 'result', 'result_play', \
                  FindResultString)

    # import pdb ; pdb.set_trace()
    max_num_thread = -1
    for field in p_list:
        num_thread = field[0]
        if num_thread:
            num_thread = int(num_thread)
            if num_thread > max_num_thread:
                max_num_thread = num_thread

    return max_num_thread

def GetFocusThreadWP(options):
    """
    Get the focus thread for result files in the tracing instance WP pinball directory.

    Return -1 if no focus thread found.
    """

    # Get a list which contains a set of lists. Each member of the list contains:
    #     instruction count, PID and TID
    #
    p_list = ProcessAllFiles(options, GetWPDir(), 'focus_thread:', 'result', 'result_play', \
                  FindResultString)

    # If there is a focus thread then it should be the same for all TIDs.
    #
    # import pdb ; pdb.set_trace()
    ft = -1
    for field in p_list:
        ft = field[0]
        if ft:
            ft = int(ft)

    return ft

def GetFocusThreadPB(filename):
    """
    Get the focus thread for a pinball.

    Return -1 if no focus thread found.
    """

    field = FindResultString(filename, 'focus_thread:')
    ft = field[0]
    if ft:
        ft = int(ft)
    else:
        ft = -1

    return ft

#################################################################
#
# Functions which add options to a PinTool command line 
#
#################################################################

def AddCfgFile( options):
    """
    If this script was called with at least one configuration file, then
    add the configuration file(s) to the cmd string.

    Returns: a string containing the knob
    """

    string = ''
    if hasattr(options, 'config_file'):
        if options.config_file != '':
            for c_file in options.config_file:
                string += ' --cfg '
                string += c_file + ' '

    return string

def AddCfgFileList(options):
    """
    If this script was called with at least one configuration file, then
    add the configuration file(s) to the cmd list.

    Returns: a string containing the knob
    """

    string = ''
    if hasattr(options, 'config_file'):
        if options.config_file != '':
            tmp = ' --cfg '
            for c_file in options.config_file:
                tmp += c_file + ' '
            string += [tmp]

    return string

def AddCompressed(options):
    """
    If the option 'compressed' is defined, add it to the cmd string with the
    type of compression.

    Returns: a string containing the knob
    """

    string = ''
    if hasattr(options, 'compressed'):
        comp = options.compressed
        if comp == "none" or comp == "bzip2" or comp == "gzip":
            string = ' -log:compressed ' + comp + ' '
        else:
            msg.PrintHelpAndExit('Invalid compression: \'' + comp + '\' passed to -c or --compressed')

    return string

def AddGlobalFile(gfile, options):
    """
    Add a global file to the cmd string.

    Returns: a string containing the knob
    """

    string = ''
    if gfile != '':
        string = '  --global_file ' + gfile

    return string

def AddMt(options, file_name=None):
    """
    If necessary, add the knob for replaying multi-threaded pinballs.

    Use either the option 'mode' or figure it out from the type of the
    (optional) pinball.  If a pinball is given, it over rides the user option.

    Explicitly specify the knob '-log:mt 0' if mode is ST_MODE or pinball is
    single threaded.  Do this because the default for PinPlay is '-log:mt ON'.
    Logging with this knob enabled for PinPlay in single threaded pinballs
    significantly shows down the logging process and is not necessary.
    Explicitly specifying this knob for SDE is fine.

    Returns: a string containing the knob
    """

    mt = ' -log:mt 1'
    no_mt = ' -log:mt 0'
    string = ''
    if hasattr(options, 'mode'):

        # If the option 'mode' is either MT_MODE or MPI_MT_MODE, the user has
        # indicated it a multi-threaded run.  Add a multi-threaded flag.
        #
        if options.mode == config.MT_MODE or options.mode == config.MPI_MT_MODE:
            string = mt

        # Need explicit knob to disable multi-thread processing
        #
        if options.mode == config.ST_MODE:
            string = no_mt

        # If the WP pinballs have been relogged with a focus thread, then
        # they are per thread.  In addition, any pinballs generated from
        # relogging WP pinballs with a focus thread will also be per
        # thread.
        #
        if hasattr(options, 'use_relog_focus') and options.use_relog_focus:
            string = no_mt

    if file_name != None:

        # Called with a pinball.  Figure out if it'a cooperative pinball and add
        # the knob if it is.
        #
        if IsCoopPinball(file_name):
            string = mt
        else:
            # Need explicit knob to disable multi-thread processing
            #
            string = no_mt

    return string

def AddNoGlob(options):
    """
    If the option 'no_glob' is defined, add it to the cmd string.

    Returns: a string containing the knob
    """

    string = ''
    if hasattr(options, 'no_glob') and options.no_glob:
        string = ' --no_glob'

    return string

#################################################################
#
# Helper Functions
#
#################################################################

def Delete(options, string):
    """Delete the directory/file given by 'string'."""

    # import pdb ; pdb.set_trace()
    msg.PrintMsgPlus('Deleting: ' + string)
    cmd = 'rm -rf ' + string
    if not options.debug:
        p = subprocess.Popen(cmd, shell=True)
        p.wait()
        time.sleep(0.1)    # Wait for slow NFS file systems to catch up...
    else:
        msg.PrintMsg('       ' + cmd)
        msg.PrintMsg('       Debugging so files/dirs were not deleted')

def NumCores():
    """Get the number of cores in the system."""

    # linux code
    #
    if hasattr(os, "sysconf"):
        if os.sysconf_names.has_key("SC_NPROCESSORS_ONLN"):
            num_cpus = os.sysconf("SC_NPROCESSORS_ONLN")
    if isinstance(num_cpus, int) and num_cpus > 0:
        return num_cpus
    else:
        # code for OS X
        #
        return int(os.popen2("sysctl -n hw.ncpu")[1].read())

    # Windows specific code
    #
    if os.environ.has_key("NUMBER_OF_PROCESSORS"):
         num_cpus = int(os.environ["NUMBER_OF_PROCESSORS"]);
         if num_cpus > 0:
             return num_cpus

    # If can't find the number of cores, return 1.
    #
    return 1

def Which(program):
    """See if a program is in the user's path and if it's executable."""

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def FileType(binary):
    """Determine if a binary is 32 or 64-bit."""

    import platform

    ftype = config.ARCH_INVALID
    info = platform.architecture(binary)
    for i in info:
        if i.find('64bit') != -1:
            ftype = config.ARCH_INTEL64
            break
        if i.find('32bit') != -1:
            ftype = config.ARCH_IA32
            break

    return ftype

def FindArchitecture(basename):
    """Find out if a pinball is from a 32 or 64-bit binary."""

    if os.path.exists(basename+".result.0"):
        filename = basename + ".result.0"
    elif os.path.exists(basename+".0.result"):
        filename = basename + ".0.result"
    elif os.path.exists(basename+".result"):
        filename = basename + ".result"
    else:
        msg.PrintAndExit('Can\'t find result.0 or 0.result for basename: ' + \
            basename)

    arch = config.ARCH_INVALID
    try:
        result_file = open(filename, "r")
    except:
        msg.PrintAndExit('Can\'t open result file: ' + filename)

    line = result_file.readline()
    while line:
            if line.find("arch: x86_32") != -1:
                    arch = config.ARCH_IA32
                    break
            elif line.find("arch: x86_64") != -1:
                    arch = config.ARCH_INTEL64
                    break
            line = result_file.readline()
    result_file.close()

    return arch

def RoundupPow2(a):
    """Round an integer up to the nearest power of 2."""

    if type(a)!=type(0): raise RuntimeError, "Only works for ints!"
    if a <=0: raise RuntimeError, "Oops, doesn't handle negative values"

    next_one_up=1
    while(next_one_up < a):
        next_one_up = next_one_up << 1
    return next_one_up

def CleanupTraceEnd(options=None):
    """Do any cleanup required at the end of the script."""

    # Clean up any global data files which still exist.
    #
    gv = config.GlobalVar()
    gv.RmGlobalFiles(options)

def PrintTraceEnd(options=None):
    """Print a string at the end of the script."""

    # Print the list of options doesn't have the list attribute, or list is True.
    #
    # import pdb ; pdb.set_trace()
    if not hasattr(options, 'list') or (hasattr(options, 'list') and not options.list):
        pr_str = '***  TRACING: END' + '  ***    ' + time.strftime('%B %d, %Y %H:%M:%S')
        msg.PrintMsg('')
        msg.PrintMsg(pr_str)

# Global which contains the timestamp when a phase starts.
#
phase_start = None

def PhaseBegin(options):
    """Save a timestamp when a phase starts."""

    global phase_start
    phase_start = datetime.datetime.now().replace(microsecond=0)

def PhaseEnd(options):
    """
    Return a string which indictes the delta between the current time
    and the beginning of the phase stored in 'phase_start'.
    """

    global phase_start

    # import pdb ; pdb.set_trace()
    if phase_start != None:
        delta = datetime.datetime.now().replace(microsecond=0) - phase_start
    else:
        delta = None
    phase_start = None

    return delta

def CheckResult(result, options, phase):
    """
    Check the result of running a given phase.  If it fails, print an error msg.

    Also records in a status file if the phase passed or failed and the time
    used to run the current phase.
    """

    # Write the status of the phase to the appropriate file.
    #
    # import pdb ; pdb.set_trace()
    s_file = GetStatusFile()
    try:
        f = open(s_file, 'a+')
    except:
        msg.PrintAndExit('method util.CheckResult(), can\'t open status file: ' + \
            s_file)
    if not options.list and not options.debug:
        if result == 0:
            f.write('Phase: ' + phase.ljust(75) + ': Passed ')
        else:
            f.write('Phase: ' + phase.ljust(75) + ': Failed ')

    # If a start time has been recorded, get the time required to run the
    # current phase.
    #
    if not options.list and not options.debug:
        td = PhaseEnd(options)
        if td != None:
            f.write('%s (%s)\n' % (str(td), (td.microseconds + (td.seconds + \
                td.days * 24 * 3600) * 10**6) / 10**6))
        else:
            f.write('\n')
    f.close()

    # If an error occurred, let the user know, clean up and quit with an error code.
    #
    if result != 0:
        if not options.list and not options.debug:
            # import pdb ; pdb.set_trace()
            msg.PrintMsg("\n**************************************************"
                                     "*********************************************")
            msg.PrintMsg(os.path.basename(sys.argv[0]) + ' ERROR: A problem occurred in phase - ' + phase)

        # Cleanup and exit.
        #
        CleanupTraceEnd(options)
        PrintTraceEnd(options)
        sys.exit(-1)

def PrintModuleVersions():
    """Print out all the Python module versions.  Useful for debugging."""

    # Get all the Python files & sort them.
    #
    # import pdb;  pdb.set_trace()
    py_files = glob.glob('*.py')
    py_files += glob.glob('base/*.py')
    py_files.sort()

    msg.PrintMsg('Python module versions:')
    for p_file in py_files:
        # Get the line with the RCS 'Id:' string.
        #
        cmd = 'grep Id: ' + p_file
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        (stdout, stderr) = p.communicate()

        # Print the file name and version.
        #
        pos = stdout.find('Id:')
        if pos != -1:
            words = stdout.split(' ')
            file_name = words[2].replace(',v','')
            msg.PrintMsg(file_name.ljust(26)  + words[3])
    msg.PrintMsg('')

def MPICmdLine(options):
    """
    Generate the MPI command line.

    All MPI command line options are given here.  Definitions of options:
       -env I_MPI_DEVICE shm               Use shared memory
       -env I_MPI_SPIN_COUNT 2147483647    Spin 2 billion times
       -env I_MPI_PIN_MODE lib             Use MPI library pinning method
       -env I_MPI_PIN_PROCS 3,5,2,4        List of cores to use for pinning
       -env I_MPI_DEBUG 4                  Debug level to print pinning info
    If you change these default values, then also change the values used to
    print the default in the module cmd_options for the option 'mpi_options'.
    """

    # Check to make sure num_proc is defined for MPI apps
    #
    if config.num_proc < 1:
        if options.num_proc > 0:
            config.num_proc = options.num_proc
        else:
            string = "must use the -n option to define a number of processes with MP applications"
            msg.PrintHelpAndExit(string)

    if options.mpi_options == '':
        mpi_cmd  = 'mpirun -n ' + str(config.num_proc)
        mpi_cmd += ' -env I_MPI_DEVICE shm -env I_MPI_SPIN_COUNT 2147483647 -env I_MPI_PIN_MODE lib '
        # mpi_cmd += ' -env I_MPI_PIN_PROCS 3,2,1,0,7,6,5,4,11,10,9,8,15,14,13,12 -env I_MPI_DEBUG 4 '
        mpi_cmd += ' -env I_MPI_PIN_PROCS 3,2,1,0,7,6,5,4,11,10,9,8,15,14,13,12 -env I_MPI_DEBUG 4 '
    else:
        mpi_cmd = 'mpirun ' + options.mpi_options

    return mpi_cmd

def CountFiles(string):
    """Return the number of files in the current directory which contain string 'str'."""

    return len(glob.glob('*' + string + '*'))

#################################################################
#
# Functions to parse region pinball/LIT file names and return the
# fields contained in the file name.
#
#################################################################

# Regular expression patterns used for matching region pinball file names.
# There are three patterns:  user_pattern, pp_pattern and full_pattern
#
# The full_pattern is composed of two parts: user_pattern & pp_pattern
#
#   user_pattern - defined by either:
#       1) The user parameters 'program_name', 'input_name' and the PID
#       2) By the names of the whole program pinballs given by the user
#
#   pp_pattern - generated by the PinPlay tools when creating region pinballs 
#
# Here's an example of a file name generated by using the default naming
# convention of the pinpoints.py script:
#
#   omnetpp.p10000-s10_57015_t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.0.address
#
# Here are examples of the two sub-component patterns for this full name:
#
#   user_pattern
#       omnetpp.p10000-s10_57015
#
#   pp_pattern
#       _t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.
#
# A partial file name only contains a match for 'pp_pattern'.  The initial part of the file name
# has no limits on the format of the string.
#
# Here's an example of a file name which is a 'partial' file name.
#
#   test-abc_one.two_t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.0.address
#
user_pattern = '[a-zA-Z0-9-+%]+\.[a-zA-Z0-9-+%]+_[0-9]+'
pp_pattern = '_t[0-9]+r[0-9]+_warmup[0-9]+_prolog[0-9]+_region[0-9]+_epilog[0-9]+_[0-9]+_[0-1]-[0-9]+'
full_pattern = user_pattern + pp_pattern

# Currently, this is not used, but should probably be added to the algorithm for parsing
# file names...
#
# For backwards compatability, a pattern is given for the older file names:
#
#   old_user_pattern - generated by PinPlay using the three parameters 'program_name', 'num_proc'
#       and 'input_name' instead of just 'program_name' and 'input_name' as in 'user_pattern'.
#
# Here are examples of the two sub-component patterns for this full name:
#   user_pattern
#       omnetpp.2.p10000-s10
#
old_user_pattern = '[a-zA-Z0-9-+%]+\.[0-9]+\.[a-zA-Z0-9-+%]+_[0-9]+'
old_full_pattern = old_user_pattern + pp_pattern

def ParseFileName(file_name):
    """
    Determine the type of file name name, either full or partial.  Then
    call the appropriate function to parse the file name.

    See comments above for definitions of full and partial.

    Returns: a dictionary which contains the fields successfully parsed
    """

    result = {}
    file_name = os.path.basename(file_name)
    # import pdb;  pdb.set_trace()
    if re.search(full_pattern, file_name):
        result = ParseFullFileName(file_name)
    elif re.search(pp_pattern, file_name):
        result = ParsePartialFileName(file_name)
    else:
        msg.PrintAndExit('method util.ParseFileName() encountered a file name\n'
                'which does not meet requirements for parsing a region pinball name:\n   ' + \
                file_name + '\nFile name must conform to the region pinball naming convention.')

    return result

def ParseFullFileName(file_name):

    """
    Parse a region pinball file name where all fields were generated by the
    pinpoints.py script.

    The PinPlay tools encode information about a representative region in the
    file name.  For example, given this file name:

        omnetpp.p10000-s10_57015_t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.0.address

    The following information is contained in the first part of it:
        program name:    omnetpp
        input name:      p10000-s10
        PID:             57015

    The remainder of the file name is parsed by the function
    ParsePartialFileName() which is called by this function.

    Returns: a dictionary which contains the fields successfully parsed from
    the full file name
    """

    # Remove any directories from the name.
    #
    # import pdb;  pdb.set_trace()
    file_name = os.path.basename(file_name)

    # Make sure the file name matches the full file name pattern.
    #
    # import pdb;  pdb.set_trace()
    if not re.search(full_pattern, file_name):
        msg.PrintAndExit('method util.ParseFullFileName() encountered a file name\n'
                'which does not meet requirements for parsing a region pinball name:\n   ' + \
                file_name + '\nFile name must conform to the region pinball naming convention.')

    # Directory containing the fields which were successfull parsed.
    #
    result = {}

    # Define a lambda function to print a standard error msg.
    #
    err_msg = lambda fname, string: msg.PrintAndExit('method util.ParseFullFileName() encountered '
                'an error parsing \'' + string + '\' in \nfile name:  ' + fname)

    # Get the first 'user' part of the file name and parse it.  The example
    # given above produces this list:
    #
    #  ['omnetpp.p10000-s10_57015']
    #
    # import pdb;  pdb.set_trace()
    user_part = re.findall(user_pattern, file_name)
    field = user_part[0].split('.')
    tmp = field[1].split('_')
    result['program_name']  = field[0]  # No error check for this field
    result['input_name']  = tmp[0]      # No error check for this field

    # Old code to get the num_proc.  Curently not used. MUST be updated to use it
    # again here...  Also, code for PID must be modified if/when this code is used.
    #
    # Get the number of processes from the 1st 'user_part' string.  It
    # contains a string like '.X.', where X is num_proc.
    #
    # import pdb;  pdb.set_trace()
    # tmp = re.findall('[0-9]*\.[0-9]+\.', field[1])
    # if len(tmp) > 0:
    #     num_proc = tmp[0].replace('.', '')
    #     try:
    #         num_proc = int(num_proc)
    #     except ValueError:
    #         err_msg(file_name, 'num_proc')
    #     result['num_proc'] = num_proc

    # Get the PID
    #
    try:
        pid = int(tmp[1])
    except ValueError:
        err_msg(file_name, 'pid')
    result['pid'] = pid

    # Get the fields from the PinPlay part of the file name.
    #
    # import pdb;  pdb.set_trace()
    partial_result = ParsePartialFileName(file_name)

    # Return the fields from both parts of the file name.
    #
    return dict(result.items() + partial_result.items())

def ParsePartialFileName(file_name):
    """
    Parse just the portion of a region pinball file name generated by PinPlay.

    The PinPlay tools encode information about a representative region in the file name.
    For example, given this full file name:

        omnetpp.p10000-s10_57015_t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.0.address

    The PinPlay generated portion is:

        _t0r5_warmup1001500_prolog0_region3500003_epilog0_005_0-00970.0.address

    The following information is contained in the first part this string:
        TID:                 0  (t0)
        region number:       5  (r5)

    The next set of information contains the number of instructions in each
    'section' of the region pinball.  The format is a section name, followed by
    the number of instructions in the section.

    The number of instructions in these sections are:
        warmup: 1001500  (warmup1001500)
        prolog:       0  (prolog0) 
        region: 3500003  (region3500003)
        epilog:       0  (epilog0)

    Any of the sections, except for region, may contain 0 instructions.  In this case,
    the section will still exist, but with 0 instructions.

    Finally, there are 2 more pieces of information:
        trace number:     5   (005)
        weight:     0.00970   (0-00970)

    The trace number is the same as the region number.

    This code makes the assumption that the tracing parameters 'program_name' and
    'input_name' do NOT contain any of these chars: '.', '_'.

    Returns: a dictionary which contains the fields successfully parsed
    """

    # Remove any directories from the name.
    #
    # import pdb;  pdb.set_trace()
    file_name = os.path.basename(file_name)

    # Make sure the file name matches the PinPlay pattern.
    #
    # import pdb;  pdb.set_trace()
    if not re.search(pp_pattern, file_name):
        msg.PrintAndExit('method util.ParsePartialFileName() encountered a file name\n'
                'which does not meet requirements for parsing a region pinball name:\n   ' + \
                file_name + '\nFile name must conform to the region pinball naming convention.')

    # Directory containing the fields which were successfull parsed.
    #
    result = {}

    # Define a lambda function to print a standard error msg.
    #
    err_msg = lambda fname, string: msg.PrintAndExit('method util.ParsePartialFileName() encountered '
                'an error parsing \'' + string + '\' in \nfile name:  ' + fname)

    # Get the file extension
    #
    # import pdb;  pdb.set_trace()
    tmp = re.split(pp_pattern, file_name)
    if len(tmp) >= 2:
        file_ext = tmp[1]
        tmp = file_ext.split('.')
        if tmp[0].isdigit():
            file_ext = '.'.join(tmp[1:])     # Remove TID if it exists
        else:
            file_ext = '.'.join(tmp[0:])
        result['file_ext'] = file_ext

    # Get the PinPlay generated part of the file name.
    #
    # import pdb;  pdb.set_trace()
    pp_part = re.findall(pp_pattern, file_name)

    # Divide the pp_part into strings separated by '_' which contain the
    # fields of the file name.  The example given above produces this
    # list:
    #
    #   ['', 't0r5', 'warmup1001500', 'prolog0', 'region3500003', 'epilog0', '005', '0-00970.']
    #
    field = pp_part[0].split('_')

    # 2nd field has TID and region number.
    #
    # import pdb;  pdb.set_trace()
    tmp = field[1][1:]                     # Remove the leading 't'
    pos = tmp.find('r')
    try:
        tid = int(tmp[:pos])
    except ValueError:
        err_msg(file_name, 'tid')
    result['tid'] = tid
    region_num = tmp[pos:]
    try:
        region_num = int(region_num[1:])   # Remove the leading 'r'
    except ValueError:
        err_msg(file_name, 'region_num')
    result['region_num'] = region_num

    # Now get the number of instructions in the various regions. Each one is
    # in a separate field.
    #
    try:
        warmup = int(field[2].replace('warmup', ''))
    except ValueError:
        err_msg(file_name, 'warmup')
    result['warmup'] = warmup
    try:
        prolog = int(field[3].replace('prolog', ''))
    except ValueError:
        err_msg(file_name, 'prolog')
    result['prolog'] = prolog
    try:
        region = int(field[4].replace('region', ''))
    except ValueError:
        err_msg(file_name, 'region')
    result['region'] = region
    try:
        epilog = int(field[5].replace('epilog', ''))
    except ValueError:
        err_msg(file_name, 'epilog')
    result['epilog'] = epilog
    try:
        trace_num = int(field[6])
    except ValueError:
        err_msg(file_name, 'trace_num')
    result['trace_num'] = trace_num

    # Final field contains the weight with '-' as the decimal point.
    # NOTE: string '1-00000' == 1.0
    #
    # import pdb ; pdb.set_trace()
    if field[7].find('1-0') != -1:
        weight = 1.0
    else:
        pos = field[7].find('.')
        tmp = field[7][:pos]        # Remove trailing '.' from the field
        try:
            weight = float(tmp.replace('-', '.'))
        except ValueError:
            err_msg(file_name, 'weight')
    result['weight'] = weight

    return result

def GetRegionInfo(file_name):
    """
    Get information about a region pinball, including:
        1) Total icount
        2) Icount for each of the 4 possible regions
        3) TID
        4) Region number

    Use the actual icount from the pinball for the number of instruction in ROI
    instead of the number given in the file name. The info in the file name is
    not the exact count.

    @return List containing: total_icount, warmup_icount, prolog_icount, region_icoutn, epilog_icount, TID, region
    """

    # Define a lambda function to print an error message. This time include file name.
    #
    err_msg = lambda string, fname: msg.PrintMsg('ERROR: method sde_phases.GenLitFiles() failed to '
                'get field: ' + string + '\nfrom file: ' + file_name)

    # Get the fields from parsing the pinball file name.  'fields' is a dictionary
    # with the fields in the file name.
    #
    # import pdb;  pdb.set_trace()
    fields = ParseFileName(file_name)
    try:
        epilog = fields['epilog']
    except KeyError:
        err_msg('epilog', file_name)
        return -1
    try:
        prolog = fields['prolog']
    except KeyError:
        err_msg('prolog', file_name)
        return -1
    try:
        region = fields['region']
    except KeyError:
        err_msg('region', file_name)
        return -1
    try:
        tid = fields['tid']
    except KeyError:
        err_msg('tid', file_name)
        return -1
    try:
        warmup = fields['warmup']
    except KeyError:
        err_msg('warmup', file_name)
        return -1

    # Calculate some metrics for the pinball.  Use the number of instructions from the
    # result file (icount) instead of using the count from the file name.  The icount
    # is the actual number of instructions in the region.  The number from the file name
    # is only an approximate number of instructions.
    #
    # import pdb;  pdb.set_trace()
    field = FindResultString(file_name + '.result', 'inscount')
    icount = field[0]
    if icount:
        icount = int(icount)
    else:
        icount = 0

    # Calculate some region information.
    #
    lit_len = icount - warmup
    calc_region = icount - warmup - prolog - epilog

    return (icount, warmup, prolog, calc_region, epilog, tid, region)

def IsCoopPinball(file_name):
    """
    Is this a cooperative pinball (i.e. has > 1 thread)?

    Count the number of result files for the pinball.  If there are more than
    one, then it's a cooperative pinball.

    This will probably have to be changed when PinPlay implements the
    capability to generate one 'per thread' pinball for each thread in
    cooperative whole program pinballs.  It is currently unknown how this
    enhancement will be implemented.
    """

    return len(glob.glob(file_name + '*.result')) > 1

def IsInt(s):
    """Is a string an integer number?"""
    try:
        int(s)
        return True
    except ValueError:
        return False

def IsFloat(s):
    """Is a string an floating point number?"""
    try:
        float(s)
        return True
    except ValueError:
        return False

def OpenCompressFile(sim_file):
    """
    Open a simulator file and make sure it contains at least some data.

    The method will open either a file compressed with gzip, bzip2 or a non-compressed
    file.

    Return: a file pointer to the open file or 'None' if open fails
    """

    # Dictionary of 'magic' strings which define the first several char of
    # different type of compressed files.
    #
    magic_dict = {
        "\x1f\x8b\x08": "gz",
        "\x42\x5a\x68": "bz2",
        "\x50\x4b\x03\x04": "zip"
        }
    max_len = max(len(x) for x in magic_dict)

    def file_type(filename):
        """Return the type of file compression used for a file."""

        with open(filename) as f:
            file_start = f.read(max_len)
        for magic, filetype in magic_dict.items():
            if file_start.startswith(magic):
                return filetype
        return "no match"

    # Make sure the Simultor data file exists and has at least some data.
    #
    if not os.path.isfile(sim_file):
        msg.PrintMsg('Can\'t find data file: ' + sim_file)
        return None
    if os.path.getsize(sim_file) < 4:
        msg.PrintMsg('No real data in data file: ' + sim_file)
        return None

    # See if the file is compressed with gzip or bzip2.  Otherwise, assume the file
    # is not compressed.  Does not handle files compressed with 'zip'.
    #
    # import pdb ; pdb.set_trace()
    err_msg = lambda : msg.PrintMsg('Unable to open data file: ' + sim_file)
    ftype = file_type(sim_file)
    if ftype == 'gz':
        import gzip
        try:
            f = gzip.open(sim_file, 'rb')
        except:
            err_msg
            return None
    elif ftype == 'bz2':
        import bz2
        try:
            f = bz2.BZ2File(sim_file, 'rb')
        except:
            err_msg
            return None
    else:
        try:
            f = open(sim_file, 'rb')
        except:
            err_msg
            return None

    return f

################################################################################
#
# Functions to generate directory and file names and modify them.
#
################################################################################

def GetDefaultWPDir():
    """
    Get the default tracing instance whole program pinball directory.

    This is the directory name based solely on tracing parameters.
    """

    return config.wp_dir_basename + '.' + config.input_name

def GetBaseWPDir():
    """
    Get the base whole program pinball directory.

    The base name is either the default defined above, or the name the
    user has specified on the command line.
    """

    if config.whole_pgm_dir != '':
        wp_dir = config.whole_pgm_dir
    else:
        wp_dir = GetDefaultWPDir()

    return wp_dir

def GetWPDir():
    """
    Get the current directory name for the whole program pinballs.

    There are 3 possible locations to get this value (in priority order):
        1) config.relog_dir     - any filtered WP pinballs
        2) config.whole_pgm_dir - user has defined WP pinball dir
        3) default tracing instance dir
    """

    if config.relog_dir != '':
        wp_dir = config.relog_dir
    else:
        wp_dir = GetBaseWPDir()

    return wp_dir

def GetWPPinballs():
    """
    Get a list of all the pinballs in the whole program pinball directory.
    """

    wp_dir = GetWPDir()
    wp_pb = glob.glob(os.path.join(wp_dir, '*.address'))
    wp_pb = [w.replace('.address', '') for w in wp_pb]

    return wp_pb

def GetWPPinballsNoTID():
    """
    Get a list of all the pinballs in the whole program pinball directory
    without TIDs.

    When filtering with a focus thread the relogged WP pinballs have a TID of
    '0' added to the file name.  However, this TID is not used when generating
    the directory names for Data/pp/lit files.
    """

    wp_pb = GetWPPinballs()
    wp_pb = [RemoveTID(w) for w in wp_pb]

    return wp_pb

def AddRelogStr(string):
    """
    If the string doesn't already contain 'config.relog_dir_str', then add it to the
    end of the string.
    """

    if string.find(config.relog_dir_str) == -1:
        return string + config.relog_dir_str
    else:
        return string

def GetRelogPhaseDir(old_dir, phase, options):
    """
    Generate a directory name for the relogged whole program pinballs based
    on the the current phase.

    If the current value for the relog directory in the config object does
    not already have the string 'config.relog_dir_str', then it needs to be added to the
    directory name. Then the string for the appropriate phase is added.
    """

    # Default to the old name.
    #
    new_dir = old_dir

    if phase == config.RELOG_NONE:
        # Set to the original whole program directory name because not in a
        # relogging phase.
        #
        new_dir = GetWPDir()

    if phase == config.RELOG_NAME:
        if options.relog_name != '':
            string = options.relog_name
        if options.use_relog_name != '':
            string = options.use_relog_name
        new_dir = AddRelogStr(old_dir) + '.' + string

    if phase == config.RELOG_FOCUS:
        # Make sure there really is a focus thread.
        #
        if config.focus_thread == -1:
            # Since we know exactly which phase we are in, use the method
            # CheckResult() to exit the app. This records the failure in
            # the *.status file.
            #
            msg.PrintMsg('ERROR: Trying to relog using a focus thread,\n'
                'but a focus thread has not been defined.  Use option \'--focus_thread\' to define a focus thread.')
            CheckResult(-1, options, 'Filtering WP pinballs with focus thread %s' % config.PhaseStr(4))   # Force the failure
        new_dir = AddRelogStr(old_dir) + '.per_thread_' + str(config.focus_thread)

    if phase == config.RELOG_NO_INIT:
        new_dir = AddRelogStr(old_dir) + '.no_init'

    if phase == config.RELOG_NO_CLEANUP:
        new_dir = AddRelogStr(old_dir) + '.no_cleanup'

    # Add the basename of the code exclusion file to the WP dirctory
    # name.
    #
    ce_dir = 'code_ex-'
    if phase == config.RELOG_CODE_EXCLUDE:
        if options.relog_code_exclude != '':
            s = os.path.splitext(os.path.basename(options.relog_code_exclude))
        if options.use_relog_code_exclude != '':
            s = os.path.splitext(os.path.basename(options.use_relog_code_exclude))
        new_dir = AddRelogStr(old_dir) + '.' + ce_dir + s[0]

    if phase == config.RELOG_NO_OMP_SPIN:
        new_dir = AddRelogStr(old_dir) + '.no_omp_spin'

    if phase == config.RELOG_NO_MPI_SPIN:
        new_dir = AddRelogStr(old_dir) + '.no_mpi_spin'

    return new_dir

def GetLogFile():
    """
    Generate the base file name used for many things, including pinballs, BB vector
    files and SimPoints files.
    """

    return Config.GetInstanceName()

def GetDataDir():
    """Get all the Data directories for this tracing instance."""

    data_list = GetWPPinballsNoTID()
    data_list = [os.path.basename(d) + '.Data' for d in data_list]

    return data_list

def GetLitDir():
    """Get all the *.lit directories for this tracing instance."""

    lit_list = GetWPPinballsNoTID()
    lit_list = [os.path.basename(l) + '.lit' for l in lit_list]

    return lit_list

def GetRegionPinballDir():
    """Get all the region pinball directories for this tracing instance."""

    pb_list = GetWPPinballsNoTID()
    pb_list = [os.path.basename(p) + '.pp' for p in pb_list]

    return pb_list

def GetStatusFile():
    """Generate the name of the status file."""

    return Config.GetInstanceFileName(config.phase_status_ext)

def GetMsgFileOption(string):
    """
    If a user defined value for a msg file extension exists, return a PinPlay
    knob which generates a msg file.  Otherwise, return an empty string so the
    default msgifile will be generated.
    """

    if config.msgfile_ext != '':
        # If the msgfile string doesn't start with the char '.', then
        # add it.
        #
        if config.msgfile_ext.find('.') == -1:
            msg_str = '.' + config.msgfile_ext
        else:
            msg_str = config.msgfile_ext
        return ' -pinplay:msgfile ' + string + msg_str
    else:
        # No extension, don't want to add an explict msgfile knob.
        #
        return ''

def ChangeExtension(file_name, old_str, new_str):
    """
    Change the 'extension' at the end a file or directory to a new type.
    For example, change 'foo.pp' to 'foo.Data'

    Do this by substituting the last occurance of 'old_str' in the file
    name with 'new_str'. This is required because the file name may contain
    'old_str' as a legal part of the name which is not at the end of the
    directory name.

    This assumes anything after the last '.' is the file extension.  If there
    isn't a file extention, then just return the original name.
    """

    pos = file_name.rfind(old_str)
    if pos == -1:
        # old_str not found, just return the file_name
        #
        return file_name

    return file_name[:pos] + new_str

def RemoveTID(filename):
    """
    Remove the TID (i.e. the focus_thread) from the end of the file name.

    This assumes the string 'filename' is the base file name, not a file name
    with file extensions.

    For example:
        omnetpp.1.p10000-s10_78607_t0r4_warmup1001500_prolog0_region3500002_epilog0_004_0-00970.0
    not:
        omnetpp.1.p10000-s10_78607_t0r4_warmup1001500_prolog0_region3500002_epilog0_004_0-00970.0.address
    """

    # import pdb;  pdb.set_trace()

    # Remove dot immediately followed by digit(s) at end.
    filename = re.sub('\.\d+$', '', filename);

    return filename
