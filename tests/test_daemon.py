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

""" Unit test for bda.daemon.daemon module
"""

import __builtin__
import os
import sys
from StringIO import StringIO
import itertools
import tempfile

import scaffold

from bda.daemon import daemon


class FakeFileHandleStringIO(StringIO, object):
    """ A StringIO class that fakes a file handle """

    _fileno_generator = itertools.count()

    def __init__(self, *args, **kwargs):
        self._fileno = self._fileno_generator.next()
        super_instance = super(FakeFileHandleStringIO, self)
        super_instance.__init__(*args, **kwargs)

    def fileno(self):
        return self._fileno


class Daemon_start_TestCase(scaffold.TestCase):
    """ Test cases for Daemon start process """

    class TestApp(object):

        def __init__(self, pidfile_name):
            self.stdin = tempfile.mktemp()
            self.stdout = tempfile.mktemp()
            self.stderr = tempfile.mktemp()
            self.pidfile = pidfile_name

        def run(self):
            pass

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
        scaffold.mock(
            "os.dup2",
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

        scaffold.mock(
            "sys.argv",
            mock_obj=["fooprog", "start"],
            tracker=self.mock_tracker)

        self.mock_pid = 235
        mock_pidfile_name = tempfile.mktemp()

        self.test_app = self.TestApp(mock_pidfile_name)

        def mock_pidfile_open_nonexist(filename, mode, buffering):
            if 'r' in mode:
                raise IOError("No such file %(filename)r" % vars())
            else:
                result = FakeFileHandleStringIO()
            return result

        def mock_pidfile_open_exist(filename, mode, buffering):
            return FakeFileHandleStringIO("%(mock_pid)s\n" % vars(self))

        self.pidfile_open_func = mock_pidfile_open_nonexist

        def mock_open(filename, mode=None, buffering=None):
            if filename == mock_pidfile_name:
                result = self.pidfile_open_func(filename, mode, buffering)
            else:
                result = FakeFileHandleStringIO()
            return result

        scaffold.mock(
            "__builtin__.file",
            returns_func=mock_open,
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
            daemon.Daemon, self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
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
            daemon.Daemon, self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
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
        instance = daemon.Daemon(self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
            Called os.fork()
            Called os.setsid()
            ...
            """
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
            daemon.Daemon, self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
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
            daemon.Daemon, self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
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
        instance = daemon.Daemon(self.test_app)
        expect_mock_output = """\
            Called __builtin__.file(..., 'r')
            Called os.fork()
            Called os.setsid()
            Called os.fork()
            ...
            Called __builtin__.file(...)
            ...
            """ % vars(instance.instance)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_creates_pid_file_with_specified_name(self):
        """ Should request creation of a PID file with specified name """
        instance = daemon.Daemon(self.test_app)
        expect_mock_output = """\
            ...
            Called __builtin__.file(%(pidfile)r, 'w+')
            ...
            """ % vars(instance.instance)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_disables_standard_streams(self):
        """ Should disable standard stream files """
        instance = daemon.Daemon(self.test_app)
        expect_mock_output = """\
            ...
            Called __builtin__.file(%(stdin)r, 'r')
            Called __builtin__.file(%(stdout)r, 'a+')
            Called __builtin__.file(%(stderr)r, 'a+', 0)
            ...
            Called os.dup2(...)
            Called os.dup2(...)
            Called os.dup2(...)
            """ % vars(instance.instance)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())
