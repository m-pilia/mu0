#!/usr/bin/env python

# Copyright (C) 2015 Martino Pilia (where not differently specified)
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
    @file mu0_graphic.py
    @author Martino Pilia <martino.pilia@gmail.com>
    @date 2015-05-12
    @brief Simplified emulator for mu0 processor.
"""

import io
import os.path
import re
import sys

# tk support
try:
    import tkinter as tk
    from tkinter import filedialog
    from tkinter import *
except ImportError:
    print("Tk support missing")
    quit()

class FileNotFound(RuntimeError):
    """ Exception to be risen when the source file is not found.
    """
    pass

class SourceSyntaxError(RuntimeError):
    """ Exception to be risen when the source file contains a syntax error.
    """
    def __init__(self, line = 0, line_content = None):
        """
            line: line number
            line_content: text contained in the line causing the exception
        """
        self.line = line
        self.line_content = line_content

class ExecutionComplete(Exception):
    """ Exception risen when the program reaches the end of its execution.
    """
    def __init__(self, message = None):
        self.message = message

# thanks to Bryan Oakley on StackOverflow: http://stackoverflow.com/a/16375233
class TextLineNumbers(tk.Canvas):
    """ Class defining the canvas containing the line numbers for the text box.
    """
    def __init__(self, *args, **kwargs):
        tk.Canvas.__init__(self, *args, **kwargs)
        self.textwidget = None

    def attach(self, text_widget):
        """ Attach the widget to a text widget.
        """
        self.textwidget = text_widget

    def redraw(self, *args):
        """ Redraw line numbers according to the text widget content.
        """
        self.delete("all")

        i = self.textwidget.index("@0,0") # line counter
        while True:
            dline = self.textwidget.dlineinfo(i) # get info on the text line
            if dline is None:
                break
            y = dline[1] # get vertical line start
            linenum = str(i).split(".")[0] # get line number
            self.create_text(2, y, anchor = "nw", text = linenum)
            i = self.textwidget.index("%s+1line" % i) # update line counter

# thanks to Bryan Oakley on StackOverflow: http://stackoverflow.com/a/16375233
class CustomText(tk.Text):
    """ Subclass of the text widget, adding the generation of an event
        when the content of the text box is changed.
    """
    def __init__(self, *args, **kwargs):
        tk.Text.__init__(self, *args, **kwargs)

        # make the widget generate an event when the text is changed
        self.tk.eval('''
            proc widget_proxy {widget widget_command args} {

                # call the real tk widget command with the real args
                set result [uplevel [linsert $args 0 $widget_command]]

                # generate the event for certain types of commands
                if {([lindex $args 0] in {insert replace delete}) ||
                    ([lrange $args 0 2] == {mark set insert}) ||
                    ([lrange $args 0 1] == {xview moveto}) ||
                    ([lrange $args 0 1] == {xview scroll}) ||
                    ([lrange $args 0 1] == {yview moveto}) ||
                    ([lrange $args 0 1] == {yview scroll})} {

                    event generate  $widget <<Change>> -when tail
                }

                # return the result from the real widget command
                return $result
            }
            ''')

        self.tk.eval('''
            rename {widget} _{widget}
            interp alias {{}} ::{widget} {{}} widget_proxy {widget} _{widget}
        '''.format(widget = str(self)))

# thanks to Bryan Oakley on StackOverflow: http://stackoverflow.com/a/16375233
class NumberedText(tk.Frame):
    """ Class defining a Frame containing both the textbox and its related
        line numbers canvas on the left.
    """
    def __init__(self, *args, **kwargs):
        tk.Frame.__init__(self, *args, **kwargs)
        self.text = CustomText(self)
        self.linenumbers = TextLineNumbers(self, width = 30)
        self.linenumbers.attach(self.text)
        self.linenumbers.pack(side = "left", fill = "y")
        self.text.pack(side="right", fill = "both", expand = True)

        # bind events related to text change to the handler for the
        # line numbers redraw
        self.text.bind("<<Change>>", self._on_change)
        self.text.bind("<Configure>", self._on_change)

    def _on_change(self, event):
        """ Handler for the text content change.
        """
        self.linenumbers.redraw()

class Application(tk.Frame):
    """ Class defining the main window frame for the program.
    """
    def __init__(self, master=None):
        tk.Frame.__init__(self, master)
        self.pack()

        # initialize the status variables of the application
        self.resetProgramStatus();
        self.outputText = StringVar()
        self.currentFileName = None

        # create regexes to catch instructions lines or comment/blank lines
        self.instructions_re = [
            re.compile(
                '^[ \t]*' + # leading whitespace
                '(LOAD|LDA|STORE|STO|ADD|SUB|JUMP|JMP|JGE|JNE)' +
                # instruction name
                '[ \t]*' + # whitespace
                '(0x[0-9A-Fa-f]{1,3})' + # operand
                '[ \t]*' + # whitespace
                '(?:;+[ \t]*(.*))?$', # comment
                flags = re.I), # ignore case
            re.compile(
                '^[ \t]*' +
                '(STOP)' +
                '[ \t]*' +
                '()?' + # void group, to have the same format as the above re
                '(?:;+[ \t]*(.*))?$',
                flags = re.I),
            re.compile('^[ \t]*;+.*$'), # comment line
            re.compile('^[ \t]*$'),    # blank line
        ]
        # regex for a line initializing a value in memory
        self.initializer = re.compile(
                '^[ \t]*' +
                '(INI)' +
                '[ \t]*' +
                '(0x[0-9A-Fa-f]{1,3})' + # location
                '[ \t]*' +
                '(0x[0-9A-Fa-f]{1,3})' + # value
                '[ \t]*' +
                '(;+[ \t]*(.*))?$',
                flags = re.I)

        # create the widgets in the window
        self.createWidgets()

    def dump(self):
        """Return a string representing the dump of the input memory.

        Note: for negative values, conversion to 2's complement is needed:
        it is done adding the (negative) value to 0x1000 (i.e. 2^12).
        """
        return '\n'.join(['  @%#0.3x: %#0.3x (dec: %d)'
            % (l, v if v >= 0 else v + 0x1000, v) # 2's complement
            for (l, v) in self.memory.items()])

    def parseSource(self, source_file):
        """ Parse the source file whose path is passed as a parameter.
        """

        self.line = 1 # source file line counter
        self.instructions = [] # instructions
        self.memory = {}       # RAM memory

        # get lines from file and put instructions in the array
        print("### Parsing source file ...")
        for source_line in source_file:
            source_line = source_line.rstrip() # strip final newline char
            # match initializer lines
            match = self.initializer.match(source_line)
            if match:
                value = int(match.group(3), 16) # get value from string
                if value > 0x7FF: # two's complement when negative
                    value = value - 0x1000
                self.memory[int(match.group(2), 16)] = value # store value
                self.line += 1
                print("Recognized: " + source_line)
                continue
            # match instruction lines
            for regex in self.instructions_re:
                match = regex.match(source_line)
                if match:
                    if len(match.groups()) != 0: # ignore non-instruction lines
                        self.instructions.append(dict(
                            opc = match.group(1), # save opcode
                            imm = match.group(2), # save immediate
                            com = match.group(3), # save comment
                            line = self.line))         # save source line number
                        print("Recognized: " + source_line)
                    self.line += 1
                    break
            # unrecognized line
            if match == None:
                print("Line " + str(self.line) +
                        ": unrecognized instruction\n   " +
                        source_line)
                raise SourceSyntaxError(self.line, source_line)

    def runInstruction(self):
        """ Run the next instruction in the current program.
        """
        if self.pc >= len(self.instructions):
            raise ExecutionComplete(
                    "End of program reached." +
                    "\nMemory dump after program end:" +
                    self.dump())
        else:
            # opcode for current instr.
            opcode = self.instructions[self.pc]['opc']
            # line for current instr.
            self.line = str(self.instructions[self.pc]['line'])
            number = self.pc # PC for the current instruction

            # check for stop instruction
            if (opcode == "STOP"):
                raise ExecutionComplete(
                        "Reached STOP instruction at line "
                        + self.line + "." +
                        "\nMemory dump after program end:" +
                        self.dump())

            # immediate for the current inst., it may be safely set only now
            immediate = int(self.instructions[self.pc]['imm'], 16)

            # access instructions (potentially invalid location)
            try:
                if (opcode == "LOAD" or opcode == "LDA"):
                    self.acc = self.memory[immediate]
                elif (opcode == "ADD"):
                    self.acc += self.memory[immediate]
                elif (opcode == "SUB"):
                    self.acc -= self.memory[immediate]
            except KeyError as e:
                print("Line " + self.line + ": uninitialized memory access.")
                quit()

            # other instructions
            if (opcode == "STORE" or opcode == "STO"):
                self.memory[immediate] = self.acc
            elif (opcode == "JUMP" or opcode == "JMP"):
                self.pc = immediate
            elif (opcode == "JGE"):
                if self.acc >= 0:
                    self.pc = immediate
                else:
                    self.pc += 1
            elif (opcode == "JNE"):
                if self.acc != 0:
                    self.pc = immediate
                else:
                    self.pc += 1

            # increment program counter after each non-jump instruction
            if opcode != "JUMP" and opcode != "JGE" and opcode != "JNE":
                self.pc += 1

            # set output text message
            self.outputText.set(
                "Executed line " + self.line +
                ", instr. %#0.3x: %s %#0.3x" % (number, opcode, immediate) +
                "\nComment: " + str(self.instructions[number]['com']) +
                "\n  Current PC value:  %#0.3x" % (self.pc) +
                "\n  Current ACC value: %#0.3x (dec: %d)"
                    % (self.acc if self.acc >= 0 else 0x1000 + self.acc,
                        self.acc) + # 2's complement
                "\nMemory dump after instruction execution:" +
                self.dump())
            return 1

    def createWidgets(self):
        """ Create the widgets in the application window.
        """
        # text box to interact with the source file
        self.textBox = NumberedText(
                self,
                width = 80,
                height = 25)
        self.textBox.text.insert('1.0',
                "; Write your asm source here\n" +
                "; or load a source file with the button on the right.\n" +
                "; You can edit and save your source files.\n" +
                ";\n" +
                "; To test a program, use the \"Run all\" button.\n" +
                "; To run your program one instruction a time, use the " +
                "\"Run step\" button.\n" +
                "; and then use the \"Next\" button to run the next " +
                "instruction,\n" +
                "; or \"Stop\" to stop the execution\n")
        self.textBox.grid(row = 0, column = 0, rowspan = 9)

        # scrollbar for the source text box
        self.scrollBar = tk.Scrollbar(
                self,
                command = self.textBox.text.yview)
        self.textBox.text["yscrollcommand"] = self.scrollBar.set
        self.scrollBar.grid(row = 0, column = 1, rowspan = 9, sticky = 'nsew')

        # label for the execution output
        self.terminal = tk.Label(
                self,
                textvariable = self.outputText,
                width = 60,
                fg = "#FFFFFF",
                bg = "#000000",
                justify = LEFT,
                anchor = NW) # align text to up-left corner
        self.terminal.grid(row = 9, column = 0, columnspan = 2)
        self.outputText.set("\n\n\n\n\n\n\n\n")

        # button for source file opening
        self.openButton = tk.Button(
                self,
                text = "Load file",
                command = self.openFile,
                width = 8)
        self.openButton.grid(row = 0, column = 2)

        # button for source file saving
        self.saveButton = tk.Button(
                self,
                text = "Save",
                command = self.saveFile,
                state = DISABLED)
        self.saveButton.grid(row = 1, column = 2)
        self.saveButton.config(width = 8)

        # button for source file saving with name
        self.saveAsButton = tk.Button(
            self,
            text = "Save as...",
            command = self.saveAsFile)
        self.saveAsButton.grid(row = 2, column = 2)
        self.saveAsButton.config(width = 8)

        # button to run the whole program
        self.runAllButton = tk.Button(
                self,
                text = "Run all",
                command = self.runAll)
        self.runAllButton.grid(row = 3, column = 2)
        self.runAllButton.config(width = 8)

        # button to run the program step by step
        self.runButton = tk.Button(
                self,
                text = "Run step",
                command = self.runProgram)
        self.runButton.grid(row = 4, column = 2)
        self.runButton.config(width = 8)

        # button to execute the next instruction when running step by step
        self.nextButton = tk.Button(
                self,
                text = "Next",
                command = self.runNext,
                state = DISABLED)
        self.nextButton.grid(row = 5, column = 2)
        self.nextButton.config(width = 8)

        # button to stop current execution
        self.stopButton = tk.Button(
                self,
                text = "Stop",
                command = self.stopProgram,
                state = DISABLED)
        self.stopButton.grid(row = 6, column = 2)
        self.stopButton.config(width = 8)

        # button to quit the program
        self.quitButton = tk.Button(
                self,
                text = "Quit",
                command = root.destroy)
        self.quitButton.grid(row = 7, column = 2)
        self.quitButton.config(width = 8)

    def openFile(self):
        """ Open a source file and copy its content inside the text box.
        """
        self.currentFileName = tk.filedialog.askopenfilename()
        if (not self.currentFileName):
            # TODO
            return

        # open source file
        try:
            source_file = open(self.currentFileName, 'r')
        except OSError:
            print("Error opening source file.")
            raise OSError('Error opening source file.')

        # put its content in the textbox
        self.textBox.text.delete('1.0', END)
        for line in source_file:
            self.textBox.text.insert(END, line)
        source_file.close() # close file

        self.saveButton["state"] = 'normal'

    def saveFile(self):
        """ Save the content of the text box in the last opened file.
        """
        # open destination file
        try:
            dest_file = open(self.currentFileName, 'w')
        except OSError:
            print("Error opening destination file.")
            raise OSError('Error opening destination file.')

        dest_file.write(self.textBox.text.get('1.0', END)) # write content
        dest_file.close()

    def saveAsFile(self):
        """ Save the content of the text box in a user selected file.
        """
        fileName = tk.filedialog.asksaveasfilename()
        if(not fileName):
            # TODO
            return
        self.currentFileName = fileName
        self.saveFile()

    def runProgram(self):
        """ Start the step by step execution of a program.
        """
        source = io.StringIO(self.textBox.text.get('1.0', END))
        self.parseSource(source)
        # change button state
        self.runButton["state"] = DISABLED
        self.textBox.text["state"] = DISABLED
        self.stopButton["state"] = 'normal'
        self.nextButton["state"] = 'normal'
        # run first instruction
        try:
            self.runNext()
        except ExecutionComplete as e:
            self.outputText.set(e.message)
            self.stopProgram()

    def resetProgramStatus(self):
        """ Reset the values of the status variables.
        """
        self.line = 1          # source file line counter
        self.instructions = [] # instructions
        self.memory = {}       # RAM memory
        self.acc = 0           # implicit accumulator register
        self.pc = 0            # program counter

    def stopProgram(self):
        """ Halt the execution of a program.
        """
        self.resetProgramStatus();
        self.runButton["state"] = 'normal'
        self.textBox.text["state"] = 'normal'
        self.stopButton["state"] = DISABLED
        self.nextButton["state"] = DISABLED

    def runNext(self):
        """ Run the next instruction of the program.
        """
        try:
            self.runInstruction()
        except ExecutionComplete as e:
            self.outputText.set(e.message)
            self.stopProgram()

    def runAll(self):
        """ Run the whole program.
        """
        if self.pc == 0:
            try:
                self.runProgram()
            except ExecutionComplete as e:
                self.outputText.set(e.message)
                self.stopProgram()
        while True:
            try:
                self.runInstruction()
            except ExecutionComplete as e:
                self.outputText.set(e.message)
                self.stopProgram()
                break

# application entry point
root = tk.Tk()
root.title("MU0 - simple processor emulator")
root.geometry('700x500')
app = Application(master=root)
app.mainloop()
