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
sys.excepthook helper to log exceptions in the journal via systemd-coredump

This module is compatible with Python 2.x and Python 3.x. Any semi-recent
version should be supported.
"""

import sys

_sys_excepthook = None

def _write_journal_field(pipe, name, value):
    import struct

    name = name.encode('ascii')
    value = value.encode('utf-8')

    pipe.write(name + b'\n' +
               struct.pack('<Q', len(value)) + value + b'\n')

def _log_exception(etype, value, text):
    import os
    import time
    import resource
    import getpass
    import subprocess

    pid = os.getpid()
    uid = os.getuid()
    gid = os.getgid()
    timestamp = str(int(time.time()))
    rlimit_core = resource.getrlimit(resource.RLIMIT_CORE)[0]
    rlimit = str(rlimit_core)

    cmd = ['/usr/lib/systemd/systemd-coredump', '--backtrace',
           str(pid),
           str(uid),
           str(gid),
           etype.__name__,
           timestamp,
           rlimit] + sys.argv
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, universal_newlines=False)

    try:
        user = getpass.getuser()
    except Exception:
        user = str(uid)

    _write_journal_field(p.stdin, 'MESSAGE',
                         "Process {} ({}) of user {} failed with {}: {}\n\n{}"
                         .format(pid, ' '.join(sys.argv), user, etype.__name__, value, text))

    _write_journal_field(p.stdin, 'COREDUMP_PYTHON_EXECUTABLE', sys.executable)
    _write_journal_field(p.stdin, 'COREDUMP_PYTHON_VERSION', sys.version)
    try:
        ti = sys.thread_info
    except AttributeError:
        pass
    else:
        _write_journal_field(p.stdin, 'COREDUMP_PYTHON_THREAD_INFO', str(ti))
    _write_journal_field(p.stdin, 'COREDUMP_PYTHON_EXCEPTION_TYPE', etype.__name__)
    _write_journal_field(p.stdin, 'COREDUMP_PYTHON_EXCEPTION_VALUE', str(value))

    p.stdin.write(b'\n')
    p.stdin.close()
    p.wait()

def _ignore_exception(e):
    import errno

    # Ignore Ctrl-C
    # SystemExit -> this exception is not an error
    if isinstance(e, (KeyboardInterrupt, SystemExit)):
        return True

    # Ignore EPIPE: it happens all the time
    # Testcase: script.py | true, where script.py is:
    ## #!/usr/bin/python
    ## import os
    ## import time
    ## time.sleep(1)
    ## os.write(1, "Hello\n")  # print "Hello" wouldn't be the same
    #
    if isinstance(e, (IOError, OSError)) and e.errno == errno.EPIPE:
        return True

    # Ignore interactive Python and similar
    # Check for first "-" is meant to catch "-c" which appears in this case:
    ## $ python -c 'import sys; print "argv0 is:%s" % sys.argv[0]'
    ## argv0 is:-c
    if not sys.argv[0] or sys.argv[0].startswith('-'):
        return True

    return False

def _handle_exception(etype, value, tb):
    import traceback

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
    _log_exception(etype, value, text)

def systemd_coredump_handle_exception(etype, value, tb):
    """Send the exception to systemd-journald via systemd-coredump.

    After systemd-coredump is done, passes control back to call the
    original hook.
    """
    try:
        if not _ignore_exception(value):
            _handle_exception(etype, value, tb)
    except Exception:
        # Ignore any and all errors
        pass

    return _sys_excepthook(etype, value, tb)

def systemd_coredump_enabled():
    "Returns True if kernel.core_pattern sysctl invokes systemd-coredump"
    with open('/proc/sys/kernel/core_pattern', 'rt') as f:
        text = f.read()
        return text.startswith('|') and 'systemd-coredump' in text

def install(nocheck=False):
    """Install the handler function as sys.excepthook.

    The original hook is stored as _sys_excepthook.
    Failure is silent.
    """
    global _sys_excepthook
    if _sys_excepthook is not None:
        # never install ourselves twice. In particular our .pth file could be
        # installed in multiple locations (e.g. in user and system-specific
        # directories), and we'd fall into infinite recursion below.
        return
    try:
        if nocheck or systemd_coredump_enabled():
            _sys_excepthook = sys.excepthook
            sys.excepthook = systemd_coredump_handle_exception
    except Exception:
        pass

if __name__ == '__main__':
    # throw a nested test exception to show the effect
    def f():
        a = 3
        h = f
        div0 = 1 / 0
    def g():
        f()
    g()
