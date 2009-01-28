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
import itertools
import tempfile
import resource
import errno

import scaffold

import daemon


class FakeFileHandleStringIO(StringIO, object):
    """ A StringIO class that fakes a file handle """

    _fileno_generator = itertools.count()

    def __init__(self, *args, **kwargs):
        self._fileno = self._fileno_generator.next()
        super_instance = super(FakeFileHandleStringIO, self)
        super_instance.__init__(*args, **kwargs)

    def fileno(self):
        return self._fileno


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


class detatch_process_context_TestCase(scaffold.TestCase):
    """ Test cases for detach_process_context function """

    def setUp(self):
        """ Set up test fixtures """
        self.mock_outfile = StringIO()
        self.mock_tracker = scaffold.MockTracker(self.mock_outfile)

        self.mock_stderr = FakeFileHandleStringIO()

        test_pids = [0, 0]
        scaffold.mock(
            "os.fork", returns_iter=test_pids,
            tracker=self.mock_tracker)
        scaffold.mock(
            "os.setsid",
            tracker=self.mock_tracker)

        def raise_system_exit(status=None):
            raise SystemExit(status)

        scaffold.mock(
            "sys.exit", returns_func=raise_system_exit,
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
        self.failUnlessRaises(
            SystemExit,
            daemon.daemon.detach_process_context)
        expect_mock_output = """\
            Called os.fork()
            Called sys.exit(0)
            """
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
        self.failUnlessRaises(
            SystemExit,
            daemon.daemon.detach_process_context)
        expect_mock_output = """\
            Called os.fork()
            Called sys.exit(1)
            """
        expect_stderr = """\
            fork #1 failed: ...%(fork_errno)d...%(fork_strerror)s...
            """ % vars()
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
        self.failUnlessRaises(
            SystemExit,
            daemon.daemon.detach_process_context)
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            Called sys.exit(0)
            """
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
        self.failUnlessRaises(
            SystemExit,
            daemon.daemon.detach_process_context)
        expect_mock_output = """\
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            Called sys.exit(1)
            """
        expect_stderr = """\
            fork #2 failed: ...%(fork_errno)d...%(fork_strerror)s...
            """ % vars()
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


def setup_lockfile_fixtures(testcase):
    """ Set up common fixtures for lockfile test cases """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    testcase.mock_pid = 235
    testcase.mock_lockfile_name = tempfile.mktemp()
    testcase.mock_lockfile = FakeFileHandleStringIO()

    def mock_path_exists(path):
        if path == testcase.mock_lockfile_name:
            result = testcase.lockfile_exists_func(path)
        else:
            result = False
        return result

    testcase.lockfile_exists_func = (lambda p: False)

    scaffold.mock(
        "os.path.exists",
        mock_obj=mock_path_exists)

    def mock_lockfile_open_nonexist(filename, mode, buffering):
        if 'r' in mode:
            raise IOError("No such file %(filename)r" % vars())
        else:
            result = testcase.mock_lockfile
        return result

    def mock_lockfile_open_exist(filename, mode, buffering):
        lockfile = testcase.mock_lockfile
        lockfile.write("%(mock_pid)s\n" % vars(testcase))
        lockfile.seek(0)
        return lockfile

    testcase.mock_lockfile_open_nonexist = mock_lockfile_open_nonexist
    testcase.mock_lockfile_open_exist = mock_lockfile_open_exist

    testcase.lockfile_open_func = mock_lockfile_open_nonexist

    def mock_open(filename, mode=None, buffering=None):
        if filename == testcase.mock_lockfile_name:
            result = testcase.lockfile_open_func(filename, mode, buffering)
        else:
            result = FakeFileHandleStringIO()
        return result

    scaffold.mock(
        "__builtin__.file",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)


class lockfile_exists_TestCase(scaffold.TestCase):
    """ Test cases for lockfile_exists function """

    def setUp(self):
        """ Set up test fixtures """
        setup_lockfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_true_when_lockfile_exists(self):
        """ Should return True when lockfile exists """
        self.lockfile_exists_func = (lambda p: True)
        result = daemon.daemon.lockfile_exists(self.mock_lockfile_name)
        self.failUnless(result)

    def test_returns_false_when_no_lockfile_exists(self):
        """ Should return False when lockfile does not exist """
        self.lockfile_exists_func = (lambda p: False)
        result = daemon.daemon.lockfile_exists(self.mock_lockfile_name)
        self.failIf(result)


class read_pid_from_lockfile_TestCase(scaffold.TestCase):
    """ Test cases for read_pid_from_lockfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_lockfile_fixtures(self)
        self.lockfile_open_func = self.mock_lockfile_open_exist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified lockfile filename """
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            Called __builtin__.file(%(lockfile_name)r, 'r')
            """ % vars()
        dummy = daemon.daemon.read_pid_from_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_reads_pid_from_file(self):
        """ Should read the PID from the specified file """
        lockfile_name = self.mock_lockfile_name
        expect_pid = self.mock_pid
        pid = daemon.daemon.read_pid_from_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_pid, pid)

    def test_returns_none_when_file_nonexist(self):
        """ Should return None when the lockfile does not exist """
        lockfile_name = self.mock_lockfile_name
        self.lockfile_open_func = self.mock_lockfile_open_nonexist
        pid = daemon.daemon.read_pid_from_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessIs(None, pid)


class remove_existing_lockfile_TestCase(scaffold.TestCase):
    """ Test cases for remove_existing_lockfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_lockfile_fixtures(self)
        self.lockfile_open_func = self.mock_lockfile_open_exist

        scaffold.mock(
            "os.remove",
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_removes_specified_filename(self):
        """ Should attempt to remove specified lockfile filename """
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            Called os.remove(%(lockfile_name)r)
            """ % vars()
        daemon.daemon.remove_existing_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_ignores_file_not_exist_error(self):
        """ Should ignore error if file does not exist """
        lockfile_name = self.mock_lockfile_name
        mock_error = OSError(errno.ENOENT, "Not there", lockfile_name)
        os.remove.mock_raises = mock_error
        expect_mock_output = """\
            Called os.remove(%(lockfile_name)r)
            """ % vars()
        daemon.daemon.remove_existing_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_propagates_arbitrary_oserror(self):
        """ Should propagate any OSError other than ENOENT """
        lockfile_name = self.mock_lockfile_name
        mock_error = OSError(errno.EACCES, "Denied", lockfile_name)
        os.remove.mock_raises = mock_error
        self.failUnlessRaises(
            mock_error.__class__,
            daemon.daemon.remove_existing_lockfile,
            lockfile_name)


class write_pid_to_lockfile_TestCase(scaffold.TestCase):
    """ Test cases for write_pid_to_lockfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_lockfile_fixtures(self)
        self.lockfile_open_func = self.mock_lockfile_open_nonexist

        scaffold.mock(
            "os.getpid",
            returns=self.mock_pid,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified lockfile filename """
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            Called __builtin__.file(%(lockfile_name)r, 'w')
            ...
            """ % vars()
        daemon.daemon.write_pid_to_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_writes_pid_to_file(self):
        """ Should write the current PID to the specified file """
        lockfile_name = self.mock_lockfile_name
        expect_line = "%(mock_pid)d\n" % vars(self)
        expect_mock_output = """\
            ...
            Called 
            """ % vars()
        daemon.daemon.write_pid_to_lockfile(lockfile_name)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_line, self.mock_lockfile.getvalue())


def setup_streams_fixtures(testcase):
    """ Set up common test fixtures for standard streams """
    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    scaffold.mock(
        "os.dup2",
        tracker=testcase.mock_tracker)


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
        system_stream = FakeFileHandleStringIO()
        system_fileno = system_stream.fileno()
        target_stream = FakeFileHandleStringIO()
        target_fileno = target_stream.fileno()
        expect_mock_output = """\
            Called os.dup2(%(target_fileno)r, %(system_fileno)r)
            """ % vars()
        daemon.daemon.redirect_stream(system_stream, target_stream)
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


def setup_daemon_fixtures(testcase):
    """ Set up common test fixtures for Daemon test case """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    class TestApp(object):

        def __init__(self, lockfile_name):
            self.stdin = tempfile.mktemp()
            self.stdout = tempfile.mktemp()
            self.stderr = tempfile.mktemp()
            self.pidfile = lockfile_name

            self.stream_files = {
                self.stdin: FakeFileHandleStringIO(),
                self.stdout: FakeFileHandleStringIO(),
                self.stderr: FakeFileHandleStringIO(),
                }

    testcase.TestApp = TestApp

    testcase.mock_lockfile_name = tempfile.mktemp()

    scaffold.mock(
        "daemon.daemon.abort_if_existing_lockfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.abort_if_no_existing_lockfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.read_pid_from_lockfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.write_pid_to_lockfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.remove_existing_lockfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.detach_process_context",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.prevent_core_dump",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "daemon.daemon.redirect_stream",
        tracker=testcase.mock_tracker)

    testcase.mock_stderr = FakeFileHandleStringIO()

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

    test_app = testcase.TestApp(testcase.mock_lockfile_name)
    testcase.test_instance = daemon.Daemon(test_app)

    def mock_open(filename, mode=None, buffering=None):
        if filename in test_app.stream_files:
            result = test_app.stream_files[filename]
        else:
            result = FakeFileHandleStringIO()
        return result

    scaffold.mock(
        "__builtin__.file",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)


class Daemon_TestCase(scaffold.TestCase):
    """ Test cases for Daemon class """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of Daemon should be created """
        self.failIfIs(None, self.test_instance)


class Daemon_start_TestCase(scaffold.TestCase):
    """ Test cases for Daemon start process """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_fixtures(self)

        scaffold.mock(
            "sys.argv",
            mock_obj=["fooprog", "start"],
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_aborts_if_lockfile_exists(self):
        """ Should request abort if lockfile exists """
        instance = self.test_instance
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            Called daemon.daemon.abort_if_existing_lockfile(
                %(lockfile_name)r)
            ...
            """ % vars()
        instance.start()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_detaches_process_context(self):
        """ Should request detach of process context """
        instance = self.test_instance
        expect_mock_output = """\
            ...
            Called daemon.daemon.detach_process_context()
            ...
            """ % vars()
        instance.start()
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
        instance.start()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_writes_pid_to_specified_lockfile(self):
        """ Should request creation of a PID file with specified name """
        instance = self.test_instance
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            ...
            Called daemon.daemon.write_pid_to_lockfile(%(lockfile_name)r)
            ...
            """ % vars()
        instance.start()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_redirects_standard_streams(self):
        """ Should request redirection of standard stream files """
        instance = self.test_instance
        test_app = instance.instance
        (system_stdin, system_stdout, system_stderr) = (
            sys.stdin, sys.stdout, sys.stderr)
        (target_stdin, target_stdout, target_stderr) = (
            test_app.stream_files[getattr(test_app, name)]
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
        instance.start()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


class Daemon_stop_TestCase(scaffold.TestCase):
    """ Test cases for Daemon stop process """

    def setUp(self):
        """ Set up test fixtures """
        setup_daemon_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_aborts_if_no_lockfile_exists(self):
        """ Should request abort if lockfile does not exist """
        instance = self.test_instance
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            Called daemon.daemon.abort_if_no_existing_lockfile(
                %(lockfile_name)r)
            ...
            """ % vars()
        instance.stop()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_removes_existing_lockfile(self):
        """ Should request removal of existing lockfile """
        instance = self.test_instance
        lockfile_name = self.mock_lockfile_name
        expect_mock_output = """\
            ...
            Called daemon.daemon.remove_existing_lockfile(%(lockfile_name)r)
            """ % vars()
        instance.stop()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())
