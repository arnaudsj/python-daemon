# -*- coding: utf-8 -*-

"""
Copyright (c) 2006-2007 by:
    Blue Dynamics Alliance Klein & Partner KEG, Austria
    Squarewave Computing Robert Niederreiter, Austria

Permission to use, copy, modify, and distribute this software and its 
documentation for any purpose and without fee is hereby granted, provided that 
the above copyright notice appear in all copies and that both that copyright 
notice and this permission notice appear in supporting documentation, and that 
the name of Stichting Mathematisch Centrum or CWI not be used in advertising 
or publicity pertaining to distribution of the software without specific, 
written prior permission.

STICHTING MATHEMATISCH CENTRUM DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS 
SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS, IN 
NO EVENT SHALL STICHTING MATHEMATISCH CENTRUM BE LIABLE FOR ANY SPECIAL, 
INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS 
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER 
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF 
THIS SOFTWARE.

References:
    http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/66012

History:
    2001/07/10 by Juergen Hermann
    2002/08/28 by Noah Spurrier
    2003/02/24 by Clark Evans
    2006/01/25 by Robert Niederreiter

Class Daemon is used to run any routine in the background on unix environments
as daemon.

There are several things to consider:
    
*The instance object given to the constructor MUST provide a run method with 
represents the main routine of the deamon

*The instance object MUST provide global file descriptors for (and named as):
    -stdin
    -stdout
    -stderr

*The instance object MUST provide a global (and named as) pidfile.
"""

__author__ = """Robert Niederreiter <office@squarewave.at>"""
__version__ = 0.1
__docformat__ = 'plaintext'

import os
import sys
import time

from signal import SIGTERM

class Daemon(object):

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
            sys.stderr.write("fork #1 failed: (%d) %s\n" % (e.errno, e.strerror))
            sys.exit(1)
        
        os.chdir(self.WORKDIR) 
        os.umask(self.UMASK) 
        os.setsid() 
    
        try: 
            pid = os.fork() 
            if pid > 0:
                sys.exit(0)
        except OSError, e: 
            sys.stderr.write("fork #2 failed: (%d) %s\n" % (e.errno, e.strerror))
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
            file(self.instance.pidfile,'w+').write("%s\n" % pid)
    
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def startstop(self):
        """Start/stop/restart behaviour.
        """
        if len(sys.argv) > 1:
            action = sys.argv[1]
            try:
                pf  = file(self.instance.pidfile,'r')
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
                        os.kill(pid,SIGTERM)
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
 