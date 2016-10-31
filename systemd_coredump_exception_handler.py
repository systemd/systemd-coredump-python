# -*- coding: utf-8 -*-

# Copyright (C) 2014 Red Hat, Inc.
# Copyright (C) 2016 Zbigniew Jędrzejewski-Szmek <zbyszek@in.waw.pl>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA  02110-1335  USA

"""
Module to the log Python exceptions in the journal via systemd-coredump
"""

import sys

def _log_exception(exception, text):
    import subprocess
    import time
    import os
    import resource

    pid = os.getpid()
    uid = os.getuid()
    gid = os.getgid()
    timestamp = str(int(time.time()))
    rlimit_core = resource.getrlimit(resource.RLIMIT_CORE)[0]
    rlimit = str(rlimit_core)

    cmd = ['/home/zbyszek/src/systemd-master/systemd-coredump', '--traceback',
           str(pid),
           str(uid),
           str(gid),
           exception,
           timestamp,
           rlimit] + sys.argv
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, universal_newlines=True)
    p.communicate(input=text)

def _ignore_exception(etype, value):
    return (etype in (KeyboardInterrupt, SystemExit)
            or
            etype in (IOError, OSError) and value.errno == errno.EPIPE
            or
            not sys.argv[0] or sys.argv[0][0] == '-')

def _handle_exception(etype, value, tb):
    import traceback
    import os
    import errno

    short = '{}: {}'.format(etype.__name__, value)
    long = traceback.format_exception(etype, value, tb)
    text = ''.join(long)
    if tb is not None and etype != IndentationError:
        while tb.tb_next:
            tb = tb.tb_next
        frame = tb.tb_frame
        try:
            text += ('\nLocal variables in innermost frame:\n' +
                     '\n'.join('  {}={!r}'.format(key, val)
                               for key, val in frame.f_locals.items()))
        except Exception:
            pass

    # Send data to the journal
    _log_exception(short, text)

def handle_exception(etype, value, tb):
    "Send the exception to systemd-journald via systemd-coredump."
    try:
        # Restore original exception handler
        sys.excepthook = sys.__excepthook__
        if not _ignore_exception(etype, value):
            _handle_exception(etype, value, tb)
    except Exception:
        # Silently ignore any error in this hook,
        # to not interfere with other scripts
        pass

    return sys.__excepthook__(etype, value, tb)

# install the exception handler when this module is imported
try:
    sys.excepthook = handle_exception
except Exception as e:
    pass

if __name__ == '__main__':
    # test exception raised to show the effect
    def f():
        a = 3
        h = f
        div0 = 1 / 0
    def g():
        f()
    g()
