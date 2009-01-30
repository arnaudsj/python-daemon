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

from daemon import DaemonContext


class Service(object):
    """ Service to run a callable in a separate background process.
        """

    def __init__(self, app):
        """ Set up the parameters of a new service.
            """
        self.app = app
        self.daemon_context = DaemonContext(app)
        self.daemon_context.pidfile_name = app.pidfile
        self.daemon_context.stdin = open(app.stdin, 'r')
        self.daemon_context.stdout = open(app.stdout, 'w+')
        self.daemon_context.stderr = open(app.stderr, 'w+')
