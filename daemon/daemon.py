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

import os
import sys
import time
import resource
import errno
from signal import SIGTERM


def prevent_core_dump():
    """ Prevent this process from generating a core dump.

        Sets the soft and hard limits for core dump size to zero. On
        Unix, this prevents the process from creating core dump
        altogether.

        """
    core_resource = resource.RLIMIT_CORE

    # Ensure the resource limit exists on this platform, by requesting
    # its current value
    core_limit_prev = resource.getrlimit(core_resource)

    # Set hard and soft limits to zero, i.e. no core dump at all
    core_limit = (0, 0)
    resource.setrlimit(core_resource, core_limit)


def detach_process_context():
    """ Detach the process context from parent and session.

        Detach from the parent process and session group, allowing the
        parent to exit while this process continues running.

        Reference: “Advanced Programming in the Unix Environment”,
        section 13.3, by W. Richard Stevens, published 1993 by
        Addison-Wesley.
    
        """
    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            sys.exit(0)
    except OSError, e:
        msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        sys.exit(1)


def pidfile_exists(pidfile_name):
    """ Return True if the named PID file exists on the filesystem.
        """
    result = os.path.exists(pidfile_name)
    return result


def read_pid_from_pidfile(pidfile_name):
    """ Read the PID recorded in the named PID file.

        Read and return the numeric PID recorded as text in the named
        PID file. If the PID file cannot be read, return ``None``.

        """
    try:
        pidfile = open(pidfile_name, 'r')
        pid = int(pidfile.read().strip())
        pidfile.close()
    except IOError:
        pid = None

    return pid


def abort_if_existing_pidfile(pidfile_name):
    """ Exit the program if the named PID file exists.

        The presence of the specified PID file indicates another
        instance of this daemon program is already running, so we exit
        this program in that case.

        """
    if pidfile_exists(pidfile_name):
        mess = (
            "Aborting: PID file '%(pidfile_name)s' exists.\n"
            ) % vars()
        sys.stderr.write(mess)
        sys.exit(1)


def abort_if_no_existing_pidfile(pidfile_name):
    """ Exit the program if the named PID file does not exist.

        The specified PID file should be created when we start and
        should continue to be readable while the daemon runs, so
        failure indicates a fatal error.

        """
    if not pidfile_exists(pidfile_name):
        mess = (
            "Aborting: could not read PID file '%(pidfile_name)s'.\n"
            ) % vars()
        sys.stderr.write(mess)
        sys.exit(1)


def write_pid_to_pidfile(pidfile_name):
    """ Write the PID in the named PID file.

        Get the numeric process ID (“PID”) of the current process
        and write it to the named file as a line of text.

        """
    pidfile = open(pidfile_name, 'w')

    pid = os.getpid()
    line = "%(pid)d\n" % vars()
    pidfile.write(line)


def remove_existing_pidfile(pidfile_name):
    """ Remove the named PID file if it exists.

        Removing a PID file that doesn't already exist puts us in the
        desired state, so we ignore the condition if the file does not
        exist.

        """
    try:
        os.remove(pidfile_name)
    except OSError, exc:
        if exc.errno == errno.ENOENT:
            pass
        else:
            raise


def redirect_stream(system_stream, target_stream):
    """ Redirect a system stream to a specified file.

        `system_stream` is a standard system stream such as
        ``sys.stdout``. `target_stream` is an open file object that
        should replace the corresponding system stream object.

        """
    os.dup2(target_stream.fileno(), system_stream.fileno())


class DaemonContext(object):
    """ Context for turning the current program into a daemon process.

        Implements the well-behaved daemon behaviour defined in PEP
        [no number yet].

        """
    
    """Class Daemon is used to run any routine in the background on unix
    environments as daemon.
    
    There are several things to consider:
    
    * The instance object MUST provide global file descriptors for
      (and named as):
        -stdin
        -stdout
        -stderr
    
    * The instance object MUST provide a global (and named as) pidfile.
    """

    UMASK = 0
    WORKDIR = "."
    instance = None
    startmsg = 'started with pid %s'

    def __init__(
        self,
        instance=None,
        pidfile_name=None,
        stdin=None,
        stdout=None,
        stderr=None,
        ):
        self.instance = instance
        self.pidfile_name = pidfile_name
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def start(self):
        """ Become a daemon process. """

        abort_if_existing_pidfile(self.instance.pidfile)

        detach_process_context()

        os.chdir(self.WORKDIR)
        os.umask(self.UMASK)

        prevent_core_dump()

        if not self.instance.stderr:
            self.instance.stderr = self.instance.stdout

        si = open(self.instance.stdin, 'r')
        so = open(self.instance.stdout, 'a+')
        se = open(self.instance.stderr, 'a+', 0)

        pid = str(os.getpid())

        sys.stderr.write("\n%s\n" % self.startmsg % pid)
        sys.stderr.flush()

        if self.instance.pidfile:
            write_pid_to_pidfile(self.instance.pidfile)

        redirect_stream(sys.stdin, si)
        redirect_stream(sys.stdout, so)
        redirect_stream(sys.stderr, se)

    def stop(self):
        """ Stop the running daemon process. """
        abort_if_no_existing_pidfile(self.instance.pidfile)
        remove_existing_pidfile(self.instance.pidfile)

    def startstop(self):
        """Start/stop/restart behaviour.
        """
        if len(sys.argv) > 1:
            action = sys.argv[1]
            if 'stop' == action:
                self.stop()
                sys.exit(0)
                return
            if 'start' == action:
                self.start()
                return
            if 'restart' == action:
                self.stop()
                self.start()
                return
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
