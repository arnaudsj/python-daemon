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
    """ Prevent this process from generating a core dump. """
    core_resource = resource.RLIMIT_CORE

    # Ensure the resource limit exists on this platform, by requesting
    # its current value
    core_limit_prev = resource.getrlimit(core_resource)

    # Set hard and soft limits to zero, i.e. no core dump at all
    core_limit = (0, 0)
    resource.setrlimit(core_resource, core_limit)


class Daemon(object):
    """Class Daemon is used to run any routine in the background on unix
    environments as daemon.
    
    There are several things to consider:
    
    * The instance object given to the constructor MUST provide a ``run()``
      function with represents the main routine of the deamon
    
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
        self.startstop()
        instance.run()

    def deamonize(self):
        """Fork the process into the background.
        """
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
            sys.stderr.write(msg)
            sys.exit(1)

        os.chdir(self.WORKDIR)
        os.umask(self.UMASK)
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError, e:
            msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
            sys.stderr.write(msg)
            sys.exit(1)

        if not self.instance.stderr:
            self.instance.stderr = self.instance.stdout

        si = file(self.instance.stdin, 'r')
        so = file(self.instance.stdout, 'a+')
        se = file(self.instance.stderr, 'a+', 0)

        pid = str(os.getpid())

        sys.stderr.write("\n%s\n" % self.startmsg % pid)
        sys.stderr.flush()

        if self.instance.pidfile:
            file(self.instance.pidfile, 'w+').write("%s\n" % pid)

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def startstop(self):
        """Start/stop/restart behaviour.
        """
        if len(sys.argv) > 1:
            action = sys.argv[1]
            try:
                pf = file(self.instance.pidfile, 'r')
                pid = int(pf.read().strip())
                pf.close()
            except IOError:
                pid = None
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
                if pid:
                    mess = "Start aborded since pid file '%s' exists.\n"
                    sys.stderr.write(mess % self.instance.pidfile)
                    sys.exit(1)
                self.deamonize()
                return
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)
