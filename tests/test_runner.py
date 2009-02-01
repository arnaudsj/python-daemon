# -*- coding: utf-8 -*-
#
# tests/test_runner.py
#
# Copyright © 2009 Ben Finney <ben+python@benfinney.id.au>
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Unit test for runner module
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
from test_daemon import (
    FakeFileDescriptorStringIO,
    setup_streams_fixtures,
    )
import daemon.daemon

from daemon import runner


def setup_runner_fixtures(testcase):
    """ Set up common test fixtures for Runner test case """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    setup_streams_fixtures(testcase)

    testcase.mock_stderr = FakeFileDescriptorStringIO()
    scaffold.mock(
        "sys.stderr",
        mock_obj=testcase.mock_stderr,
        tracker=testcase.mock_tracker)

    testcase.mock_pidfile_path = tempfile.mktemp()

    class TestApp(object):

        def __init__(self):
            self.stdin_path = testcase.stream_file_paths['stdin']
            self.stdout_path = testcase.stream_file_paths['stdout']
            self.stderr_path = testcase.stream_file_paths['stderr']
            self.pidfile_path = testcase.mock_pidfile_path

        run = scaffold.Mock(
            "TestApp.run",
            tracker=testcase.mock_tracker)

    testcase.TestApp = TestApp

    scaffold.mock(
        "daemon.runner.DaemonContext",
        returns=scaffold.Mock(
            "DaemonContext",
            tracker=testcase.mock_tracker),
        tracker=testcase.mock_tracker)

    testcase.test_app = testcase.TestApp()

    testcase.valid_argv_params = {
        'start': ['fooprog', 'start'],
        'stop': ['fooprog', 'stop'],
        'restart': ['fooprog', 'restart'],
        }

    def mock_open(filename, mode=None, buffering=None):
        if filename in testcase.stream_files_by_path:
            result = testcase.stream_files_by_path[filename]
        else:
            result = FakeFileDescriptorStringIO()
        result.mode = mode
        return result

    scaffold.mock(
        "__builtin__.open",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)

    scaffold.mock(
        "sys.argv",
        mock_obj=testcase.valid_argv_params['start'],
        tracker=testcase.mock_tracker)

    testcase.test_instance = runner.Runner(testcase.test_app)


class Runner_TestCase(scaffold.TestCase):
    """ Test cases for Runner class """

    def setUp(self):
        """ Set up test fixtures """
        setup_runner_fixtures(self)
        self.mock_outfile.truncate(0)

        scaffold.mock(
            "runner.Runner.parse_args",
            tracker=self.mock_tracker)

        self.test_instance = runner.Runner(self.test_app)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of Runner should be created """
        self.failUnlessIsInstance(self.test_instance, runner.Runner)

    def test_parses_commandline_args(self):
        """ Should parse commandline arguments """
        expect_mock_output = """\
            Called runner.Runner.parse_args()
            ...
            """
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_has_specified_app(self):
        """ Should have specified application object """
        self.failUnlessIs(self.test_app, self.test_instance.app)

    def test_daemon_context_has_specified_pidfile_path(self):
        """ DaemonContext component should have specified PID file path """
        expect_pidfile_path = self.test_app.pidfile_path
        daemon_context = self.test_instance.daemon_context
        self.failUnlessEqual(
            expect_pidfile_path, daemon_context.pidfile_path)

    def test_daemon_context_has_specified_stdin_stream(self):
        """ DaemonContext component should have specified stdin file """
        test_app = self.test_app
        expect_file = self.stream_files_by_name['stdin']
        daemon_context = self.test_instance.daemon_context
        self.failUnlessEqual(expect_file, daemon_context.stdin)

    def test_daemon_context_has_stdin_in_read_mode(self):
        """ DaemonContext component should open stdin file for read """
        expect_mode = 'r'
        daemon_context = self.test_instance.daemon_context
        self.failUnlessIn(daemon_context.stdin.mode, expect_mode)

    def test_daemon_context_has_specified_stdout_stream(self):
        """ DaemonContext component should have specified stdout file """
        test_app = self.test_app
        expect_file = self.stream_files_by_name['stdout']
        daemon_context = self.test_instance.daemon_context
        self.failUnlessEqual(expect_file, daemon_context.stdout)

    def test_daemon_context_has_stdout_in_append_mode(self):
        """ DaemonContext component should open stdout file for append """
        expect_mode = 'w+'
        daemon_context = self.test_instance.daemon_context
        self.failUnlessIn(daemon_context.stdout.mode, expect_mode)

    def test_daemon_context_has_specified_stderr_stream(self):
        """ DaemonContext component should have specified stderr file """
        test_app = self.test_app
        expect_file = self.stream_files_by_name['stderr']
        daemon_context = self.test_instance.daemon_context
        self.failUnlessEqual(expect_file, daemon_context.stderr)

    def test_daemon_context_has_stderr_in_append_mode(self):
        """ DaemonContext component should open stderr file for append """
        expect_mode = 'w+'
        daemon_context = self.test_instance.daemon_context
        self.failUnlessIn(daemon_context.stderr.mode, expect_mode)


class Runner_parse_args_TestCase(scaffold.TestCase):
    """ Test cases for Runner.parse_args method """

    def setUp(self):
        """ Set up test fixtures """
        setup_runner_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_emits_usage_message_if_insufficient_args(self):
        """ Should emit a usage message and exit if too few arguments """
        instance = self.test_instance
        argv = ['fooprog']
        scaffold.mock(
            "sys.argv",
            mock_obj=argv,
            tracker=self.mock_tracker)
        expect_stderr_output = """\
            usage: ...
            """
        self.failUnlessRaises(
            SystemExit,
            instance.parse_args)
        self.failUnlessOutputCheckerMatch(
            expect_stderr_output, self.mock_stderr.getvalue())

    def test_emits_usage_message_if_unknown_action_arg(self):
        """ Should emit a usage message and exit if unknown action """
        instance = self.test_instance
        argv = ['fooprog', 'bogus']
        scaffold.mock(
            "sys.argv",
            mock_obj=argv,
            tracker=self.mock_tracker)
        expect_stderr_output = """\
            usage: ...
            """
        self.failUnlessRaises(
            SystemExit,
            instance.parse_args)
        self.failUnlessOutputCheckerMatch(
            expect_stderr_output, self.mock_stderr.getvalue())

    def test_should_parse_system_argv_by_default(self):
        """ Should parse sys.argv by default """
        instance = self.test_instance
        expect_action = 'start'
        argv = self.valid_argv_params['start']
        scaffold.mock(
            "sys.argv",
            mock_obj=argv,
            tracker=self.mock_tracker)
        instance.parse_args()
        self.failUnlessEqual(expect_action, instance.action)

    def test_sets_action_from_first_argument(self):
        """ Should set action from first commandline argument """
        instance = self.test_instance
        for name, argv in self.valid_argv_params.items():
            expect_action = name
            instance.parse_args(argv)
            self.failUnlessEqual(expect_action, instance.action)


class Runner_do_action_TestCase(scaffold.TestCase):
    """ Test cases for Runner.do_action method """

    def setUp(self):
        """ Set up test fixtures """
        setup_runner_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_raises_error_if_unknown_action(self):
        """ Should emit a usage message and exit if too few arguments """
        instance = self.test_instance
        instance.action = 'bogus'
        expect_error = ValueError
        self.failUnlessRaises(
            expect_error,
            instance.do_action)

    def test_requests_daemon_start_if_start_action(self):
        """ Should request the daemon to start if action is 'start' """
        instance = self.test_instance
        instance.action = 'start'
        expect_mock_output = """\
            ...
            Called DaemonContext.start()
            ...
            """
        instance.do_action()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_requests_app_run_if_start_Action(self):
        """ Should request the application to run if action is 'start' """
        instance = self.test_instance
        instance.action = 'start'
        expect_mock_output = """\
            ...
            Called TestApp.run()
            """
        instance.do_action()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_requests_daemon_stop_if_stop_action(self):
        """ Should request the daemon to stop if action is 'stop' """
        instance = self.test_instance
        instance.action = 'stop'
        expect_mock_output = """\
            ...
            Called DaemonContext.stop()
            """
        instance.do_action()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_requests_stop_then_start_if_restart_action(self):
        """ Should request stop, then start, if action is 'restart' """
        instance = self.test_instance
        instance.action = 'restart'
        scaffold.mock(
            "daemon.runner.Runner._start",
            tracker=self.mock_tracker)
        scaffold.mock(
            "daemon.runner.Runner._stop",
            tracker=self.mock_tracker)
        expect_mock_output = """\
            ...
            Called daemon.runner.Runner._stop()
            Called daemon.runner.Runner._start()
            """
        instance.do_action()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())
