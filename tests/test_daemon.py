# -*- coding: utf-8 -*-
#
# tests/test_daemon.py
#
# Copyright © 2008–2009 Ben Finney <ben+python@benfinney.id.au>
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Unit test for daemon module
"""

import __builtin__
import os
import sys
from StringIO import StringIO
import tempfile
import resource
import errno
import signal

import scaffold
from test_pidlockfile import (
    FakeFileDescriptorStringIO,
    setup_pidfile_fixtures,
    )

from daemon import pidlockfile
import daemon


class prevent_core_dump_TestCase(scaffold.TestCase):
    """ Test cases for prevent_core_dump function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.RLIMIT_CORE = object()
        scaffold.mock(
            "resource.RLIMIT_CORE", mock_obj=self.RLIMIT_CORE,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.getrlimit", returns=None,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.setrlimit", returns=None,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_sets_core_limit_to_zero(self):
        """ Should set the RLIMIT_CORE resource to zero """
        expect_resource = self.RLIMIT_CORE
        expect_limit = (0, 0)
        expect_mock_output = """\
            Called resource.getrlimit(
                %(expect_resource)r)
            Called resource.setrlimit(
                %(expect_resource)r,
                %(expect_limit)r)
            """ % vars()
        daemon.daemon.prevent_core_dump()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_raises_error_when_no_core_resource(self):
        """ Should raise ValueError if no RLIMIT_CORE resource """
        def mock_getrlimit(res):
            if res == resource.RLIMIT_CORE:
                raise ValueError("Bogus platform doesn't have RLIMIT_CORE")
            else:
                return None
        resource.getrlimit.mock_returns_func = mock_getrlimit
        expect_error = ValueError
        self.failUnlessRaises(
            expect_error,
            daemon.daemon.prevent_core_dump)


class detach_process_context_TestCase(scaffold.TestCase):
    """ Test cases for detach_process_context function """

    class FakeOSExit(SystemExit):
        """ Fake exception raised for os._exit() """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.mock_stderr = FakeFileDescriptorStringIO()

        test_pids = [0, 0]
        scaffold.mock(
            "os.fork", returns_iter=test_pids,
            tracker=self.mock_tracker)
        scaffold.mock(
            "os.setsid",
            tracker=self.mock_tracker)

        def raise_os_exit(status=None):
            raise self.FakeOSExit(status)

        scaffold.mock(
            "os._exit", returns_func=raise_os_exit,
            tracker=self.mock_tracker)

        scaffold.mock(
            "sys.stderr",
            mock_obj=self.mock_stderr,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_parent_exits(self):
        """ Parent process should exit """
        parent_pid = 23
        scaffold.mock("os.fork", returns_iter=[parent_pid],
            tracker=self.mock_tracker)
        expect_mock_output = """\
            Called os.fork()
            Called os._exit(0)
            """
        self.failUnlessRaises(
            self.FakeOSExit,
            daemon.daemon.detach_process_context)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_first_fork_error_reports_to_stderr(self):
        """ Error on first fork should cause report to stderr """
        fork_errno = 13
        fork_strerror = "Bad stuff happened"
        fork_error = OSError(fork_errno, fork_strerror)
        test_pids_iter = iter([fork_error])

        def mock_fork():
            next = test_pids_iter.next()
            if isinstance(next, Exception):
                raise next
            else:
                return next

        scaffold.mock("os.fork", returns_func=mock_fork,
            tracker=self.mock_tracker)
        expect_mock_output = """\
            Called os.fork()
            Called os._exit(1)
            """
        expect_stderr = """\
            fork #1 failed: ...%(fork_errno)d...%(fork_strerror)s...
            """ % vars()
        self.failUnlessRaises(
            self.FakeOSExit,
            daemon.daemon.detach_process_context)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())
        self.failUnlessOutputCheckerMatch(
            expect_stderr, self.mock_stderr.getvalue())

    def test_child_starts_new_process_group(self):
        """ Child should start new process group """
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            ...
            """
        daemon.daemon.detach_process_context()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_child_forks_next_parent_exits(self):
        """ Child should fork, then exit if parent """
        test_pids = [0, 42]
        scaffold.mock("os.fork", returns_iter=test_pids,
            tracker=self.mock_tracker)
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            Called os._exit(0)
            """
        self.failUnlessRaises(
            self.FakeOSExit,
            daemon.daemon.detach_process_context)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_second_fork_error_reports_to_stderr(self):
        """ Error on second fork should cause report to stderr """
        fork_errno = 17
        fork_strerror = "Nasty stuff happened"
        fork_error = OSError(fork_errno, fork_strerror)
        test_pids_iter = iter([0, fork_error])

        def mock_fork():
            next = test_pids_iter.next()
            if isinstance(next, Exception):
                raise next
            else:
                return next

        scaffold.mock("os.fork", returns_func=mock_fork,
            tracker=self.mock_tracker)
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            Called os._exit(1)
            """
        expect_stderr = """\
            fork #2 failed: ...%(fork_errno)d...%(fork_strerror)s...
            """ % vars()
        self.failUnlessRaises(
            self.FakeOSExit,
            daemon.daemon.detach_process_context)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())
        self.failUnlessOutputCheckerMatch(
            expect_stderr, self.mock_stderr.getvalue())

    def test_child_forks_next_child_continues(self):
        """ Child should fork, then continue if child """
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            """ % vars()
        daemon.daemon.detach_process_context()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


def setup_streams_fixtures(testcase):
    """ Set up common test fixtures for standard streams """
    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    testcase.stream_file_paths = dict(
        stdin = tempfile.mktemp(),
        stdout = tempfile.mktemp(),
        stderr = tempfile.mktemp(),
        )

    testcase.stream_files_by_name = dict(
        (name, FakeFileDescriptorStringIO())
        for name in ['stdin', 'stdout', 'stderr']
        )

    testcase.stream_files_by_path = dict(
        (testcase.stream_file_paths[name],
            testcase.stream_files_by_name[name])
        for name in ['stdin', 'stdout', 'stderr']
        )

    scaffold.mock(
        "os.dup2",
        tracker=testcase.mock_tracker)


class close_file_descriptor_if_open_TestCase(scaffold.TestCase):
    """ Test cases for close_file_descriptor_if_open function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.test_fd = 274

        scaffold.mock(
            "os.close",
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_requests_file_descriptor_close(self):
        """ Should request close of file descriptor """
        fd = self.test_fd
        expect_mock_output = """\
            Called os.close(%(fd)r)
            """ % vars()
        daemon.daemon.close_file_descriptor_if_open(fd)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_ignores_badfd_error_on_close(self):
        """ Should ignore OSError EBADF when closing """
        fd = self.test_fd
        test_error = OSError(errno.EBADF, "Bad file descriptor")
        def os_close(fd):
            raise test_error
        os.close.mock_returns_func = os_close
        expect_mock_output = """\
            Called os.close(%(fd)r)
            """ % vars()
        daemon.daemon.close_file_descriptor_if_open(fd)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_propagates_error_on_close(self):
        """ Should propagate OSError when closing """
        fd = self.test_fd
        test_error = OSError(object(), "Unexpected error")
        def os_close(fd):
            raise test_error
        os.close.mock_returns_func = os_close
        self.failUnlessRaises(
            type(test_error),
            daemon.daemon.close_file_descriptor_if_open, fd)


class maxfd_TestCase(scaffold.TestCase):
    """ Test cases for module MAXFD """

    def test_positive(self):
        """ Should be a positive number """
        maxfd = daemon.daemon.MAXFD
        self.failUnless(maxfd > 0)

    def test_integer(self):
        """ Should be an integer """
        maxfd = daemon.daemon.MAXFD
        self.failUnlessEqual(int(maxfd), maxfd)


class get_maximum_file_descriptors_TestCase(scaffold.TestCase):
    """ Test cases for get_maximum_file_descriptors function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.RLIMIT_NOFILE = object()
        self.RLIM_INFINITY = object()
        self.test_rlimit_nofile = 2468

        def mock_getrlimit(resource):
            result = (object(), self.test_rlimit_nofile)
            if resource != self.RLIMIT_NOFILE:
                result = NotImplemented
            return result

        self.test_maxfd = object()
        scaffold.mock(
            "daemon.daemon.MAXFD", mock_obj=self.test_maxfd,
            tracker=self.mock_tracker)

        scaffold.mock(
            "resource.RLIMIT_NOFILE", mock_obj=self.RLIMIT_NOFILE,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.RLIM_INFINITY", mock_obj=self.RLIM_INFINITY,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.getrlimit", returns_func=mock_getrlimit,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_system_hard_limit(self):
        """ Should return process hard limit on number of files """
        expect_result = self.test_rlimit_nofile
        result = daemon.daemon.get_maximum_file_descriptors()
        self.failUnlessEqual(expect_result, result)

    def test_returns_module_default_if_hard_limit_infinity(self):
        """ Should return module MAXFD if hard limit is infinity """
        self.test_rlimit_nofile = self.RLIM_INFINITY
        expect_result = self.test_maxfd
        result = daemon.daemon.get_maximum_file_descriptors()
        self.failUnlessEqual(expect_result, result)


class close_all_open_files_TestCase(scaffold.TestCase):
    """ Test cases for close_all_open_files function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.RLIMIT_NOFILE = object()
        self.RLIM_INFINITY = object()
        self.test_rlimit_nofile = self.RLIM_INFINITY

        def mock_getrlimit(resource):
            result = (self.test_rlimit_nofile, object())
            if resource != self.RLIMIT_NOFILE:
                result = NotImplemented
            return result

        self.test_maxfd = 8
        scaffold.mock(
            "daemon.daemon.get_maximum_file_descriptors",
            returns=self.test_maxfd,
            tracker=self.mock_tracker)

        scaffold.mock(
            "resource.RLIMIT_NOFILE", mock_obj=self.RLIMIT_NOFILE,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.RLIM_INFINITY", mock_obj=self.RLIM_INFINITY,
            tracker=self.mock_tracker)
        scaffold.mock(
            "resource.getrlimit", returns_func=mock_getrlimit,
            tracker=self.mock_tracker)

        scaffold.mock(
            "daemon.daemon.close_file_descriptor_if_open",
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_requests_all_open_files_to_close(self):
        """ Should request close of all open files """
        expect_file_descriptors = reversed(range(self.test_maxfd))
        expect_mock_output = "...\n" + "".join(
            "Called daemon.daemon.close_file_descriptor_if_open(%(fd)r)\n"
                % vars()
            for fd in expect_file_descriptors)
        daemon.daemon.close_all_open_files()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_requests_all_but_excluded_files_to_close(self):
        """ Should request close of all open files but those excluded """
        test_exclude = set([3, 7])
        args = dict(
            exclude = test_exclude,
            )
        expect_file_descriptors = (
            fd for fd in reversed(range(self.test_maxfd))
            if fd not in test_exclude)
        expect_mock_output = "...\n" + "".join(
            "Called daemon.daemon.close_file_descriptor_if_open(%(fd)r)\n"
                % vars()
            for fd in expect_file_descriptors)
        daemon.daemon.close_all_open_files(**args)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


class redirect_stream_TestCase(scaffold.TestCase):
    """ Test cases for redirect_stream function """

    def setUp(self):
        """ Set up test fixtures """
        setup_streams_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_duplicates_file_descriptor(self):
        """ Should duplicate file descriptor from target to system stream """
        system_stream = FakeFileDescriptorStringIO()
        system_fileno = system_stream.fileno()
        target_stream = FakeFileDescriptorStringIO()
        target_fileno = target_stream.fileno()
        expect_mock_output = """\
            Called os.dup2(%(target_fileno)r, %(system_fileno)r)
            """ % vars()
        daemon.daemon.redirect_stream(system_stream, target_stream)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


class set_signal_handlers_TestCase(scaffold.TestCase):
    """ Test cases for set_signal_handlers function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        scaffold.mock(
            "signal.signal",
            tracker=self.mock_tracker)

        self.signal_map = {
            signal.SIGQUIT: object(),
            signal.SIGSEGV: object(),
            signal.SIGINT: object(),
            }

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_sets_signal_handler_for_each_item(self):
        """ Should set signal handler for each item in map """
        signal_map = self.signal_map
        expect_mock_output = "".join(
            "Called signal.signal(%(signal_number)r, %(handler)r)\n"
                % vars()
            for (signal_number, handler) in signal_map.items())
        daemon.daemon.set_signal_handlers(signal_map)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


def setup_daemon_context_fixtures(testcase):
    """ Set up common test fixtures for DaemonContext test case """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    setup_streams_fixtures(testcase)

    setup_pidfile_fixtures(testcase)

    testcase.mock_pidfile_path = tempfile.mktemp()

    testcase.mock_pidlockfile = scaffold.Mock(
        "pidlockfile.PIDLockFile",
        tracker=testcase.mock_tracker)
    testcase.mock_pidlockfile.path = testcase.mock_pidfile_path

    scaffold.mock(
        "daemon.daemon.detach_process_context",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.prevent_core_dump",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.close_all_open_files",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.redirect_stream",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.set_signal_handlers",
        tracker=testcase.mock_tracker)

    testcase.mock_stderr = FakeFileDescriptorStringIO()

    testcase.daemon_context_args = dict(
        stdin = testcase.stream_files_by_name['stdin'],
        stdout = testcase.stream_files_by_name['stdout'],
        stderr = testcase.stream_files_by_name['stderr'],
        )
    testcase.test_instance = daemon.DaemonContext(
        **testcase.daemon_context_args)

    def mock_open(filename, mode=None, buffering=None):
        if filename in testcase.stream_files_by_path:
            result = testcase.stream_files_by_path[filename]
        else:
            result = FakeFileDescriptorStringIO()
        return result

    scaffold.mock(
        "__builtin__.open",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)

    scaffold.mock(
        "sys.stdin",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "sys.stdout",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "sys.stderr",
        mock_obj=testcase.mock_stderr,
        tracker=testcase.mock_tracker)


class DaemonContext_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext class """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of DaemonContext should be created """
        self.failUnlessIsInstance(
            self.test_instance, daemon.daemon.DaemonContext)

    def test_minimum_zero_arguments(self):
        """ Initialiser should not require any arguments """
        instance = daemon.daemon.DaemonContext()
        self.failIfIs(None, instance)

    def test_has_specified_files_preserve(self):
        """ Should have specified files_preserve option """
        args = dict(
            files_preserve = object(),
            )
        expect_files_preserve = args['files_preserve']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_files_preserve, instance.files_preserve)

    def test_has_specified_pidfile(self):
        """ Should have the specified pidfile """
        args = dict(
            pidfile = object(),
            )
        expect_pidfile = args['pidfile']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_pidfile, instance.pidfile)

    def test_has_specified_stdin(self):
        """ Should have specified stdin option """
        args = dict(
            stdin = object(),
            )
        expect_file = args['stdin']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_file, instance.stdin)

    def test_has_specified_stdout(self):
        """ Should have specified stdout option """
        args = dict(
            stdout = object(),
            )
        expect_file = args['stdout']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_file, instance.stdout)

    def test_has_specified_stderr(self):
        """ Should have specified stderr option """
        args = dict(
            stderr = object(),
            )
        expect_file = args['stderr']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_file, instance.stderr)

    def test_has_specified_signal_map(self):
        """ Should have specified signal_map option """
        args = dict(
            signal_map = object(),
            )
        expect_signal_map = args['signal_map']
        instance = daemon.daemon.DaemonContext(**args)
        self.failUnlessEqual(expect_signal_map, instance.signal_map)


class DaemonContext_open_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext.open method """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

        self.test_files_preserve = object()
        self.test_files_preserve_fds = object()
        scaffold.mock(
            "daemon.daemon.DaemonContext._get_exclude_file_descriptors",
            returns=self.test_files_preserve_fds,
            tracker=self.mock_tracker)

        self.test_signal_handler_map = object()
        scaffold.mock(
            "daemon.daemon.DaemonContext._make_signal_handler_map",
            returns=self.test_signal_handler_map,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_detaches_process_context(self):
        """ Should request detach of process context """
        instance = self.test_instance
        expect_mock_output = """\
            Called daemon.daemon.detach_process_context()
            ...
            """ % vars()
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_prevents_core_dump(self):
        """ Should request prevention of core dumps """
        instance = self.test_instance
        expect_mock_output = """\
            ...
            Called daemon.daemon.prevent_core_dump()
            ...
            """ % vars()
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_enters_pidfile_context(self):
        """ Should enter the PID file context manager """
        instance = self.test_instance
        instance.pidfile = self.mock_pidlockfile
        expect_mock_output = """\
            ...
            Called pidlockfile.PIDLockFile.__enter__()
            ...
            """
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_closes_open_files(self):
        """ Should close all open files, excluding `files_preserve` """
        instance = self.test_instance
        expect_exclude = self.test_files_preserve_fds
        expect_mock_output = """\
            ...
            Called daemon.daemon.close_all_open_files(
                exclude=%(expect_exclude)r)
            ...
            """ % vars()
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_redirects_standard_streams(self):
        """ Should request redirection of standard stream files """
        instance = self.test_instance
        (system_stdin, system_stdout, system_stderr) = (
            sys.stdin, sys.stdout, sys.stderr)
        (target_stdin, target_stdout, target_stderr) = (
            self.stream_files_by_name[name]
            for name in ['stdin', 'stdout', 'stderr'])
        expect_mock_output = """\
            ...
            Called daemon.daemon.redirect_stream(
                %(system_stdin)r, %(target_stdin)r)
            Called daemon.daemon.redirect_stream(
                %(system_stdout)r, %(target_stdout)r)
            Called daemon.daemon.redirect_stream(
                %(system_stderr)r, %(target_stderr)r)
            """ % vars()
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_omits_signal_handlers_if_no_signal_map(self):
        """ Should omit signal handler setting if `signal_map` is None """
        instance = self.test_instance
        instance.signal_map = None
        instance.open()
        scaffold.mock_restore()
        self.failIfIn(
            self.mock_outfile.getvalue(),
            "Called daemon.daemon.set_signal_handlers")

    def test_sets_signal_handlers_from_signal_map(self):
        """ Should set signal handlers according to `signal_map` """
        instance = self.test_instance
        instance.signal_map = object()
        expect_signal_handler_map = self.test_signal_handler_map
        expect_mock_output = """\
            ...
            Called daemon.daemon.set_signal_handlers(
                %(expect_signal_handler_map)r)
            """ % vars()
        instance.open()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


class DaemonContext_close_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext.close method """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_exits_pidfile_context(self):
        """ Should exit the PID file context manager """
        instance = self.test_instance
        instance.pidfile = self.mock_pidlockfile
        expect_mock_output = """\
            Called pidlockfile.PIDLockFile.__exit__()
            """
        instance.close()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_raises_system_exit(self):
        """ Should raise SystemExit """
        instance = self.test_instance
        expect_exception = SystemExit
        self.failUnlessRaises(
            expect_exception,
            instance.close)


class DaemonContext_get_exclude_file_descriptors_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext._get_exclude_file_descriptors function """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

        self.test_files = {
            2: FakeFileDescriptorStringIO(),
            5: 5,
            11: FakeFileDescriptorStringIO(),
            17: None,
            23: FakeFileDescriptorStringIO(),
            37: 37,
            42: FakeFileDescriptorStringIO(),
            }
        for (fileno, item) in self.test_files.items():
            if hasattr(item, '_fileno'):
                item._fileno = fileno
        self.test_file_descriptors = [
            fd for (fd, item) in self.test_files.items()
            if item is not None]
        self.test_file_descriptors.extend([
            self.stream_files_by_name[name].fileno()
            for name in ['stdin', 'stdout', 'stderr']
            ])

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_expected_file_descriptors(self):
        """ Should return expected list of file descriptors """
        instance = self.test_instance
        instance.files_preserve = self.test_files.values()
        expect_result = self.test_file_descriptors
        result = instance._get_exclude_file_descriptors()
        self.failUnlessEqual(sorted(expect_result), sorted(result))

    def test_returns_stream_redirects_if_no_files_preserve(self):
        """ Should return only stream redirects if no files_preserve """
        instance = self.test_instance
        instance.files_preserve = None
        expect_result = [
            self.stream_files_by_name[name].fileno()
            for name in ['stdin', 'stdout', 'stderr']]
        result = instance._get_exclude_file_descriptors()
        self.failUnlessEqual(sorted(expect_result), sorted(result))

    def test_returns_empty_list_if_no_files(self):
        """ Should return empty list if no file options """
        instance = self.test_instance
        for name in ['files_preserve', 'stdin', 'stdout', 'stderr']:
            setattr(instance, name, None)
        expect_result = []
        result = instance._get_exclude_file_descriptors()
        self.failUnlessEqual(sorted(expect_result), sorted(result))


class DaemonContext_make_signal_handler_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext._make_signal_handler function """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_ignore_for_none(self):
        """ Should return SIG_IGN when None handler specified """
        instance = self.test_instance
        target = None
        expect_result = signal.SIG_IGN
        result = instance._make_signal_handler(target)
        self.failUnlessEqual(expect_result, result)

    def test_returns_method_for_name(self):
        """ Should return method of DaemonContext when name specified """
        instance = self.test_instance
        target = 'close'
        expect_result = instance.close
        result = instance._make_signal_handler(target)
        self.failUnlessEqual(expect_result, result)

    def test_raises_error_for_unknown_name(self):
        """ Should raise AttributeError for unknown method name """
        instance = self.test_instance
        target = 'b0gUs'
        expect_error = AttributeError
        self.failUnlessRaises(
            expect_error,
            instance._make_signal_handler, target)

    def test_returns_object_for_object(self):
        """ Should return same object for any other object """
        instance = self.test_instance
        target = object()
        expect_result = target
        result = instance._make_signal_handler(target)
        self.failUnlessEqual(expect_result, result)


class DaemonContext_make_signal_handler_map_TestCase(scaffold.TestCase):
    """ Test cases for DaemonContext._make_signal_handler_map function """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_context_fixtures(self)

        self.test_instance.signal_map = {
            object(): object(),
            object(): object(),
            object(): object(),
            }

        self.test_signal_handlers = dict(
            (key, object())
            for key in self.test_instance.signal_map.values())
        self.test_signal_handler_map = dict(
            (key, self.test_signal_handlers[target])
            for (key, target) in self.test_instance.signal_map.items())

        def mock_make_signal_handler(target):
            return self.test_signal_handlers[target]
        scaffold.mock(
            "daemon.daemon.DaemonContext._make_signal_handler",
            returns_func=mock_make_signal_handler,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_constructed_signal_handler_items(self):
        """ Should return items as constructed via make_signal_handler """
        instance = self.test_instance
        expect_result = self.test_signal_handler_map
        result = instance._make_signal_handler_map()
        self.failUnlessEqual(expect_result, result)
