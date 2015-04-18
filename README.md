MU0 - Simplified Processor Emulator
===================================

This is a simple emulator for the MU0 processor, written in Python 3. 
It has two registers, the program counter ``PC`` and the accumulator ``ACC``,
and it understands a language with the following instruction set:

| Opcode  | Instruction  | Effect description         |
|:--------|:-------------|:---------------------------|
| ``0000``| ``LOAD X``   | ``ACC = memory[X]``        | 
| ``0001``| ``STORE X``  | ``memory[X] = ACC``        | 
| ``0010``| ``ADD X``    | ``ACC = ACC + memory[X]``  | 
| ``0011``| ``SUB X``    | ``ACC = ACC - memory[X]``  | 
| ``0100``| ``JUMP X``   | ``pc = X``                 | 
| ``0101``| ``JGE X``    | ``if ACC>=0 pc = X``       | 
| ``0110``| ``JNE X``    | ``if ACC!=0 pc = X``       | 
| ``0111``| ``STOP``     | ``stop``                   | 

The extra assembly pseudoinstruction ``INI X Y`` is avaible, in order to load 
values into the memory. Values range is from -2<sup>11</sup> to 
2<sup>11</sup> - 1, encoded in two's complement.
All the values are statically loaded before the program start, regardless 
of their position in the code. All values and immediates must be expressed 
in hexadecimal form, preceded by the ``0x`` prefix.
The address space is 2<sup>12</sup> bit, so eventual instructions containing
a bigger address (more than 3 hex digits, including leading zeroes)
are refused as invalid.

Comments are introduced by semicolon and may follow an instruction or may
occupy an empty line. Blank lines (empty, or containing spaces only) are 
allowed.

Note that the address in the ``JUMP`` instruction is relative to the number
of the instruction (zero-based and ignoring blank lines, comment lines and
``INI`` pseudoinstruction lines) and not to the mere line number in the 
source file

Run
===
To run a program without interruptions, the emulator should be invoked as:
```bash
python mu0.py source_filename
```
To run a program step by step, pausing and showing the system status after 
each instruction, add the ``-s`` option:
```bash
python mu0.py -s source_filename
```
Here ``source_filename`` is the name of a source file written according to
the rules in the section above. A sample source file (``sample_program.asm``)
is provided with the project.

License
===================
The project is licensed under GPL 3. See [LICENSE](./LICENSE)
file for the full license.
