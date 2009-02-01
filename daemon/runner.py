# -*- coding: utf-8 -*-

# daemon/runner.py
#
# Copyright © 2007–2009 Robert Niederreiter, Jens Klein, Ben Finney
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

from daemon import DaemonContext


class Runner(object):
    """ Controller for a callable running in a separate background process.

        The first command-line arguments is the action to take:

        * 'start': Become a daemon and call `app.run()`.
        * 'stop': Stop the daemon.
        * 'restart': Stop, then start.

        """

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
        self.daemon_context = DaemonContext(app)
        self.daemon_context.pidfile_path = app.pidfile_path
        self.daemon_context.stdin = open(app.stdin_path, 'r')
        self.daemon_context.stdout = open(app.stdout_path, 'w+')
        self.daemon_context.stderr = open(app.stderr_path, 'w+')

    def _usage_exit(self, argv):
        """ Emit a usage message, then exit.
            """
        progname = argv[0]
        usage_exit_code = 2
        sys.stderr.write(
            "usage: %(progname)s start|stop|restart\n" % vars())
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
        valid_actions = ['start', 'stop', 'restart']
        if self.action not in valid_actions:
            self._usage_exit(argv)
