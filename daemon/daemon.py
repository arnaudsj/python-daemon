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
import signal


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
            os._exit(0)
    except OSError, e:
        msg = "fork #1 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        os._exit(1)

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError, e:
        msg = "fork #2 failed: (%d) %s\n" % (e.errno, e.strerror)
        sys.stderr.write(msg)
        os._exit(1)


def close_file_descriptor_if_open(fd):
    """ Close a file descriptor if already open.

        Close the file descriptor `fd`, suppressing an error in the
        case the file was not open.

        """
    try:
        os.close(fd)
    except OSError, exc:
        if exc.errno == errno.EBADF:
            # File descriptor was not open
            pass
        else:
            raise


MAXFD = 1

def get_maximum_file_descriptors():
    """ Return the maximum number of open file descriptors for this process.

        Return the process hard resource limit of maximum number of
        open file descriptors. If the limit is “infinity”, a default
        value of ``MAXFD`` is returned.

        """
    limits = resource.getrlimit(resource.RLIMIT_NOFILE)
    result = limits[1]
    if result == resource.RLIM_INFINITY:
        result = MAXFD
    return result


def close_all_open_files(exclude=set()):
    """ Close all open file descriptors.

        Closes every file descriptor (if open) of this process. If
        specified, `exclude` is a set of file descriptors to *not*
        close.

        The standard streams (stdin, stdout, stderr) are then
        re-opened to the system defaults.

        """
    maxfd = get_maximum_file_descriptors()
    for fd in reversed(range(maxfd)):
        if fd not in exclude:
            close_file_descriptor_if_open(fd)


def redirect_stream(system_stream, target_stream):
    """ Redirect a system stream to a specified file.

        `system_stream` is a standard system stream such as
        ``sys.stdout``. `target_stream` is an open file object that
        should replace the corresponding system stream object.

        """
    os.dup2(target_stream.fileno(), system_stream.fileno())


def set_signal_handlers(signal_map):
    """ Set the signal handlers as specified.

        The `signal_map` argument maps signal numbers to the signal
        handler which should be set for that signal.

        """
    for (signal_number, handler) in signal_map.items():
        signal.signal(signal_number, handler)


class DaemonContext(object):
    """ Context for turning the current program into a daemon process.

        Implements the well-behaved daemon behaviour defined in PEP
        [no number yet].

        """

    def __init__(
        self,
        chroot_directory=None,
        working_directory='/',
        umask=0,
        files_preserve=None,
        pidfile=None,
        stdin=None,
        stdout=None,
        stderr=None,
        signal_map=None,
        ):
        """ Set up a new instance. """
        self.chroot_directory = chroot_directory
        self.working_directory = working_directory
        self.umask = umask
        self.files_preserve = files_preserve
        self.pidfile = pidfile
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.signal_map = signal_map

    def open(self):
        """ Become a daemon process. """
        if self.chroot_directory is not None:
            os.chdir(self.chroot_directory)
            os.chroot(self.chroot_directory)

        prevent_core_dump()

        os.umask(self.umask)
        os.chdir(self.working_directory)

        detach_process_context()

        if not self.stderr:
            self.stderr = self.stdout

        if self.pidfile is not None:
            self.pidfile.__enter__()

        exclude_fds = self._get_exclude_file_descriptors()
        close_all_open_files(exclude=exclude_fds)

        redirect_stream(sys.stdin, self.stdin)
        redirect_stream(sys.stdout, self.stdout)
        redirect_stream(sys.stderr, self.stderr)

        if self.signal_map is not None:
            signal_handler_map = self._make_signal_handler_map()
            set_signal_handlers(signal_handler_map)

    def close(self):
        """ Exit the daemon process context. """
        if self.pidfile is None:
            exception = SystemExit()
            raise exception

        else:
            self.pidfile.__exit__()

    def _get_exclude_file_descriptors(self):
        """ Return the list of file descriptors to exclude closing.

            Returns a list containing the file descriptors for the
            items in `files_preserve`, and also each of `stdin`,
            `stdout`, and `stderr`:

            * If the item is ``None``, it is omitted from the return
              list.

            * If the item has a ``fileno()`` method, that method's
              return value is in the return list.

            * Otherwise, the item is in the return list verbatim.

            """
        files_preserve = self.files_preserve
        if files_preserve is None:
            files_preserve = []
        files_preserve.extend([self.stdin, self.stdout, self.stderr])
        exclude_descriptors = []
        for item in files_preserve:
            if item is None:
                continue
            if hasattr(item, 'fileno'):
                exclude_descriptors.append(item.fileno())
            else:
                exclude_descriptors.append(item)
        return exclude_descriptors

    def _make_signal_handler(self, target):
        """ Make the signal handler for a specified target object.

            If `target` is ``None``, returns ``signal.SIG_IGN``. If
            `target` is a string, returns the attribute of this
            instance named by that string. Otherwise, returns `target`
            itself.

            """
        if target is None:
            result = signal.SIG_IGN
        elif isinstance(target, basestring):
            name = target
            result = getattr(self, name)
        else:
            result = target

        return result

    def _make_signal_handler_map(self):
        """ Make the map from signals to handlers for this instance.

            Constructs a map from signal numbers to handlers for this
            context instance, suitable for passing to
            `set_signal_handlers`.

            """
        signal_handler_map = dict(
            (signal_number, self._make_signal_handler(target))
            for (signal_number, target) in self.signal_map.items())
        return signal_handler_map
