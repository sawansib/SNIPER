#! /usr/bin/perl -w
# Create regions CSV file in a variety of ways.
#-*-Perl-*- This line forces emacs to use Perl mode.

use strict;
use warnings;
no warnings qw(portable); # allow reading 64-bit hex ints.
use FileHandle;
use File::Basename;
use Getopt::Long;
use POSIX;

my $debug = 0;
my $script = basename $0;

# Just print dots while reading files to keep user entertained.
sub printDot()  {
  print STDERR '.' if $. % 1000 == 0;
}

# Read next slice from file.
# Returns: total number of instructions in slice (0 if EOF).
# Returns: ref to hash of BB num to BB count -OR- instr count if instrs/BB not available.
sub readNextSlice($$) {
  my $fh = shift;               # file handle.
  my $instrsPerBb = shift;      # ref to array of instr counts per BB (or undef if not available).

  my %bbCounts;
  my $instrCount = 0;
  while (<$fh>) {
    printDot();

    # get next slice from A.
    if (/^T:/) {
      my $value = $';

      my @pairs = split / :/, $value;
      for my $pair (@pairs) {
        my ($bb, $icount) = split /:/,$pair,2;
        $instrCount += $icount;

        # update how many times each BB has been seen.
        $bbCounts{$bb} = defined $instrsPerBb ? int($icount / $instrsPerBb->[$bb]) : $icount;
      }
      last;                     # only read 1 slice.
    }

    elsif (/^Dynamic/) {
      last;                     # no more slices.
    }
  }
  return $instrCount, \%bbCounts;
}

# Read a simpoint file.
# Returns ref to hash of cluster number to slice number, weight, etc.
# Returns number of ignored clusters.
sub readSimPointFile($$$) {
  my $simPointFile = shift;
  my $clustersToSkip = shift;
  my $minVal = shift;

  open SPFILE, "< $simPointFile" or die "cannot open $simPointFile: $!\n";
  warn "Reading $simPointFile...\n";

  my $skipped = 0;
  my $curPt = 0;
  my %vals;
  while (<SPFILE>) {
    my ($val, $pt) = split;
    if (grep { $_ == $pt } @$clustersToSkip) {
      warn "  ignoring region $pt due to -skip option.\n";
      $skipped++;
    }
    elsif (defined $minVal && $val < $minVal) {
      warn "  ignoring region $pt because $val < $minVal.\n";
      $skipped++;
    }
    else {
      $vals{$pt} = $val;
      warn "  region $pt: $val.\n";
    }
    $curPt = $pt + 1;
  }
  close SPFILE;
  warn "  ".(scalar keys %vals)." regions read.\n";
  return \%vals, $skipped;
}

# Finds trace vectors in BB file.
# Returns: ref to hash from cluster num to hash of BB num to instr count.
sub findTraceVectors($$) {
  my $bbFile = shift;
  my $traceSlices = shift;

  my $readCmd = ($bbFile =~ /\.gz$/) ? "gzcat $bbFile |" : "< $bbFile";
  open BBFILE, $readCmd or die "cannot open $bbFile: $!\n";
  print STDERR "Reading $bbFile to find BB vectors for ",(scalar keys %$traceSlices)," regions...";

  if ($debug) {
    while (my ($cluster, $slice) = each %$traceSlices ) {
      warn "  looking for region $cluster in slice $slice.\n";
    }
  }

  my %traceVectors;             # hash from orig slice num to hash of BB num to instr count.
  my $sliceNum = -1;
 bbreadloop:
  while (<BBFILE>) {

    printDot();
    if (/^T:/) {
      my $value = $';
      $sliceNum++;

      # determine what trace cluster(s) we're in (if any).
      my @activeTraceClusters;
      scalar keys %$traceSlices; # reset 'each' iterator.
      while (my ($cluster, $slice) = each %$traceSlices ) {
        if ($sliceNum == $slice) {
          push @activeTraceClusters, $cluster;
          print STDERR "\n  found region $cluster in slice $slice..." if $debug;
        }
      }

      # read slice if needed.
      if (scalar @activeTraceClusters) {
        my @pairs = split / :/, $value;
        for my $pair (@pairs) {
          my ($bb, $icount) = split /:/,$pair,2;

          # build vector for trace(s).
          map { $traceVectors{$_}{$bb} += $icount; } @activeTraceClusters;
        }
      }

      # done?
      if (scalar keys %traceVectors == scalar keys %$traceSlices) {
        warn "\n  All region vectors found.\n";
        last;
      }
    } elsif (/^Dynamic/) {
      die "error: only ".(scalar keys %traceVectors)." slices were found.\n";
      last;
    }
  }
  close BBFILE;

  return \%traceVectors;
}

# Read a bblmap file.
# Returns: ref to array of num instrs indexed by BB (some entries may be undef).
# Returns: ref to array of BB addrs indexed by BB (some entries may be undef).
# Returns: ref to array of num bytes indexed by BB (some entries may be undef).
sub readBblmap($) {
  my $bblmapFile = shift;

  my @bbSizes;
  my @bbAddrs;
  my @bbBytes;

  open BBLMAP, "< $bblmapFile" or die "cannot open '$bblmapFile': $!.\n";
  warn "Reading from '$bblmapFile'...\n";
  my $numRead = 0;
  while (<BBLMAP>) {

    # Example file:
    #  #headpc tailpc bblid procid instcount meminstcount intinstcount fpinstcount branchinstcount
    #  4194704 4194708 0 0 2 1 1 0 1 
    #  4194713 4194713 1 0 1 1 0 0 1 
    #  ...

    next if /^#/;
    my ($headAddr, $tailAddr, $blkId, $procId, $size) = split;
    $blkId++;                   # adjust to be one-based indices instead of zero-based.
    $bbSizes[$blkId] = $size;
    $bbAddrs[$blkId] = $headAddr;
    $bbBytes[$blkId] = $tailAddr - $headAddr + 1; # may miss trailing bytes of last instr in block.
    $numRead++;
  }
  close BBLMAP;
  warn "  $numRead BBL maps read.\n";
  return \@bbSizes, \@bbAddrs, \@bbBytes;
}

# Find num instrs and counts in BBs.
# Returns: ref to array of num instrs indexed by BB (some entries may be undef).
# Returns: ref to array of BB counts indexed by BB (some entries may be undef).
# Returns: ref to array of BB addrs indexed by BB (some entries may be undef).
# Returns: ref to array of num bytes indexed by BB (some entries may be undef).
# Returns: total number of instrs.
# Returns: slice size.
# Returns: number of slices.
sub readBbInfo($) {
  my $bbFile = shift;

  my @bbSizes;
  my @bbCounts;
  my @bbAddrs;
  my @bbBytes;
  my $numBbs = 0;
  my $numInstrs = 0;
  my $numBbInstrs = 0;
  my $numSlices = 0;
  my $sliceSize;

  # Read file to find BBs.
  my $readCmd = ($bbFile =~ /\.gz$/) ? "gzcat $bbFile |" : "< $bbFile";
  open BBFILE, $readCmd or die "cannot open $bbFile: $!\n";
  print STDERR "Reading '$bbFile' to find basic info...";
  while (<BBFILE>) {
    printDot();

    if (/^T:/) {
      $numSlices++;
    }

    # Block id: 9870 0x76ed8450:0x76ed8465 static instructions: 7 block count: 1 block size: 27
    if (/^Block id: (\d+) 0x([0-9a-fA-F]+):0x([0-9a-fA-F]+)\s+static instructions:\s+(\d+)\s+block count:\s+(\d+)\s+block size:\s+(\d+)/) {
      my ($blk, $addr, $instrs, $count, $bytes) = ($1, hex $2, $4, $5, $6);
      $bbSizes[$blk] = $instrs;
      $bbCounts[$blk] = $count;
      $numBbs++;
      $numBbInstrs += $instrs * $count;
      $bbAddrs[$blk] = $addr;
      $bbBytes[$blk] = $bytes;
    }

    # SliceSize: 10000000
    if (/^SliceSize:\s+(\d+)/) {
      $sliceSize = $1;
      print STDERR "\n  slice size: $sliceSize...";
    }

    elsif (/^Dynamic instruction count\s+(\d+)/) {
      $numInstrs = $1;
      print STDERR "\n  total instructions executed: $numInstrs...";
    }

  }
  close BBFILE;
  print STDERR "\n  $numSlices slices found.\n";
  print STDERR "  $numBbs BBs read, $numBbInstrs instrs reported in BBs.\n";
  printf STDERR "    Note: this %d fewer than the reported total).\n", $numInstrs - $numBbInstrs
    if $numInstrs != $numBbInstrs;

  return \@bbSizes, \@bbCounts, \@bbAddrs, \@bbBytes, $numInstrs, $sliceSize, $numSlices;
}

# Write disasm-ish files for debug.
sub makeFakeDisasmFiles($$$$$) {
  my $traceVectors = shift;     # ref to hash from cluster num to hash of BB num to instr count.
  my $addrsPerBb = shift;       # ref to array.
  my $instrsPerBb = shift;      # ref to array.
  my $bytesPerBb = shift;       # ref to array.
  my $xedDisasm = shift;        # may be undef.

  my %allAddrs;
  if (defined $xedDisasm) {
    my $readCmd = ($xedDisasm =~ /\.([gb])z2?$/) ? "${1}zcat $xedDisasm |" : "< $xedDisasm";
    open XED, $readCmd or die "cannot open $xedDisasm: $!\n";
    while (<XED>) {

      # XDIS 400190: BINARY     BASE  4883EC08                       sub rsp, 0x8
      if (/^XDIS\s([0-9a-fA-F]+):/) {
        my $addr = hex $1;
        $allAddrs{$addr} = 1;
      }
    }
    close XED;
  }
  my $addrsOk = scalar keys %allAddrs > 0;

  my @clusters = sort {$a <=> $b} keys %$traceVectors;
  for my $cluster (@clusters) {
    my $disFile = "r$cluster.disasm";
    my $tVec = $traceVectors->{$cluster};

    # accumulate counts for each addr in each bb.
    my %icountPerAddr;
    my %blkSizePerAddr;
    my $totalIcount = 0;
    while (my($bb, $icount) = each %$tVec) {
      $totalIcount += $icount;
      my $addr = $addrsPerBb->[$bb];
      if (!defined $addr) {
        printf STDERR "warning: no BB data found for block at 0x%x.\n", $addr;
        next;
      }
      my $icountPerInstr = int($icount / $instrsPerBb->[$bb]);
      my $hits = 0;
      if ($addrsOk) {

        # scan all addrs in this block.
        for (my $a = $addr; $a < $addr + $bytesPerBb->[$bb]; $a++) {
          if (exists $allAddrs{$a}) {
            $icountPerAddr{$a} += $icountPerInstr;
            $hits++;
          }
        }

        # missed any?
        if ($hits < $instrsPerBb->[$bb]) {
          printf STDERR "  note: expected $instrsPerBb->[$bb] instructions at 0x%x; found $hits.\n",
            $addr;
        }
      }

      # allocate remaining counts to first addr.
      if ($hits < $instrsPerBb->[$bb]) {
        $icountPerAddr{$addr} += $icount - ($icountPerInstr * $hits);
        $blkSizePerAddr{$addr} = $instrsPerBb->[$bb] - $hits;
      }
    }

    open DISASM, "> $disFile" or die "cannot open '$disFile': $!.\n";
    warn "Writing fake disasm to '$disFile'...\n";
    print DISASM "# Instr counts per block for region $cluster.\n";
    foreach my $addr (sort { int($a) <=> int($b) } keys %icountPerAddr) {
      if (defined $blkSizePerAddr{$addr}) {
        printf DISASM "# %d iteration(s) of %d instrs in block at 0x%08x: %.2g%% of instrs in this region.\n",
          int($icountPerAddr{$addr} / $blkSizePerAddr{$addr}), $blkSizePerAddr{$addr},
            $addr, 100 * $icountPerAddr{$addr} / $totalIcount;
      }
      printf DISASM "0x%08x: unknown ; n=$icountPerAddr{$addr}\n", $addr;
    }
    print DISASM "# End.\n";
    close DISASM;
  }
}

### vec() implementations of frequency-vector routines. ###

# Convert trace vector with instr-counts to normalized vector.
# Returns: ref to vec of normalized values indexed by BB.
# Returns: total instr count.
# Returns: max BB index.
my $numVecBits = 16;
my $defaultVecLen = 512;
sub normalizeTraceVector_vec($) {
  my $tVec = shift;

  my $icount = 0;
  my $maxBbNum = 0;
  while (my ($bb, $instrs) = each %$tVec) {
    $maxBbNum = $bb if $bb > $maxBbNum;
    $icount += $instrs;
  }
  my $maxVal = (1 << $numVecBits) - 1;
  $defaultVecLen = $maxBbNum - 1 if $maxBbNum - 1 > $defaultVecLen;

  my $tVecNorm = '';
  while (my ($bb, $instrs) = each %$tVec) {
    vec($tVecNorm, $bb, $numVecBits) = int($maxVal * $instrs / $icount); # convert to integer in [0..$maxVal].
    #vec($tVecNorm, $bb, $numVecBits) = ceil($maxVal * $instrs / $icount); # convert to integer in [0..$maxVal].
  }
  return \$tVecNorm, $icount, $maxBbNum;
}

# Add elements of first vector to second.
# Second vector is modified.
sub addVectors_vec($$$) {
  my $vecA = shift;             # ref to vec
  my $vecB = shift;
  my $lastIndex = shift;

  for my $bb (0..$lastIndex) {
    vec($$vecB, $bb, $numVecBits) += vec($$vecA, $bb, $numVecBits);
  }
  return;
}

# Find Manhattan distance between two vectors.
# Returns: distance (min value = 0; smaller is better).
sub getVectorDist_vec($$$) {
  my $vecA = shift;             # ref to vec
  my $vecB = shift;
  my $lastIndex = shift;

  my $maxVal = (1 << ($numVecBits)) - 1;
  my $dist = 0;
  my ($a, $b);
  for my $bb (0..$lastIndex) {
    $a = vec($$vecA, $bb, $numVecBits);
    $b = vec($$vecB, $bb, $numVecBits);
    $dist += abs($a - $b);      # sum of abs values.
  }
  return $dist / $maxVal;
}

# Find the static coverage of first vector in second.
# Returns: fraction of non-zero vectors from first that are non-zero in second (range: [0..1]; larger is better).
sub getStaticVectorCov_vec($$$) {
  my $vecA = shift;
  my $vecB = shift;
  my $lastIndex = shift;

  my $cov = 0;
  my ($a, $b);
  my $num = 0;
  for my $bb (0..$lastIndex) {
    $a = vec($$vecA, $bb, $numVecBits);
    if ($a != 0) {
      $num++;
      $b = vec($$vecB, $bb, $numVecBits);
      $cov++ if $b;
    }
  }
  $cov = $num ? ($cov / $num) : 0;
  return $cov;
}

# Find the dynamic coverage of first vector in second.
# Returns: fraction of non-zero vectors from first that are non-zero in second (range: [0..1]; larger is better).
sub getDynamicVectorCov_vec($$$) {
  my $vecA = shift;
  my $vecB = shift;
  my $lastIndex = shift;

  my $icount = 0;
  my $cov = 0;
  my ($a, $b);
  for my $bb (0..$lastIndex) {
    $a = vec($$vecA, $bb, $numVecBits);
    $icount += $a;
    $b = vec($$vecB, $bb, $numVecBits);
    $cov += $a if $b;
  }
  $cov = $icount ? $cov / $icount : 0;
  return $cov;
}

sub newVec_vec() {
  my $v = '';
  my $x = vec($v, $defaultVecLen, $numVecBits);
  return \$v;
}

### hash implementations of frequency-vector routines. ###

# Convert trace vector with instr-counts to normalized vector.
# Returns: ref to hash of normalized values indexed by BB.
# Returns: total instr count.
# Returns: max BB index.
sub normalizeTraceVector_hash($) {
  my $tVec = shift;

  my $icount = 0;
  my $maxBbNum = 0;
  while (my ($bb, $instrs) = each %$tVec) {
    $maxBbNum = $bb if $bb > $maxBbNum;
    $icount += $instrs;
  }

  my %tVecNorm;
  while (my ($bb, $instrs) = each %$tVec) {
    $tVecNorm{$bb} = $instrs / $icount if $instrs > 0; # range [0..1];
  }
  return \%tVecNorm, $icount, $maxBbNum;
}

# Add elements of first vector to second.
# Second vector is modified.
sub addVectors_hash($$$) {
  my $vecA = shift;             # ref to vec
  my $vecB = shift;
  my $lastIndex = shift;

  while (my ($bb, $valA) = each %$vecA) {
    if (defined $vecB->{$bb}) {
      $vecB->{$bb} += $valA;
    } else {
      $vecB->{$bb} = $valA;
    }
  }
  return;
}

# Find Manhattan distance between two vectors.
# Vectors must be normalized (values sum to 1.0).
# Returns: distance (min value = 0; smaller is better).
sub getVectorDist_hash($$$) {
  my $vecA = shift;             # ref to vec
  my $vecB = shift;
  my $lastIndex = shift;

  my $sumB = 0;
  my $diff = 0;
  while (my ($bb, $valA) = each %$vecA) {
    my $valB = $vecB->{$bb};
    if (defined $valB) {
      $sumB += $valB;
      $diff += abs($valA - $valB);
    }
  }
  my $rem = 1.0 - $sumB;
  $diff += $rem;
  return $diff;
}

# Find the static coverage of first vector in second.
# Vectors can be raw or normalized.
# Returns: fraction of non-zero vectors from first that are non-zero in second (range: [0..1]; larger is better).
sub getStaticVectorCov_hash($$$) {
  my $vecA = shift;
  my $vecB = shift;
  my $lastIndex = shift;

  my $numer = 0;
  my $denom = 0;
  while (my ($bb, $valA) = each %$vecA) {
    if (defined $vecB->{$bb}) {
      $numer++;
    }
    $denom++;
  }
  my $cov = $denom ? ($numer / $denom) : 0;
  return $cov;
}

# Find the dynamic coverage of first vector in second.
# Vectors can be raw or normalized.
# Returns: fraction of non-zero values from first that are non-zero in second (range: [0..1]; larger is better).
sub getDynamicVectorCov_hash($$$) {
  my $vecA = shift;
  my $vecB = shift;
  my $lastIndex = shift;

  my $numer = 0;
  my $denom = 0;
  while (my ($bb, $valA) = each %$vecA) {
    if (defined $vecB->{$bb}) {
      $numer += $valA;
    }
    $denom += $valA;
  }
  my $cov = $denom ? ($numer / $denom) : 0;
  return $cov;
}

sub newVec_hash() {
  return { };
}

# Use pointers to functions.
# This scheme allows other implementations to be used.
# (OOP would have made this much cleaner!)
# Set vec implementations as default.
#my $normalizeTraceVector = \&normalizeTraceVector_vec;
#my $addVectors = \&addVectors_vec;
#my $getVectorDist = \&getVectorDist_vec;
#my $getStaticVectorCov = \&getStaticVectorCov_vec;
#my $getDynamicVectorCov = \&getDynamicVectorCov_vec;
#my $newVec = \&newVec_vec;
my $normalizeTraceVector = \&normalizeTraceVector_hash;
my $addVectors = \&addVectors_hash;
my $getVectorDist = \&getVectorDist_hash;
my $getStaticVectorCov = \&getStaticVectorCov_hash;
my $getDynamicVectorCov = \&getDynamicVectorCov_hash;
my $newVec = \&newVec_hash;

### End of frequency-vector routines. ###

# Find number of instrs that each trace represents, among other things.
# Returns: ref to hash from cluster num to instr counts represented by that trace (if $needWeights).
# Returns: ref to hash from cluster num to sorted list of starting slices for that phase (if $needWeights).
# Returns: ref to hash from cluster num to array of begin,end instr counts.
# Returns: overall dynamic coverage.
# Returns: total number of instrs.
sub findTraceDetails($$$$$$) {
  my $bbFile = shift;
  my $traceVectors = shift;     # ref to hash from cluster num to hash of BB num to instr count.
  my $traceSlices = shift;      # ref to hash from cluster num to slice num.
  my $needWeights = shift;      # boolean.
  my $minCov = shift;           # minimum coverage desired (may be undef).
  my $minNumRegions = shift;    # minimum regions to select when subsetting by coverage (may be undef).

  # normalize trace vectors.
  printf STDERR "Calculating instruction offsets%s and coverage for the following regions from $bbFile:\n",
    ($needWeights ? ", weights" : "");
  my %instrWeights;             # hash of cluster num to instr counts represented by that trace.
  my %phaseBorders;             # hash of cluster num to list of starting slices for that phase.
  my %traceBordersByInstr;      # hash from cluster num to array of begin,end instr counts.
  my %tVecNorm;
  my %traceInstrCounts;
  my @clusters = sort {$a <=> $b} keys %$traceVectors;
  my $maxBbNum = 0;
  for my $cluster (@clusters) {
    my ($thisVecNorm, $thisInstrCount, $thisMaxBbNum) = &$normalizeTraceVector($traceVectors->{$cluster});
    $tVecNorm{$cluster} = $thisVecNorm;
    $traceInstrCounts{$cluster} = $thisInstrCount;
    printf STDERR "  region %2d: %9d instrs, %5d BBs from slice %6d.\n",
      $cluster, $thisInstrCount, scalar keys %{$traceVectors->{$cluster}}, $traceSlices->{$cluster};
    $maxBbNum = $thisMaxBbNum if $thisMaxBbNum > $maxBbNum;
    $instrWeights{$cluster} = 0;
    $phaseBorders{$cluster} = [ ]; # ref to empty array.
  }

  # Read slices until we get the required instrs.
  # Then, find the trace it matches best.
  # Repeat until all slices read.
  my $readCmd = ($bbFile =~ /\.([gb])z2?$/) ? "${1}zcat $bbFile |" : "< $bbFile";
  open BBFILE, $readCmd or die "cannot open $bbFile: $!\n";
  print STDERR "Analyzing slices...";
  my $prevCluster;
  my $sliceNum = -1;
  my %totalVector;
  my $totalInstrCount = 0;

  while (1) {

    # get next slice.
    my ($instrs, $instrCounts) = readNextSlice(\*BBFILE, undef);
    last if $instrs == 0;
    $sliceNum++;

    # record borders if we're in a trace slice.
    my $traceCluster;
    while (my ($cluster, $clusterSlice) = each %$traceSlices) {
      if ($sliceNum == $clusterSlice) {
        $traceBordersByInstr{$cluster}[0] = $totalInstrCount;
        $traceBordersByInstr{$cluster}[1] = $totalInstrCount + $instrs;
        $traceCluster = $cluster if !defined $traceCluster; # remember first match.
      }
    }

    if ($needWeights) {
      my ($thisVecNorm, $thisInstrCount, $thisMaxBbNum) = &$normalizeTraceVector($instrCounts);
      $maxBbNum = $thisMaxBbNum if $thisMaxBbNum > $maxBbNum;

      # find trace to which this cluster is most similar.
      my $bestDist;
      my $bestCluster;
      for my $cluster (@clusters) {

        # perfect match if this is a trace.
        if (defined $traceCluster) {
          $bestDist = 0;
          $bestCluster = $traceCluster;
          last;
        }

        # otherwise, find closest match (Manhattan distance).
        else {
          my $curTVecNorm = $tVecNorm{$cluster};
          my $dist = &$getVectorDist($thisVecNorm, $curTVecNorm, $maxBbNum);
          if (!defined $bestCluster || $dist < $bestDist) {
            $bestCluster = $cluster;
            $bestDist = $dist;
          }
        }
      }
      print STDERR "\n  slice $sliceNum ($thisInstrCount instrs) is in phase $bestCluster..." if $debug;

      # adjust weights.
      $instrWeights{$bestCluster} += $thisInstrCount;

      # determine if we are at the border of a new phase.
      if (!defined $prevCluster || $prevCluster != $bestCluster) {
        push @{$phaseBorders{$bestCluster}}, $sliceNum;
        print STDERR "\n    phase $bestCluster starts at slice $sliceNum..." if $debug;
      }

      # init for next vector.
      $prevCluster = $bestCluster;
    }

    # add to totals.
    $totalInstrCount += $instrs;
    addVectors_hash($instrCounts, \%totalVector, undef);
  }

  close BBFILE;
  warn "\n  Scanned slices 0..$sliceNum.\n";
  warn "Instr boundaries per trace:\n";
  my $numReplacements = 0;
  for my $cluster (@clusters) {
    my $startI = $traceBordersByInstr{$cluster}[0];
    my $endI = $traceBordersByInstr{$cluster}[1];
    my $numI = $endI - $startI;
    printf STDERR "  region %2d: %9d instrs (%15d .. %15d).\n", $cluster, $numI, $startI, $endI;
  }

  if ($needWeights) {
    warn "Resulting number of instrs represented per trace:\n";
    for my $cluster (@clusters) {
      my $w = $instrWeights{$cluster} / $totalInstrCount;
      printf STDERR "  region %2d: represents %15d instrs (weight = %.3f).\n", $cluster, $instrWeights{$cluster}, $w;
    }
  }

  # Calculate coverage.
  warn "Dynamic (execution-count-weighted) instruction (IP) coverage of entire workload per trace:\n";
  my %totalTraceVec;
  my ($totalCov, $totalDynamicCov);
  for my $cluster (@clusters) {
    my $dynamicCov = getDynamicVectorCov_hash(\%totalVector, $traceVectors->{$cluster}, undef);
    addVectors_hash($traceVectors->{$cluster}, \%totalTraceVec, undef);
    $totalDynamicCov = &$getDynamicVectorCov(\%totalVector, \%totalTraceVec, undef);
    printf STDERR "  region %2d: %.4f (cumulative: %.4f).\n",
      $cluster, $dynamicCov, $totalDynamicCov;
  }
  printf STDERR "  overall coverage: %.4f.\n", $totalDynamicCov;

  # subset based on coverage if desired.
  if (defined $minCov) {
    if ($totalDynamicCov <= $minCov) {
      printf STDERR "  dynamic coverage (%.4f) <= minimum (%.4f); not subsetting.\n",
        $totalDynamicCov, $minCov;
    }
    else {
      $minNumRegions = 1 if !defined $minNumRegions ||  $minNumRegions < 1;

      my $numClusters = scalar @clusters;
      if ($minNumRegions >= $numClusters) {
        printf STDERR "  only $numClusters regions (minimum is $minNumRegions); not subsetting.\n";
      }
    
      else {
        printf STDERR "Finding a subset of regions with at least $minNumRegions element(s) to get a minimum of %.4f dynamic coverage...\n",
          $minCov;

        # use a greedy algorithm to avoid 2^n search.
        undef %totalTraceVec;   # reset to empty.
        $totalDynamicCov = 0;
        my %selectedClusters;
        while (scalar keys %selectedClusters < $minNumRegions || $totalDynamicCov < $minCov) {

          # find trace with highest additional cov.
          my ($bestCluster, $bestCov, $skippedCluster, $skippedCov);
          for my $cluster (@clusters) {
            next if defined $selectedClusters{$cluster}; # already added.

            my %curTotalTraceVec = %totalTraceVec; # deep copy so we don't mess with last result.
            addVectors_hash($traceVectors->{$cluster}, \%curTotalTraceVec, undef);
            my $newCov = getDynamicVectorCov_hash(\%totalVector, \%curTotalTraceVec, undef);
            printf STDERR "    region $cluster brings coverage to %.4f...\n", $newCov if $debug;

            # don't use end slices yet.
            if ($traceSlices->{$cluster} == 0 || $traceSlices->{$cluster} == $sliceNum) {
              $skippedCluster = $cluster;
              $skippedCov = $newCov;
              next;
            }

            # see if this is the only one or the best one so far.
            if (!defined $bestCluster || $newCov > $bestCov) {
              warn "      best so far.\n" if $debug;
              $bestCluster = $cluster;
              $bestCov = $newCov;
            }
          }

          # use skipped cluster only as a last resort.
          if (!defined $bestCluster && defined $skippedCluster) {
            $bestCluster = $skippedCluster;
            $bestCov = $skippedCov;
          }

          # add it.
          printf STDERR "  selecting region $bestCluster; ".
            "cumulative dynamic coverage = %.4f.\n", $bestCov;
          $totalDynamicCov = $bestCov;
          $selectedClusters{$bestCluster} = 1;
          addVectors_hash($traceVectors->{$bestCluster}, \%totalTraceVec, undef);
        }

        # delete dropped clusters from various hashes.
        printf STDERR "%d regions in final subset.\n", scalar keys %selectedClusters;
        for my $cluster (@clusters) {
          if (!defined $selectedClusters{$cluster}) {
            delete $traceVectors->{$cluster};
            delete $traceSlices->{$cluster};
            delete $instrWeights{$cluster};
            delete $phaseBorders{$cluster};
            delete $traceBordersByInstr{$cluster};
          }
        }
      }
    }
  }

  return \%instrWeights, \%phaseBorders, \%traceBordersByInstr, $totalDynamicCov, $totalInstrCount;
}

# Select a random set of clusters.
sub pickRandomClusters($$) {
  my $numDesiredRegions = shift;
  my $numSlices = shift;

  my %clusters;                 # key: cluster number, value: slice number (0..$numSlices-1).

  if ($numDesiredRegions >= $numSlices) {
    warn "Note: Desired number of regions ($numDesiredRegions) >= total number of slices ($numSlices);".
      " selecting all slices.\n";
    for (my $c = 0; $c < $numSlices; $c++) {
      $clusters{$c} = $c;
    }
  }

  else {
    warn "Selecting $numDesiredRegions regions at random...\n";
    my %slices;
    while (scalar keys %slices < $numDesiredRegions) {
      my $s = int(rand $numSlices);
      next if exists $slices{$s};
      $slices{$s} = 1;
    }
    my $c = 0;
    for my $s (sort { $a <=> $b } keys %slices) {
      $clusters{$c++} = $s;
    }
  }

  return \%clusters;
}

# Select an evenly-spaced set of clusters.
sub pickRegularClusters($$) {
  my $numDesiredRegions = shift;
  my $numSlices = shift;

  if ($numDesiredRegions >= $numSlices) {
    return pickRandomClusters($numDesiredRegions, $numSlices);
  }

  warn "Selecting $numDesiredRegions regions at regular intervals...\n";
  my %clusters;                 # key: cluster number, value: slice number (0..$numSlices-1).
  my $pos = 0;
  for (my $c = 0; $c < $numDesiredRegions; $c++) {
    $pos += $numSlices / ($numDesiredRegions + 1);
    $clusters{$c} = int($pos);
  }

  return \%clusters;
}

# Make sure weights are positive and sum to instr count.
sub correctInstrWeights($$) {
  my $weights = shift;          # ref to hash: key=cluster, value=weight.
  my $icount = shift;           # total instr count.

  # make values positive and find sum.
  my @clusters = sort { $a <=> $b } keys %$weights;
  my $sum = 0;
  map {
    $weights->{$_} = 0 if $weights->{$_} < 0;
    $sum += $weights->{$_};
  } @clusters;

  # set to equal values if all zeros.
  if ($sum == 0) {
    map { $weights->{$_} = 1; } @clusters;
    $sum = (scalar @clusters);
  }

  # normalize.
  my $newSum = 0;
  map {
    my $w = int($icount * $weights->{$_} / $sum);
    $weights->{$_} = $w;
    $newSum += $w;
  } @clusters;

  # add leftover due to truncation to first weight.
  $weights->{$clusters[0]} += $icount - $newSum;
}

# Make equal instr weights.
sub makeEqualWeights($) {
  my $clusters = shift;

  my %weights;
  map {
    $weights{$_} = 1;
  } keys %$clusters;
  return \%weights;
}

# Make length-based instr weights.
sub makeLengthWeights($$) {
  my $clusters = shift;
  my $traceBordersByInstr = shift;

  my %weights;
  map {
    my $bb = $clusters->{$_};
    my $instrs = $traceBordersByInstr->{$bb}[1] - $traceBordersByInstr->{$bb}[0];
    $weights{$_} = $instrs;
  } keys %$clusters;
  return \%weights;
}

# Returns number of instrs dropped due to maxLen.
sub reportSlices($$$$$$$$$) {
  my $sliceNums = shift;
  my $traceBordersByInstr = shift;
  my $traceInstrWeights = shift;
  my $tid = shift;
  my $seqRegionIds = shift;
  my $regionFileOutput = shift;
  my $weightFileOutput = shift;
  my $maxLen = shift;           # may be undef.
  my $outputInstrsRep = shift;

  my $regionMult = (defined $maxLen) ? 10 : 1;

  if (defined $regionFileOutput) {
    if (open RFOUT, "> $regionFileOutput") {
      warn "saving final regions to '$regionFileOutput'...\n";
    } else {
      warn "cannot open '$regionFileOutput': $!; not saving final regions.\n";
      undef $regionFileOutput;
    }
  }
  if (defined $weightFileOutput) {
    if (open WFOUT, "> $weightFileOutput") {
      warn "saving final weights to '$weightFileOutput'...\n";
    } else {
      warn "cannot open '$weightFileOutput': $!; not saving final weights.\n";
      undef $weightFileOutput;
    }
  }

  my $totalInstrs = 0;
  map { $totalInstrs += $_ } values %{$traceInstrWeights};
  my $totalRegionInstrs = 0;
  my $totalInstrsLost = 0;
  my $nextSeqRegionId = 0;
      
  print "comment,thread-id,region-id,simulation-region-start-icount,simulation-region-end-icount,".
    "region-weight";
  print ",num-instrs-represented" if $outputInstrsRep;
  print "\n";
  for my $cluster (sort {$a <=> $b} keys %$sliceNums) {
    $nextSeqRegionId++;
    my $slice = $sliceNums->{$cluster};
    my $regionId = $seqRegionIds ? $nextSeqRegionId : $cluster * $regionMult;
    my $comment = "cluster $cluster from slice $slice";
    my $startInstr = $traceBordersByInstr->{$cluster}[0];
    my $endInstr = $traceBordersByInstr->{$cluster}[1];
    my $numInstrs = $endInstr - $startInstr;
    my $numRep = (defined $traceInstrWeights->{$cluster}) ? $traceInstrWeights->{$cluster} : 0;
    my $weight = $numRep / $totalInstrs;

    my $printRegion = sub
      {
        print "# Region = ", $regionId, " Slice = ", $slice, " Icount = ", $startInstr, " Length = ", $numInstrs;
        printf " Weight = %.4f\n", $weight;
        printf "$comment,$tid,$regionId,$startInstr,$endInstr,%.6f\n", $weight;
        print ",$numRep" if $outputInstrsRep;
        print "\n";
      };
    
    # handle regions that are too big.
    if (defined $maxLen && $numInstrs > $maxLen) {
      my $origEndInstr = $endInstr;
      my $origStartInstr = $startInstr;
      my $origNumInstrs = $numInstrs;
      my $origComment = $comment;
      my $numRep1 = ceil($numRep / 2); # estimate only.
      my $numRep2 = floor($numRep / 2); # estimate only.
      $weight /= 2;             # estimate only.
      my $msg = "Split region $cluster into 2 parts due to length";
      my $numLost = 0;
      my $numInstrs1 = ceil($numInstrs / 2);
      my $numInstrs2 = floor($numInstrs / 2);

      # get beginning and end (leave gap in middle).
      if ($origNumInstrs > $maxLen * 2) {
        $numLost = $origNumInstrs - $maxLen * 2;
        $msg .= "; lost $numLost instrs";
        $numInstrs1 = $maxLen;
        $numInstrs2 = $maxLen;
      }
      $totalInstrsLost += $numLost;
      print "# $msg.\n";
      warn "  $msg.\n";

      # truncate this region.
      $comment = "beginning of $origComment";
      $numRep = $numRep1;
      $numInstrs = $numInstrs1;
      $endInstr = $origStartInstr + $numInstrs;
      $regionId++;
      &$printRegion();
      $totalRegionInstrs += $numInstrs;
        
      # make a new region at the end.
      $nextSeqRegionId++;
      $comment = "end of $origComment";
      $numRep = $numRep2;
      $numInstrs = $numInstrs2;
      $startInstr = $origEndInstr - $numInstrs;
      $endInstr = $origEndInstr;
      $regionId++;
      &$printRegion();
    }

    else {
      &$printRegion();
    }

    print RFOUT "$slice $cluster\n" if defined $regionFileOutput;
    print WFOUT "$weight $cluster\n" if defined $weightFileOutput;
    $totalRegionInstrs += $numInstrs;
  }
  close RFOUT if defined $regionFileOutput;
  close WFOUT if defined $weightFileOutput;

  print "# Total instructions in $nextSeqRegionId regions = $totalRegionInstrs.\n";
  print "# Total instructions lost due to long regions = $totalInstrsLost.\n" if defined $maxLen;
  print "# Total instructions in workload = $totalInstrs.\n";
  warn "Number of regions created = $nextSeqRegionId.\n";
}

sub usage($) {
  my $msg = shift;
  warn "$script: $msg\n" if defined $msg;

  print STDERR <<"ENDMSG";
usage: $script [options] <bb-file>.
  $script selects slices from the <bb-file> and creates a region file.
  The <bb-file> input is the output of the -bbprofile Pin tool (can be gzip'd).
  The output of $script is a comma-separate-value (CSV) file written to stdout.

  Options:

   You must use exactly one option to select slices from <bb-file>:
    -region_file <file>      File containing lines in 
                              <slice-index><space><region-id> format, 
                              one region per line.
                             The <slice-index> starts at 0 (zero).
                             This is the format output by 
                              'simpoint -saveSimpoints'.
    -random_regions <n>      Randomly select <n> slices.
    -regular_regions <n>     Select <n> slices spaced at regular intervals.

   You must use exactly one option to assign weights to the regions:
    -weight_file <file>      File containing lines in 
                              <weight><space><region-id> format,
                              one region per line.
                             This is the format output by
                              'simpoint -saveSimpointWeights'.
                             The weights will be normalized to sum to 1.0
                              if needed.
                             There must be a weight for each region.
    -equal_weights           Assign weights equally.
    -length_weights          Assign weights proportional to length of region.
    -calc_weights            Calculate weights (may take a while).

  Other options:
    -skip <n>                Ignore the <n>th <region-id> from the region
                              and/or weight files.
                             This option may be used more than once to skip
                              multiple regions.
                             Use of this option forces recalculation of
                              weights if any regions are skipped.
    -min_weight <w>          Discard any region that has a weight less than
                              <w> in the weight file.
                             Use of this option forces recalculation of
                              weights if any regions are dropped.
                             Note that this does NOT force a minimum weight
                              of the recalculated weights.
    -cov_goal <c>            Select a subset of the regions such that the
                              dynamic coverage is at least <c>.
                             Use of this option forces recalculation of
                              weights if any regions are dropped (unless
                              -equal_weights was used).
    -min_num_regions <n>     Select at least <n> regions when subsetting
                              via -cov_goal.
    -max_length <n>          Break up regions with more than <n> instructions.
                              Renumbers regions unless -seq_region_ids is used.
    -tid <t>                 Set the thread-id in the output to <t>
                              (default = 0).
    -seq_region_ids          Force sequential region-ids in the output, i.e.,
                              1, 2, ...
    -region_file_out <file>  Output file containing final regions in same
                              format as -region_file input.
    -weight_file_out <file>  Output file containing final weights in same
                              format as -weight_file input.
    -output_instrs_rep       Output the number of instructions represented
                              in each region to stdout.
    -debug                   Output some debug info.

  Examples:
    $script -region_file foo.simpoints -weight_file foo.weights
    $script -region_file foo.simpoints -calc_weights
    $script -region_file foo.simpoints -weight_file foo.weights -min_weight 0.02
    $script -regular_regions 100 -calc_weights -cov_goal 0.95
    $script -random_regions 100 -calc_weights -cov_goal 0.95 -region_file_out regions.txt
ENDMSG
  exit 1;
}

sub main() {
  my $cmd = $0 . ' ' . join(' ', @ARGV);
  my %opts = ( tid=>0 );
  my $optOk = GetOptions(\%opts,
                         "region_file=s",
                         "random_regions=i",
                         "regular_regions=i",
                         "weight_file=s",
                         "equal_weights!",
                         "calc_weights!",
                         "length_weights!",
                         "min_weight=f",
                         "cov_goal=f",
                         "skip=i@",
                         "tid=i",
                         "seq_region_ids!",
                         "region_file_out=s",
                         "weight_file_out=s",
                         "min_num_regions=i",
                         "max_length=i",
                         "output_instrs_rep!",
                         "bblmap_file=s", # not documented
                         "fake_disasm!",  # not documented
                         "xed_disasm=s",  # not documented
                         "debug!");
  usage(undef) if (!$optOk || @ARGV != 1);
  my $numRegionKnobs = 0;
  map { $numRegionKnobs++ if defined $opts{$_}; } qw(region_file random_regions regular_regions);
  usage(sprintf "expecting exactly 1 region knob; found $numRegionKnobs.") if $numRegionKnobs != 1;
  my $numWeightKnobs = 0;
  map { $numWeightKnobs++ if defined $opts{$_}; } qw(weight_file equal_weights calc_weights length_weights);
  usage(sprintf "expecting exactly 1 weight knob; found $numWeightKnobs.") if $numWeightKnobs != 1;
  usage("coverage goal must be > 0.") if defined $opts{cov_goal} && $opts{cov_goal} <= 0;
  usage("minimum weight must be < 1.") if defined $opts{min_weight} && $opts{min_weight} >= 1;

  my $bbFile = shift @ARGV;
  $debug = defined $opts{debug};
  my $factor = 1;               # Hard-coded for now. Could be used later to allow >1 slices per region.

  # look up the sizes and counts of the BBs.
  my ($instrsPerBb, $countsPerBb, $addrsPerBb, $bytesPerBb, $instrCount, $sliceSize, $numSlices) = readBbInfo($bbFile);

  # get some of this data from the bblmap file if provided.
  ($instrsPerBb, $addrsPerBb, $bytesPerBb) = readBblmap($opts{bblmap_file}) if defined $opts{bblmap_file};

  my $clusters;                 # ref to hash of cluster num to slice num.
  my $numSkipped = 0;           # number of clusters skipped.
  my $calcWeights = 0;          # need to [re]calculate weights.
  my $setLengthWeights = 0;        # need to set weights to lengths.

  # read simpoint clusters.
  if (defined $opts{region_file}) {
    my $simPointFile = $opts{region_file};
    my $clustersToSkip = $opts{skip};
    ($clusters, $numSkipped) = readSimPointFile($simPointFile, $clustersToSkip, undef);
    $calcWeights = 1 if $numSkipped > 0;
  }

  # create random traces.
  elsif (defined $opts{random_regions}) {
    $clusters = pickRandomClusters($opts{random_regions}, $numSlices);
  }

  # create regularly-spaced traces.
  elsif (defined $opts{regular_regions}) {
    $clusters = pickRegularClusters($opts{regular_regions}, $numSlices);
  }

  # shouldn't fall through.
  else { die; }

  # check clusters.
  scalar keys %$clusters;       # reset iterator.
  while (my ($num, $slice) = each %$clusters) {
    die "error: slice number $slice >= $numSlices in region $num.\n"
      if $slice >= $numSlices;
    warn "  region $num = slice $slice.\n" if $debug;
  }

  # read simpoint weights.
  my $weights;        # ref to hash;
  if (defined $opts{weight_file}) {
    my $weightFile = $opts{weight_file};
    my $clustersToSkip = $opts{skip};
    my $minWeight = $opts{min_weight}; # may be undef.
    my ($fileWeights, $numWeightsSkipped) = readSimPointFile($weightFile, $clustersToSkip, $minWeight);
    my $numWeights = scalar keys %$fileWeights;

    # check that weights are for known clusters.
    while (my ($c,$w) = each %$fileWeights) {
      die "$script: weight found for unknown region $c.\n" if !defined $clusters->{$c};
    }

    # check that each cluster has a weight unless some were dropped.
    my $numClusters = scalar keys %$clusters;
    my $wasDropped = defined $minWeight && $numWeights < $numClusters;
    foreach my $c (keys %$clusters) {
      if (defined $fileWeights->{$c}) {
        $weights->{$c} = $fileWeights->{$c};
      }
      elsif ($wasDropped) {
        delete $clusters->{$c};
        $calcWeights = 1;
      }
      else {
        die "$script: weight not found for cluster $c.\n";
      }
    }
  }

  # equal weights.
  elsif (defined $opts{equal_weights}) {
    $weights = makeEqualWeights($clusters);
  }

  # calculate weights
  elsif (defined $opts{calc_weights}) {
    $calcWeights = 1;           # do later.
  }

  # make weights equal to lengths
  elsif (defined $opts{length_weights}) {
    $setLengthWeights = 1;      # do later.
  }

  # shouldn't fall through.
  else { die; }

  my $numClusters = scalar keys %$clusters;
  die "Zero regions selected; exiting.\n" if $numClusters == 0;

  # read (instr-count weighted) BB vectors for trace slices.
  my $traceVectors = findTraceVectors($bbFile, $clusters);
  die "internal error" unless scalar keys %$traceVectors == $numClusters;

  # find coverage, trace weights, phase-transition points, and trace borders by instr count, as needed.
  my $minCov = $opts{cov_goal};
  my $calcWeightsNow = (defined $minCov) ? 0 : $calcWeights; # defer calculation when cov_goal used.
  my ($newWeights, $phaseBorders, $traceBordersByInstr, $cov, $newInstrCount) = 
    findTraceDetails($bbFile, $traceVectors, $clusters,
                     $calcWeightsNow, $minCov, $opts{min_num_regions});
  $weights = $newWeights if $calcWeightsNow;
  my $numNewClusters = scalar keys %$traceVectors;
  my $need2ndPass = ($calcWeights && !$calcWeightsNow);

  # has the number of clusters changed (based on cov_goal)?
  if ($numClusters != $numNewClusters) {
    
    # fix clusters and weights.
    map {
      if (!defined $traceVectors->{$_}) {
        delete $clusters->{$_};
        delete $weights->{$_} if defined $weights;
      }
    } keys %$clusters;
    $calcWeights = 1 unless defined $opts{equal_weights};
    $need2ndPass = 1;
  }

  # redo if needed.
  if ($need2ndPass) {
    warn "Second pass is required.\n";
    ($weights, $phaseBorders, $traceBordersByInstr, $cov, $newInstrCount) = 
      findTraceDetails($bbFile, $traceVectors, $clusters, $calcWeights, undef, undef);
  }

  warn "warning: instruction count from slices ($newInstrCount) != instruction count from BB data ($instrCount).\n"
    if $instrCount && $instrCount != $newInstrCount;

  # fix up the weights.
  $weights = makeLengthWeights($clusters, $traceBordersByInstr) if $setLengthWeights;
  correctInstrWeights($weights, $newInstrCount);

  # make fake disasm files for debugging other tools.
  makeFakeDisasmFiles($traceVectors, $addrsPerBb, $instrsPerBb, $bytesPerBb, $opts{xed_disasm})
    if $opts{fake_disasm};

  # print the results.
  warn "Writing the region file...\n";
  print "# Regions based on '$cmd':\n";
  my $numInstrsLost = reportSlices($clusters, $traceBordersByInstr, $weights, $opts{tid}, $opts{seq_region_ids},
                                   $opts{region_file_out}, $opts{weight_file_out}, $opts{max_length},
                                   $opts{output_instrs_rep});
  printf "# Total slices in workload = $numSlices.\n";
  printf "# Overall dynamic coverage of workload by these regions = %.4f%s.\n",
    $cov, ($numInstrsLost ? " (including lost instrs)" : "");
}

main();
warn "$script: done.\n";
