#!/usr/bin/env python

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

"""
    @file mu0.py
    @author Martino Pilia <martino.pilia@gmail.com>
    @date 2015-04-17
    @brief Simplified emulator for mu0 processor.
"""

import os.path
import re
import sys

def dump(memory):
    """Return a string representing the dump of the input memory.
    Note: for negative values, conversion to 2's complement is needed:
    it is done adding the (negative) value to 0x1000 (i.e. 2^12).
    """
    return '\n'.join(['  @%#0.3x: %#0.3x (dec: %d)'
        % (l, v if v >= 0 else v + 0x1000, v) # deal with negative 2's compl.
        for (l, v) in memory.items()])

source_path = ""  # path for the source file
step = False      # program is executed step by step when True
line = 1          # source file line counter
source = []       # instructions
instructions = [] # regexes to match instructions
memory = {}       # RAM memory
acc = 0           # implicit accumulator register
pc = 0            # program counter

# parse command line arguments
for s in sys.argv[1:]:
    if s == "-s":
        step = True
    elif s[0] == '-':
        print("Unrecognized option \"" + s + "\".")
        quit()
    elif source_path == "":
        source_path = s
if len(sys.argv) < 2 or source_path == "":
    print("Missing source file parameter.")
    quit()

# ensure the source file exists
if (not (os.path.exists(source_path) and os.path.isfile(source_path))):
    print("Source file not found.")
    quit()

# open source file
try:
    source_file = open(source_path, 'r')
except OSError as e:
    print("Error opening source file.")
    quit()

# create regexes to catch instructions lines or comment/blank lines
instructions = [
    re.compile('^ *(LOAD) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(STORE) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(ADD) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(SUB) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(JUMP) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(JGE) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(JNE) *(0x[0-9A-Fa-f]{1,3}) *(;+ *(.*))?$'),
    re.compile('^ *(STOP) *()?(;+ *(.*))?$'), # note the void group
    re.compile('^ *;+.*$'), # comment line
    re.compile('^ *$'),    # blank line
]

# regex for line initializing a value in memory
initializer = re.compile(
    '^(INI) *(0x[0-9A-Fa-f]{1,3}) *(0x[0-9A-Fa-f]{1,3}) *(;+.*)?$')

# get lines from file and put instructions in the array
print("### Parsing source file ...")
for source_line in source_file:
    # match initializer lines
    match = initializer.match(source_line)
    if match:
        value = int(match.group(3), 16) # get value from string
        if value > 0x7FF: # if it is negative, convert from two's complement
            value = value - 0x1000
        memory[int(match.group(2), 16)] = value # store value
        line += 1
        print("Recognized: " + source_line, end = "")
        continue
    # match instruction lines
    for regex in instructions:
        match = regex.match(source_line)
        if match:
            if len(match.groups()) != 0: # ignore non-instruction lines
                source.append(dict(
                    opc = match.group(1), # save opcode
                    imm = match.group(2), # save immediate
                    com = match.group(4), # save comment
                    line = line))         # save source line number
                print("Recognized: " + source_line, end = "")
            line += 1
            break
    # unrecognized line
    if match == None:
        print("Line " + str(line) + ": unrecognized instruction\n   " +
                source_line, end = "")
        quit()

# close source file
source_file.close()

print("\n### Memory dump before program execution:")
print(dump(memory))

# cicle for actual instructions execution
print("\n### Running the program ...")
while pc < len(source):
    opcode = source[pc]['opc']     # opcode for the current instuction
    line = str(source[pc]['line']) # line number for the current inst.
    number = pc # instruction number (i.e. PC for the current instruction)

    # check for stop instruction
    if (opcode == "STOP"):
        print("\n### Reached STOP instruction at line " + line + ".")
        break

    # immediate for the current inst., it may be safely set only now
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
    elif (opcode == "JGE"):
        if acc >= 0:
            pc = immediate
        else:
            pc += 1
    elif (opcode == "JNE"):
        if acc != 0:
            pc = immediate
        else:
            pc += 1

    # increment program counter after each non-jump instruction
    if opcode != "JUMP" and opcode != "JGE" and opcode != "JNE":
        pc += 1

    if step: # show status and ask for continuation
        print("\nExecuted line " + line +
                ", instr. %#0.3x: %s %#0.3x" % (number, opcode, immediate))
        print("Comment: " + str(source[number]['com']))
        print("  Current PC value:  %#0.3x" % (pc))
        print("  Current ACC value: %#0.3x (dec: %d)"
                % (acc if acc >= 0 else 0x1000 + acc, acc)) # 2's complement
        print("Memory dump after instruction execution:")
        print(dump(memory))
        input("Press ENTER for next instruction")

# show EOF message (if the program has not been stopped before)
if pc == len(source):
    print("\nReached end of instructions.")

# and show a memory dump
print("\n### Memory dump after program end:")
print(dump(memory))
