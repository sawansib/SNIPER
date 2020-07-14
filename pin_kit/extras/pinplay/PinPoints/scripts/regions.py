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
# Read in a file of frequency vectors (BBV or LDV) and execute one of several
# actions on it.  Default is to generate a regions CSV file from a BBV file.
# Other actions include:
#   normalizing and projecting FV file to a lower dimension
#
# $Id: regions.py,v 1.11.1.9 2014/06/09 23:30:44 tmstall Exp tmstall $

import datetime
import glob
import optparse
import os
import random
import re
import sys

import cmd_options
import msg
import util

def GetOptions():
    """
    Get users command line options/args and check to make sure they are correct.

    @return List of options and 3 file pointers: fp_bbv, fp_simp, fp_weight
    """

    version = '$Revision: 1.11.1.9 $';      version = version.replace('$Revision: ', '')
    ver = version.replace(' $', '')
    us = '%prog [options] FVfile'
    desc = 'Implements several different actions to process FV (Frequency Vector) files ' \
           'such as BBV and LDV files.  ' \
           'All actions requires a FV file as an argument, while some require additional ' \
           'options.  ' \
           '                                                            '\
           '--------------------------------------------'\
           '                                                            '\
           'Default action is to generate a regions CSV file (--csv_region), which requires additional '\
           'options --region_file and --weight_file. '

    parser = optparse.OptionParser(usage=us, version=ver, description=desc)

    # Command line options to control script behavior.
    #
    # import pdb;  pdb.set_trace()
    cmd_options.csv_region(parser, '')
    cmd_options.focus_thread(parser, '')
    # cmd_options.bbv_file(parser)        # Currently, don't use this option as FV file is required
    cmd_options.project_bbv(parser, '')
    cmd_options.region_file(parser, '')
    cmd_options.weight_file(parser, '')

    # Parse command line options and get any arguments.
    #
    (options, args) = parser.parse_args()

    # If user does not chose an action to perform, then run the
    # default: region CSV generation
    #
    if not options.project_bbv:
        options.csv_region = True

    # Must at least define a FV file. 
    #
    if hasattr(options, 'bbv') and options.bbv_file  != '':
        bbv_file = options.bbv_file
    else:
        if len(args) < 1:
           msg.PrintAndExit('Must have at least a FVfile as an argument.\n'
            'Use -h to get help')
        bbv_file = args[0]

    # Check to make sure valid FV file exists.
    #
    # import pdb;  pdb.set_trace()
    err_msg = lambda string: msg.PrintAndExit('This is not a valid file, ' + string + \
                '\nUse -h for help.')
    bbv_str = "basic block vector file: "
    if hasattr(options, 'bbv_file') and options.bbv_file  == '':
        bbv_file = args[0]
    if not os.path.isfile(bbv_file):
        err_msg(bbv_str + bbv_file)

    # BBV file must have at least one line which starts with 'T:'.
    #
    fp_bbv = util.OpenCompressFile(bbv_file)
    if fp_bbv == None:
        err_msg(bbv_str + bbv_file)
    line = fp_bbv.readline()
    while not line.startswith('T:') and line != '':
        line = fp_bbv.readline()
    if not line.startswith('T:'):
        err_msg(sim_str + simp_file)
    fp_bbv.seek(0,0)

    # If required, look for additional files.
    #
    fp_simp = fp_weight = None
    if options.csv_region:
        sim_str = "simpoints file: "
        weight_str = "weights file: "
        simp_file = options.region_file
        weight_file = options.weight_file
        if not os.path.isfile(simp_file):
            err_msg(sim_str + simp_file)
        if not os.path.isfile(weight_file):
            err_msg(weight_str + weight_file)

        # Simpoints file must start with an integer.
        #
        fp_simp = util.OpenCompressFile(simp_file)
        if fp_simp == None:
            err_msg(sim_str + simp_file)
        line = fp_simp.readline()
        l_list = line.split()
        if not l_list[0].isdigit():
            err_msg(sim_str + simp_file)

        # Weight file must either have a floating point number < 1.0 as the first
        # value in the file or the first line must be two integers.  (The first
        # integer are assumed to be '1', i.e. a slice with weight 1.  Should never get
        # a weight > 1.)
        #
        fp_weight = util.OpenCompressFile(weight_file)
        if fp_weight == None:
            err_msg(weight_str + weight_file)
        line = fp_weight.readline()
        l_list = line.split()
        if '.' not in l_list[0] and not re.search('\d\s\d', line):
            err_msg(weight_str + weight_file)

        fp_simp.seek(0,0)
        fp_weight.seek(0,0)

    return (options, fp_bbv, fp_simp, fp_weight)

def GetSlice(fp):
    """
    Get the frequency vector for one slice (i.e. line in the FV file).

    All the frequency vector data for a slice is contained in one line.  It
    starts with the char 'T'.  After the 'T', there should be a sequence of
    the following tokens:
       ':'  integer  ':' integer
    where the first integer is the dimension index and the second integer is
    the count for that dimension. Ignore any whitespace.

    @return list of the frequency vectors for a slice, element = (dimension, count)
    """

    fv = []
    line = fp.readline()
    while not line.startswith('T:') and line != '':
        # print 'Skipping line: ' + line

        # Don't want to skip the part of BBV files at the end which give
        # information on the basic blocks in the file.  If 'Block id:' is
        # found, then back up the file pointer to before this string.
        #
        if line.startswith('Block id:'):
            fp.seek(0-len(line), os.SEEK_CUR)
            return []
        line = fp.readline()
    if line == '': return []

    blocks = re.findall(':\s*(\d+)\s*:\s*(\d+)\s*', line)
    # print 'Slice:'
    for block in blocks:
        # print block
        bb = int(block[0])
        count = int(block[1])
        fv.append((bb, count))

    # import pdb;  pdb.set_trace()
    return fv

def GetBlockIDs(fp):
    """
    Get the information about each basic block which is stored at the end
    of BBV frequency files.

    Extract the values for fields 'block id' and 'static instructions' from
    each block.  Here's an example block id entry:

      Block id: 2233 0x69297ff1:0x69297ff5 static instructions: 2 block count: 1 block size: 5

    @return list of the basic block info, elements are (block_id, icount of block)
    """

    block_id = []
    line = fp.readline()
    while not line.startswith('Block id:') and line != '':
        line = fp.readline()
    if line == '': return []

    while line.startswith('Block id:'):
        bb = int(line.split('Block id:')[1].split()[0])
        bb -= 1           # Change BBs to use 0 based numbering instead of 1 based
        icount = int(line.split('static instructions:')[1].split()[0])
        block_id.append((bb, icount))
        line = fp.readline()

    # import pdb;  pdb.set_trace()
    return block_id

############################################################################
#
#  Functions for generating regions CSV files
#
############################################################################

def GetWeights(fp):
    """
    Get the regions and weights from a weights file.

    @return lists of regions and weights
    """

    weight_list = []
    weight_regions = []
    for line in fp.readlines():
        field = re.match('(0\.\d+).*(\d+)', line)

        # Look for the special case where the first field is a single digit
        # without the decimal char '.'.  This should be the weight of '1'.
        #
        if field == None:
            field = re.match('(\d)\s(\d)', line)

        if field:
            weight = float(field.group(1))
            region = int(field.group(2))
            weight_list.insert(region, weight)
            weight_regions.append(region)

    return weight_list, weight_regions

def GetSimpoints(fp):
    """
    Get the regions and slices from the Simpoint file.

    @return list of regions and slices from a Simpoint file
    """

    slice_list = []
    simp_regions = []
    for line in fp.readlines():
        field = re.match('(\d+).*(\d+)', line)
        if field:
            slice_num = int(field.group(1))
            region = int(field.group(2))
            slice_list.insert(region, slice_num)
            simp_regions.append(region)

    return slice_list, simp_regions

def GetRegionBBV(fp):
    """
    Read all the frequency vector slices and the basic block id info from a
    basic block vector file.  Put the data into a set of lists which are used
    in generating CSV regions.

    @return cumulative_icount, all_bb, bb_freq, bb_num_instr, region_bbv
    """

    # Dictionary which contains the number of instructions in each BB.
    # Key is basic block number.
    #
    bb_num_instr = {}

    # Dictionary which contains the number of times a BB was executed
    # Key is basic block number.
    #
    bb_freq = {}

    # Currently not set by the function.  May use in the future for calculating
    # coverage.
    #
    # List of BB vectors for each representative region. Each element is 
    # a dictionary keyed on BB number with the icount of the block in that
    # specific slice.
    #
    region_bbv = []

    # Set of all BB found in the BBV file. Each element
    # is a tuple with the BB number and # of instr in BB.
    #
    all_bb = []

    # List of the cumulative sum of instructions in the slices.  There is one
    # entry for each slice in the BBV file which contains the total icount up
    # to the end of the slice.
    #
    cumulative_icount = []

    # Cumulative sum of instructions so far
    #
    run_sum = 0

    # Get each slice & generate some data on it.
    #
    while True:
        fv = GetSlice(fp)
        if fv == []:
            break
        # print fv

        # Get icount for BB in slice and record the cumulative icount.
        #
        sum = 0
        for bb in fv:
            count = bb[1]
            sum += count

            # Add the number instructions for the current BB to total icount for
            # this specific BB (bb_num_instr).  
            #
            bb_num_instr[bb] = bb_num_instr.get(bb, 0) + count

            # Increment the number of times this BB number has been encountered
            #
            bb_freq[bb] = bb_freq.get(bb, 0) + 1

        if sum != 0:
            run_sum += sum
            cumulative_icount += [run_sum]

    # import pdb;  pdb.set_trace()

    # Read the basic block information at the end of the file if it exists. 
    #
    # import pdb;  pdb.set_trace()
    all_bb = GetBlockIDs(fp)
    # if all_bb != []:
        # print 'Block ids'
        # print all_bb

    # The list 'all_bb' should contain one entry for each basic block in the
    # application (and the corresponding icount).  Check to see if there are
    # any missing BB entries in the list 'all_bb'.  If there are, then add them
    # to the list with an icount of 0.  Sort the final list so the icount can
    # be accessed by BB number in constant time.
    #
    # import pdb;  pdb.set_trace()
    if all_bb != []:
        all_bb.sort(key=lambda bb: bb[0])
        length = len(all_bb)
        max_bb_num = all_bb[length-1][0]   # Last list entry has the total number of BB
        if max_bb_num+1 > length:
            # Missing at least one BB entry in the list.  
            #
            array_index = 0                # Used to access the next entry in the list
            count = 0                      # Used to loop thru the list
            while count <= length:
                if all_bb[array_index][0] != count:
                    # Missing this BB entry in the list.  Add the missing BB tuple
                    # with icount = 0
                    #
                    all_bb.append((array_index, 0))
                    count += 1             # Skip the 'missing' entry
                array_index += 1
                count += 1
        all_bb.sort(key=lambda bb: bb[0])  # Sort once missing entries are added

    # import pdb;  pdb.set_trace()
    return cumulative_icount, all_bb, bb_freq, bb_num_instr, region_bbv

def CheckRegions(simp_regions, weight_regions):
    """
    Check to make sure the simpoint and weight files contain the same regions.

    @return no return value
    """

    if len(simp_regions) != len(weight_regions) or \
       set(simp_regions) != set(weight_regions):
            msg.PrintMsg('ERROR: Regions in these two files are not identical')
            msg.PrintMsg('   Simpoint regions: ' + str(simp_regions))
            msg.PrintMsg('   Weight regions:   ' + str(weight_regions))
            cleanup()
            sys.exit(-1)

def GenRegionCSV(options, fp_bbv, fp_simp, fp_weight):
    """
    Read in three files (BBV, weights, simpoints) and print to stdout
    a regions CSV file which defines the representative regions.

    @return no return value
    """

    # Read data from weights, simpoints and BBV files.
    # Error check the regions.
    #
    weight_list, weight_regions = GetWeights(fp_weight)
    slice_list, simp_regions = GetSimpoints(fp_simp)
    cumulative_icount, all_bb, bb_freq, bb_num_instr, region_bbv = GetRegionBBV(fp_bbv)
    CheckRegions(simp_regions, weight_regions)

    total_num_slices = len(cumulative_icount)
    total_instr =  cumulative_icount[len(cumulative_icount)-1]

    # import locale
    # locale.setlocale(locale.LC_ALL, "")
    # total_instr = locale.format('%d', total_instr, True)
    # total_bb_icount = locale.format('%d', total_bb_icount, True)

    # Print header information
    #
    msg.PrintMsgNoCR('# Regions based on: ')
    for string in sys.argv:
        msg.PrintMsgNoCR(string + ' '),
    msg.PrintMsg('')
    msg.PrintMsg('# comment,thread-id,region-id,simulation-region-start-icount,simulation-region-end-icount,region-weight')
    # msg.PrintMsg('')

    # Print region information
    #
    # import pdb;  pdb.set_trace()
    if options.focus_thread != -1:
        tid = int(options.focus_thread)
    else:
        tid = 0
    total_icount = 0
    region = 1              # First region is always numbered 1
    for slice_num, weight in zip(slice_list, weight_list):
        if slice_num == 0:
            # If this is the first slice, set the initial icount to 0
            #
            start_icount = 0
        else:
            # Use cumulative icount of previous slice to get the initial
            # icount of this slice.  
            #
            start_icount = cumulative_icount[slice_num-1]+1
        end_icount = cumulative_icount[slice_num]
        length = end_icount - start_icount + 1
        total_icount += length
        msg.PrintMsg('# Region = %d Slice = %d Icount = %d Length = %d Weight = %.5f' % \
            (region, slice_num, start_icount, length, weight))
        msg.PrintMsg('Cluster %d from slice %d,%d,%d,%d,%d,%.5f\n' % \
            (region-1, slice_num, tid, region, start_icount, end_icount, weight))
        region +=1

    # Currently does nothing as 'region_bbv' is always null (at least for now.)
    #
    # Get a set which contains BBs of all representative regions
    #
    all_region_bb = set()
    for bbv in region_bbv:
        region_bb = 0
        for bb in bbv:
            all_region_bb.add(bb)
            bb, icount = all_bb[bb-1]
            region_bb += int(icount)
        print 'Trace coverage: %.4f' % (float(region_bb)/total_instr)

    # Get total number of instructions for BBs in representative regions
    #
    region_bb_icount = 0
    for num in all_region_bb:
        bb, icount = all_bb[num-1]
        region_bb_icount += int(icount)

    # Print summary statistics
    #
    # import pdb;  pdb.set_trace()
    msg.PrintMsg('# Total instructions in %d regions = %d' % (len(simp_regions), total_icount))
    msg.PrintMsg('# Total instructions in workload = %d' % cumulative_icount[total_num_slices-1])
    msg.PrintMsg('# Total slices in workload = %d' % total_num_slices)
    # msg.PrintMsg('# Overall dynamic coverage of workload by these regions = %.4f' \
    #     % (float(region_bb_icount)/total_bb_icount))

############################################################################
#
#  Functions for normalization and projection
#
############################################################################

def GetDimRandomVector(proj_matrix, proj_dim, dim):
    """
    Get the random vector for dimension 'dim'.  If it's already in 'proj_matrix',
    then just return it.  Otherwise, generate a new random vector of length
    'proj_dim' with values between -1 and 1.

    @return list of length 'dim' which contains vector of random values
    """


    # import pdb;  pdb.set_trace()
    if proj_matrix.has_key(dim):
        # print 'Using random vector: %4d' % dim
        vector = proj_matrix.get(dim)
    else:
        # print 'Generating random vector: %4d' % dim
        random.seed()             # Use default source for seed
        vector = []
        index = 0
        while index < proj_dim:
            vector.append(random.uniform(-1, 1))
            index += 1
        proj_matrix[dim] = vector

    return vector

def ProjectFVFile(fp, proj_dim=15):
    """
    Read all the slices in a frequency vector file, normalize them and use a
    random projection matrix to project them onto a result matrix with dimensions:
        num_slices x proj_dim.

    @return list of lists which contains the result matrix
    """

    # Dictionary which contains the random projection matrix.  The keys are the
    # FV dimension (NOT the slice number) and the value is a list of random
    # values with length 'proj_dim'.
    #
    proj_matrix = {}

    # List of lists which contains the result matrix. One element for each slice. 
    #
    result_matrix = []

    while True:
        fv = GetSlice(fp)
        if fv == []:
            break

        # Get the sum of all counts for this slice for use in normalizing the
        # dimension counts.
        #
        # import pdb;  pdb.set_trace()
        # print fv
        vector_sum = 0
        for block in fv:
            vector_sum += block[1]

        # Initilize this slice/vector of the result matrix to zero
        #
        result_vector = [0] * proj_dim

        # For each element in the slice, project using the "dimension of the
        # element", not the element index itself!
        #
        sum = 0
        # import pdb;  pdb.set_trace()
        for block in fv:
            dim = block[0]
            # print 'Dim: %4d' % dim
            count = float(block[1]) / vector_sum  # Normalize freq count

            # Get the random vector for the dimension 'dim' and project the values for
            # 'dim' into the result
            #
            proj_vector = GetDimRandomVector(proj_matrix, proj_dim, dim)
            index = 0
            while index < proj_dim:
                result_vector[index] += count * proj_vector[index]
                index += 1

        result_matrix.append(result_vector)

    # import pdb;  pdb.set_trace()
    return result_matrix

def PrintFloatMatrix(matrix):
    """
    Print a matrix composed of a list of list of floating point values.

    @return no return value.
    """

    index = 0
    while index < len(matrix):
        slice = matrix[index]
        for block in slice:
            # print '%6.8f' % block,
            print '%6.3f' % block,
        print
        index += 1

def cleanup():
    """
    Close all open files and any other cleanup required.

    @return no return value
    """

    fp_bbv.close()
    if fp_simp:
        fp_simp.close()
    if fp_weight:
        fp_weight.close()

############################################################################

options, fp_bbv, fp_simp, fp_weight = GetOptions()

if options.project_bbv:
    result_matrix = ProjectFVFile(fp_bbv)
    PrintFloatMatrix(result_matrix)
else:
    GenRegionCSV(options, fp_bbv, fp_simp, fp_weight)

cleanup()
sys.exit(0)

