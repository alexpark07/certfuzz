'''
Created on Oct 25, 2010

Provides a wrapper around gdb.

@organization: cert.org
'''
from string import Template
import tempfile
import os
import logging

from .registration import register
from . import DebuggerError

from .debugger_base import Debugger
from .output_parsers.gdbfile import GDBfile
from ..fuzztools import subprocess_helper as subp

logger = logging.getLogger(__name__)

class GDB(Debugger):
    _platform = 'Linux'
    _key = 'gdb'
    _ext = 'gdb'

    def __init__(self, program, cmd_args, outfile_base, timeout, killprocname, template=None, exclude_unmapped_frames=True, keep_uniq_faddr=False, **options):
        super(self.__class__, self).__init__(program, cmd_args, outfile_base, timeout, killprocname, **options)
        self.template = template
        self.exclude_unmapped_frames = exclude_unmapped_frames
        self.keep_uniq_faddr = keep_uniq_faddr

    def _get_cmdline(self):
        self._create_input_file()
        if not os.path.exists(self.input_file):
            raise DebuggerError('Input file does not exist: %s', self.input_file)

        args = [self.debugger_app(), '-batch', '-command', self.input_file]
        logger.log(5, "GDB command: [%s]", ' '.join(args))
        return args

    def _create_input_file(self):
        # short-circuit if input_file already exists
        if os.path.exists(self.input_file):
            logger.log(5, "GDB input file already exists at %s", self.input_file)
            return

        if not self.template:
            raise DebuggerError('Debugger template is not defined')

        logger.debug('Template:%s', os.path.abspath(self.template))
        if not os.path.exists(self.template):
            raise DebuggerError('No template found at %s', self.template)

        template = open(self.template, 'r').read()
        s = Template(template)

        cmdargs = ' '.join(self.cmd_args)
        new_script = s.safe_substitute(PROGRAM=self.program, CMD_ARGS=cmdargs)

        (fd, f) = tempfile.mkstemp(text=True)
        try:
            os.write(fd, new_script)
        finally:
            os.close(fd)

        self.input_file = f
        if os.path.exists(self.input_file):
            logger.log(5, "GDB input file is %s", self.input_file)
        else:
            logger.warning("Failed to create GDB input file %s", self.input_file)

    def _remove_temp_file(self):
        os.remove(self.input_file)
        if os.path.exists(self.input_file):
            logger.warning("Failed to delete %s", self.input_file)

    def debugger_app(self):
        '''
        Returns the name of the debugger application to use in this class
        '''
        return 'gdb'

    def debugger_test(self):
        '''
        Returns a command line (as list) that can be run via subprocess.call
        to confirm whether the debugger is on the path.
        '''

        return [self.debugger_app(), '--version']

    def go(self):
        '''
        Generates gdb output for <program> <cmd_args> into <outfile>.
        If gdb fails to complete before <timeout>,
        attempt to _kill gdb and <killprocname>.

        @return: a GDBfile object with the parsed results
        '''
        # build the command line in a separate function so we can unit test
        # it without actually running the command
        cmdline = self._get_cmdline()
        subp.run_with_timer(cmdline, self.timeout, self.killprocname, stdout=self.outfile)

        self._remove_temp_file()
        return GDBfile(self.outfile, self.exclude_unmapped_frames, self.keep_uniq_faddr)

register(GDB)
