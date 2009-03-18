# -*- coding: utf-8 -*-

# Copyright © 2009 Ben Finney <ben+python@benfinney.id.au>
# Copyright © 2006 Robert Niederreiter
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Library to implement a well-behaved Unix daemon process

    This library implements PEP [no number yet], Standard daemon
    process library.

    A well-behaved Unix daemon process is tricky to get right, but the
    required steps are much the same for every daemon program. An
    instance of the `DaemonContext` holds the behaviour and configured
    process environment for the program; use the instance as a context
    manager to enter a daemon state.

    Simple example of usage::

        import daemon

        from spam import do_main_program

        with daemon.DaemonContext() as daemon_context:
            do_main_program()

    """

from daemon import DaemonContext


version = "1.4.3"
