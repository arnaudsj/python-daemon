# -*- coding: utf-8 -*-

# Copyright © 2007–2009 Robert Niederreiter, Jens Klein, Ben Finney
# Copyright © 2003 Clark Evans
# Copyright © 2002 Noah Spurrier
# Copyright © 2001 Jürgen Hermann
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Background process services library.
    """

import sys

from daemon import DaemonContext


class Service(object):
    """ Service to run a callable in a separate background process.

        The first command-line arguments is the action to take:

        * 'start': Become a daemon and call `app.run()`.
        * 'stop': Stop the daemon.
        * 'restart': Stop, then start.

        """

    def __init__(self, app):
        """ Set up the parameters of a new service.

            The `app` argument must have the following attributes:

            * `stdin`, `stdout`, `stderr`: Filesystem paths to open
              and replace the existing `sys.stdin`, `sys.stdout`,
              `sys.stderr`.

            * `pidfile_name`: Filesystem path to a file that will be
              used as the PID file for the daemon.

            * `run`: Callable that will be invoked when the daemon is
              started.
            
            """
        self.parse_args()
        self.app = app
        self.daemon_context = DaemonContext(app)
        self.daemon_context.pidfile_name = app.pidfile
        self.daemon_context.stdin = open(app.stdin, 'r')
        self.daemon_context.stdout = open(app.stdout, 'w+')
        self.daemon_context.stderr = open(app.stderr, 'w+')

    def parse_args(self, argv=None):
        """ Parse command-line arguments.
            """
        if argv is None:
            argv = sys.argv

        progname = argv[0]
        min_args = 2
        usage_exit_code = 2
        if len(argv) < min_args:
            sys.stderr.write(
                "usage: %(progname)s start|stop|restart\n" % vars())
            sys.exit(usage_exit_code)

        self.action = argv[1]
