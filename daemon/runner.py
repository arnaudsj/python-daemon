# -*- coding: utf-8 -*-

# daemon/runner.py
#
# Copyright © 2009 Ben Finney <ben+python@benfinney.id.au>
# Copyright © 2007–2008 Robert Niederreiter, Jens Klein
# Copyright © 2003 Clark Evans
# Copyright © 2002 Noah Spurrier
# Copyright © 2001 Jürgen Hermann
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Daemon runner library.
    """

import sys
import os
import signal
import errno

import pidlockfile

from daemon import DaemonContext


class DaemonRunner(object):
    """ Controller for a callable running in a separate background process.

        The first command-line argument is the action to take:

        * 'start': Become a daemon and call `app.run()`.
        * 'stop': Close the daemon context.
        * 'restart': Stop, then start.

        """

    start_message = "started with pid %(pid)d"

    def __init__(self, app):
        """ Set up the parameters of a new runner.

            The `app` argument must have the following attributes:

            * `stdin_path`, `stdout_path`, `stderr_path`: Filesystem
              paths to open and replace the existing `sys.stdin`,
              `sys.stdout`, `sys.stderr`.

            * `pidfile_path`: Filesystem path to a file that will be
              used as the PID file for the daemon.

            * `run`: Callable that will be invoked when the daemon is
              started.
            
            """
        self.parse_args()
        self.app = app
        self.daemon_context = DaemonContext()
        self.daemon_context.stdin = open(app.stdin_path, 'r')
        self.daemon_context.stdout = open(app.stdout_path, 'w+')
        self.daemon_context.stderr = open(
            app.stderr_path, 'w+', buffering=0)

        self.pidfile = make_pidlockfile(app.pidfile_path)
        self.daemon_context.pidfile = self.pidfile

    def _usage_exit(self, argv):
        """ Emit a usage message, then exit.
            """
        progname = os.path.basename(argv[0])
        usage_exit_code = 2
        action_usage = "|".join(self.action_funcs.keys())
        sys.stderr.write(
            "usage: %(progname)s %(action_usage)s\n" % vars())
        sys.exit(usage_exit_code)

    def parse_args(self, argv=None):
        """ Parse command-line arguments.
            """
        if argv is None:
            argv = sys.argv

        min_args = 2
        if len(argv) < min_args:
            self._usage_exit(argv)

        self.action = argv[1]
        if self.action not in self.action_funcs:
            self._usage_exit(argv)

    def _start(self):
        """ Open the daemon context and run the application.
            """
        if self.pidfile.is_locked():
            pidfile_path = self.pidfile.path
            if pidfile_lock_is_stale(self.pidfile):
                self.pidfile.break_lock()
            else:
                error = SystemExit(
                    "PID file %(pidfile_path)r already locked"
                    % vars())
                raise error

        self.daemon_context.open()

        pid = os.getpid()
        message = self.start_message % vars()
        sys.stderr.write("%(message)s\n" % vars())
        sys.stderr.flush()

        self.app.run()

    def _stop(self):
        """ Close the daemon context.
            """
        if not self.pidfile.is_locked():
            pidfile_path = self.pidfile.path
            error = SystemExit(
                "PID file %(pidfile_path)r not locked"
                % vars())
            raise error

        if pidfile_lock_is_stale(self.pidfile):
            self.pidfile.break_lock()
        else:
            pid = self.pidfile.read_pid()
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError, exc:
                error = SystemExit(
                    "Failed to terminate %(pid)d: %(exc)s"
                    % vars())
                raise error

    def _restart(self):
        """ Stop, then start.
            """
        self._stop()
        self._start()

    action_funcs = {
        'start': _start,
        'stop': _stop,
        'restart': _restart,
        }

    def do_action(self):
        """ Perform the requested action.
            """
        func = self.action_funcs.get(self.action, None)
        if func is None:
            raise ValueError("Unknown action: %(action)r" % vars(self))
        func(self)


def make_pidlockfile(path):
    """ Make a PIDLockFile instance with the given filesystem path. """
    lockfile = None

    if path is not None:
        if not isinstance(path, basestring):
            error = ValueError("Not a filesystem path: %(path)r" % vars())
            raise error
        if not os.path.isabs(path):
            error = ValueError("Not an absolute path: %(path)r" % vars())
            raise error
        lockfile = pidlockfile.PIDLockFile(path)

    return lockfile

def pidfile_lock_is_stale(pidfile):
    """ Determine whether a PID file refers to a nonexistent PID. """
    result = False

    pidfile_pid = pidfile.read_pid()
    try:
        os.kill(pidfile_pid, signal.SIG_DFL)
    except OSError, exc:
        if exc.errno == errno.ESRCH:
            # The specified PID does not exist
            result = True

    return result
