# Copyright (c) 2001-2009 Juergen Hermann, Noah Spurrier, Clark Evans,
#                         Robert Niederreiter, Jens Klein, Ben Finney
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys
import time

from signal import SIGTERM

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
