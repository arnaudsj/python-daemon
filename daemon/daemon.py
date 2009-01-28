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


def read_pid_from_lockfile(lockfile_name):
    """ Read the PID recorded in the named lockfile.

        Read and return the numeric PID recorded as text in the named
        lockfile. If the lockfile cannot be read, return ``None``.

        """
    try:
        lockfile = file(lockfile_name, 'r')
        pid = int(lockfile.read().strip())
        lockfile.close()
    except IOError:
        pid = None

    return pid

def abort_if_lockfile_exists(lockfile_name):
    """ Exit the program if the named lockfile exists.

        The presence of the specified lockfile indicates another
        instance of this daemon program is already running, so we exit
        this program in that case.

        """
    existing_pid = read_pid_from_lockfile(lockfile_name)
    if existing_pid:
        mess = (
            "Aborting: lock file '%(lockfile_name)s' exists.\n"
            ) % vars()
        sys.stderr.write(mess)
        sys.exit(1)

def write_pid_to_lockfile(lockfile_name):
    """ Write the PID in the named lockfile.

        Get the current numeric process ID (“pid”) and write it to
        the named file as a line of text.

        """
    lockfile = file(lockfile_name, 'w')

    pid = os.getpid()
    line = "%(pid)d\n" % vars()
    lockfile.write(line)


class Daemon(object):
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

    def __init__(self, instance):
        self.instance = instance

    def start(self):
        """ Become a daemon process. """

        abort_if_lockfile_exists(self.instance.pidfile)

        detach_process_context()

        os.chdir(self.WORKDIR)
        os.umask(self.UMASK)

        prevent_core_dump()

        if not self.instance.stderr:
            self.instance.stderr = self.instance.stdout

        si = file(self.instance.stdin, 'r')
        so = file(self.instance.stdout, 'a+')
        se = file(self.instance.stderr, 'a+', 0)

        pid = str(os.getpid())

        sys.stderr.write("\n%s\n" % self.startmsg % pid)
        sys.stderr.flush()

        if self.instance.pidfile:
            write_pid_to_lockfile(self.instance.pidfile)

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def startstop(self):
        """Start/stop/restart behaviour.
        """
        if len(sys.argv) > 1:
            action = sys.argv[1]
            pid = read_pid_from_lockfile(self.instance.pidfile)
            if 'stop' == action or 'restart' == action:
                if not pid:
                    mess = "Could not stop, pid file '%s' missing.\n"
                    sys.stderr.write(mess % pidfile)
                    sys.exit(1)
                try:
                    while 1:
                        os.kill(pid, SIGTERM)
                        time.sleep(1)
                except OSError, err:
                    err = str(err)
                    if err.find("No such process") > 0:
                        os.remove(self.instance.pidfile)
                        if 'stop' == action:
                            sys.exit(0)
                        action = 'start'
                        pid = None
                    else:
                        print str(err)
                        sys.exit(1)
            if 'start' == action:
                self.start()
                return
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
