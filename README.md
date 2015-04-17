MU0 - Simplified Processor Emulator
===================================

This is a simple emulator for the MU0 processor, written in Python 3. 
It understands an assembly language with the following instruction set:

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

The extra assembly instruction ``INI X Y`` is avaible, in order to load 
values into the memory. All the values are statically loaded before the 
program start, independently of their position in the code. All values and
immediates must be expressed in hexadecimal form, preceded by the ``0x``
prefix.

Comments are introduced by semicolon and may follow an instruction or may
occupy an empty line. Blank lines (empty, or containing spaces only) are allowed.

Note that the address in the ``JUMP`` instruction is relative to the number
of the instruction in the source file (ignoring blank and comment lines).

Run
===
The program is launched as:
```bash
python mu0.py source_filename
```
where ``source_filename`` is the name of a source file written according to
the rules in the section above. A sample source file (``sample_program.asm``)
is provided with the project.

License
===================
The project is licensed under GPL 3. See [LICENSE](./LICENSE)
file for the full license.
