# -*- coding: utf-8 -*-

# daemon/daemon.py
#
# Copyright © 2008–2009 Ben Finney <ben+python@benfinney.id.au>
# Copyright © 2007–2008 Robert Niederreiter, Jens Klein
# Copyright © 2004–2005 Chad J. Schroeder
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
import resource
import errno
import signal
import socket


class DaemonError(Exception):
    """ Base exception class for errors from this module. """

class DaemonEnvironmentOSError(DaemonError, OSError):
    """ Exception raised when daemon environment setup receives OSError. """

class DaemonProcessDetachError(DaemonError, OSError):
    """ Exception raised when process detach fails. """


def change_working_directory(directory):
    """ Change the working directory of this process.
        """
    try:
        os.chdir(directory)
    except Exception, exc:
        error = DaemonEnvironmentOSError(
            "Unable to change working directory (%(exc)s)"
            % vars())
        raise error


def change_root_directory(directory):
    """ Change the root directory of this process.

        Sets the current working directory, then the process root
        directory, to the specified `directory`. Requires appropriate
        OS privileges for this process.

        """
    try:
        os.chdir(directory)
        os.chroot(directory)
    except Exception, exc:
        error = DaemonEnvironmentOSError(
            "Unable to change root directory (%(exc)s)"
            % vars())
        raise error


def change_file_creation_mask(mask):
    """ Change the file creation mask for this process.
        """
    try:
        os.umask(mask)
    except Exception, exc:
        error = DaemonEnvironmentOSError(
            "Unable to change file creation mask (%(exc)s)"
            % vars())
        raise error


def change_process_owner(uid, gid):
    """ Change the owning UID and GID of this process.

        Sets the GID then the UID of the process (in that order, to
        avoid permission errors) to the specified `gid` and `uid`
        values. Requires appropriate OS privileges for this process.

        """
    try:
        os.setgid(gid)
        os.setuid(uid)
    except Exception, exc:
        error = DaemonEnvironmentOSError(
            "Unable to change file creation mask (%(exc)s)"
            % vars())
        raise error


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
    except OSError, exc:
        exc_errno = exc.errno
        exc_strerror = exc.strerror
        error = DaemonProcessDetachError(
            "Failed first fork: [%(exc_errno)d] %(exc_strerror)s" % vars())
        raise error

    os.setsid()

    try:
        pid = os.fork()
        if pid > 0:
            os._exit(0)
    except OSError, exc:
        exc_errno = exc.errno
        exc_strerror = exc.strerror
        error = DaemonProcessDetachError(
            "Failed second fork: [%(exc_errno)d] %(exc_strerror)s" % vars())
        raise error


def is_process_started_by_init():
    """ Determine if the current process is started by `init`.

        The `init` process has the process ID of 1; if that is our
        parent process ID, return ``True``, otherwise ``False``.
    
        """
    result = False

    init_pid = 1
    if os.getppid() == init_pid:
        result = True

    return result


def is_socket(fd):
    """ Determine if the file descriptor is a socket.

        Return ``False`` if querying the socket type of `fd` raises an
        error; otherwise return ``True``.

        """
    result = False

    file_socket = socket.fromfd(fd, socket.AF_INET, socket.SOCK_RAW)

    try:
        socket_type = file_socket.getsockopt(
            socket.SOL_SOCKET, socket.SO_TYPE)
    except socket.error, exc:
        exc_errno = exc.args[0]
        if exc_errno == errno.ENOTSOCK:
            # Socket operation on non-socket
            pass
        else:
            # Some other socket error
            result = True
    else:
        # No error getting socket type
        result = True

    return result


def is_process_started_by_superserver():
    """ Determine if the current process is started by the superserver.

        The internet superserver creates a network socket, and
        attaches it to the standard streams of the child process. If
        that is the case for this process, return ``True``, otherwise
        ``False``.
    
        """
    result = False

    stdin_fd = sys.__stdin__.fileno()
    if is_socket(stdin_fd):
        result = True

    return result


def is_detach_process_context_required():
    """ Determine whether detaching process context is required.

        Return ``True`` if the process environment indicates the
        process is already detached:

        * Process was started by `init`; or

        * Process was started by `inetd`.

        """
    result = True
    if is_process_started_by_init() or is_process_started_by_superserver():
        result = False

    return result


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

        If `target_stream` is ``None``, defaults to opening the
        operating system's null device and using its file descriptor.

        """
    if target_stream is None:
        target_fd = os.open(os.devnull, os.O_RDWR)
    else:
        target_fd = target_stream.fileno()
    os.dup2(target_fd, system_stream.fileno())


def make_default_signal_map():
    """ Make the default signal map for this system.

        The signals available differ by system. The map will not
        contain any signals not defined on the running system.

        """
    name_map = {
        'SIGCLD': None,
        'SIGTSTP': None,
        'SIGTTIN': None,
        'SIGTTOU': None,
        'SIGTERM': 'terminate',
        }
    signal_map = dict(
        (getattr(signal, name), target)
        for (name, target) in name_map.items()
        if hasattr(signal, name))

    return signal_map


def set_signal_handlers(signal_handler_map):
    """ Set the signal handlers as specified.

        The `signal_handler_map` argument is a map from signal number
        to signal handler. See the `signal` module for details.

        """
    for (signal_number, handler) in signal_handler_map.items():
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
        uid=None,
        gid=None,
        detach_process=None,
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

        if uid is None:
            uid = os.getuid()
        self.uid = uid
        if gid is None:
            gid = os.getgid()
        self.gid = gid

        if detach_process is None:
            detach_process = is_detach_process_context_required()
        self.detach_process = detach_process

        if signal_map is None:
            signal_map = make_default_signal_map()
        self.signal_map = signal_map

    def open(self):
        """ Become a daemon process. """
        if self.chroot_directory is not None:
            change_root_directory(self.chroot_directory)

        prevent_core_dump()

        change_file_creation_mask(self.umask)
        change_working_directory(self.working_directory)
        change_process_owner(self.uid, self.gid)

        if self.detach_process:
            detach_process_context()

        signal_handler_map = self._make_signal_handler_map()
        set_signal_handlers(signal_handler_map)

        exclude_fds = self._get_exclude_file_descriptors()
        close_all_open_files(exclude=exclude_fds)

        redirect_stream(sys.stdin, self.stdin)
        redirect_stream(sys.stdout, self.stdout)
        redirect_stream(sys.stderr, self.stderr)

        if self.pidfile is not None:
            self.pidfile.__enter__()

    def __enter__(self):
        """ Context manager entry point. """
        self.open()
        return self

    def close(self):
        """ Exit the daemon process context. """

    def __exit__(self, exc_type, exc_value, traceback):
        """ Context manager exit point. """
        self.close()

    def terminate(self, signal_number, stack_frame):
        """ Signal handler for end-process signals. """
        if self.pidfile is not None:
            self.pidfile.__exit__()
        self.close()
        exception = SystemExit(
            "Terminating on signal %(signal_number)r"
                % vars())
        raise exception

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
