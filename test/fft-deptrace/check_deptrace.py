#!/usr/bin/env python

import sys, re, collections

BRANCH = 1
LOAD = 2
STORE = 3
GENERAL = 4

def insnstr(x):
  if x == BRANCH:
    return 'b'
  if x == LOAD:
    return 'L'
  if x == STORE:
    return 'S'
  if x == GENERAL:
    return 'd'
  return 'ERROR'

total_insns = 0
insns = collections.deque([], 256)

def check(n):
  if len(insns) < n:
	return True
  insntype = insns[-n]
  if insntype == BRANCH or insntype == STORE:
    #print map(insnstr, insns)
    print total_insns, insnstr(insntype)
  #assert(insntype != BRANCH)
  #assert(insntype != STORE)
  return True

for l in sys.stdin.readlines():
  l = collections.deque(l.split())
  while l:

        found = 0
        popnum = 0

	m = re.match
	m = re.match(r'\d', l[0])
        if m:
		# Found a number of instructions
		insns.extend([GENERAL] * int(m.string))
		found += 1
		popnum += 1
	m = re.match(r'd', l[0])
        if m:
		# just starts with a d, this is an instruction with dependencies

		#print m.string, m.string.split('d')
		map(check, map(int, filter(lambda x:x, m.string.split('d'))))

		insns.append(GENERAL)
		found += 1
		popnum += 1

	m = re.match(r'b', l[0])
        if m:

		map(check, map(int, filter(lambda x:x, m.string[1:].split('d'))))

		# just starts with a b, then this is a branch
		insns.append(BRANCH)
		found += 1
		popnum += 1
	m = re.match(r'S', l[0])
	if m:

		map(check, map(int, filter(lambda x:x, m.string[1:].split('d'))))

		# Found a store
		insns.append(STORE)
		found += 1
		popnum += 3
	m = re.match(r'L', l[0])
	if m:

		map(check, map(int, filter(lambda x:x, m.string[1:].split('d'))))

		# Found a load
		insns.append(LOAD)
		found += 1
		popnum += 3
	m = re.match(r'[AR]', l[0])
	if m:
		# Found a sync/lock
		# Don't append anything to the instructions
		found += 1
		popnum += 3
	m = re.match(r'[B]', l[0])
	if m:
		# Found a barrier
		# Don't append anything to the instructions
		found += 1
		popnum += 4
	m = re.match(r'[CE]', l[0])
	if m:
		# Found a barrier
		# Don't append anything to the instructions
		found += 1
		popnum += 1

	if found != 1:
		print l
	assert(found == 1)
	for _ in range(popnum):
		l.popleft()

	total_insns += found
