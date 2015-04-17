#!/usr/bin/env python

##
# @file mu0.py
# @author Martino Pilia <martino.pilia@gmail.com>
# @date 2015-04-17
# @brief Simplified emulator for mu0 processor.


# Copyright (C) 2015 Martino Pilia
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os.path
import re
import sys

line = 1          # source file line counter
source = []       # instructions
instructions = [] # regexes to match instructions
memory = {}       # RAM memory
acc = 0           # implicit accumulator register
pc = 0            # program counter


# check for argument
if len(sys.argv) < 2:
    print("Missing source file parameter.\n")
    quit()

# ensure the source file exists
source_path = sys.argv[1]
if (not (os.path.exists(source_path) and os.path.isfile(source_path))):
    print("Source file not found.\n")
    quit()

# open source file
try:
    source_file = open(source_path, 'r')
except OSError as e:
    print("Error opening source file.\n")
    quit()

# create regexes to catch instructions lines or comment/blank lines
instructions = [
    re.compile('^ *(LOAD) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(STORE) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(ADD) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(SUB) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(JUMP) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(JGE) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(JNE) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$'),
    re.compile('^ *(STOP) *(;+.*)?$'),
    re.compile('^ *;+.*$'), # comment line
    re.compile('^ *$'),   # blank line
]

# regex for line initializing a value in memory
initializer = re.compile(
    '^(INI) *(0x[0-9A-Fa-f]{1,3}) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$')

# get lines from file and put instructions in the array
for source_line in source_file:
    # match initializer lines
    match = initializer.match(source_line)
    if match:
        memory[int(match.group(2), 16)] = int(match.group(3), 16)
        line += 1
        print("Recognized: " + source_line)
        continue
    # match instruction lines
    for regex in instructions:
        match = regex.match(source_line)
        if match:
            if len(match.groups()) != 0: # ignore non-instruction lines
                source.append(dict(
                    opc = match.group(1), # save opcode
                    imm = match.group(2), # save immediate
                    line = line))         # save source line number
            line += 1
            print("Recognized: " + source_line)
            break
    # unrecognized line
    if match == None:
        print("Line " + str(line) + ": unrecognized instruction\n   " +
                source_line)
        quit()

# close source file
source_file.close()

# cicle for actual instructions execution
print("### Running the program ...")
while pc < len(source):
    opcode = source[pc]['opc']     # opcode for the current instuction
    line = str(source[pc]['line']) # line number for the current inst.

    # check for stop instruction
    if (opcode == "STOP"):
        print("Reached STOP instruction at line " + line + ".")
        break

    # immediate for the current inst., it may be set safely only now
    immediate = int(source[pc]['imm'], 16)

    # access instructions (potentially invalid location)
    try:
        if (opcode == "LOAD"):
            acc = memory[immediate]
        elif (opcode == "ADD"):
            acc += memory[immediate]
        elif (opcode == "SUB"):
            acc -= memory[immediate]
    except KeyError as e:
        print("Error at line " + line + ": invalid memory access.")
        quit()

    # other instructions
    if (opcode == "STORE"):
        memory[immediate] = acc
    elif (opcode == "JUMP"):
        pc = immediate
        continue
    elif (opcode == "JGE"):
        if acc >= 0:
            pc = immediate
            continue
    elif (opcode == "JNE"):
        if acc != 0:
            pc = immediate
            continue

    pc += 1 # increment program counter after each non-jump instruction

# show EOF message (if the program has not been stopped before)
if pc == len(source):
    print("\nReached end of instructions.")

# and show a memory dump
print("\nMemory dump after program end:")
print('\n'.join(['@0x%x: 0x%x' % (loc, val) for (loc, val) in memory.items()]))
