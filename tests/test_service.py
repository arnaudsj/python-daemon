# -*- coding: utf-8 -*-
#
# tests/test_service.py
#
# Copyright © 2009 Ben Finney <ben+python@benfinney.id.au>
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Unit test for service module
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

import daemon
from daemon import service


def setup_service_fixtures(testcase):
    """ Set up common test fixtures for Service test case """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    setup_streams_fixtures(testcase)

    testcase.mock_pidfile_name = tempfile.mktemp()

    class TestApp(object):

        def __init__(self):
            self.stdin = testcase.stream_file_paths['stdin']
            self.stdout = testcase.stream_file_paths['stdout']
            self.stderr = testcase.stream_file_paths['stderr']
            self.pidfile = testcase.mock_pidfile_name

        def run(self):
            pass

    testcase.TestApp = TestApp

    scaffold.mock(
        "daemon.daemon.DaemonContext",
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

    testcase.test_instance = service.Service(testcase.test_app)


class Service_TestCase(scaffold.TestCase):
    """ Test cases for Service class """

    def setUp(self):
        """ Set up test fixtures """
        setup_service_fixtures(self)
        self.mock_outfile.truncate(0)

        scaffold.mock(
            "service.Service.parse_args",
            tracker=self.mock_tracker)

        self.test_instance = service.Service(self.test_app)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of Service should be created """
        self.failUnlessIsInstance(self.test_instance, service.Service)

    def test_parses_commandline_args(self):
        """ Should parse commandline arguments """
        expect_mock_output = """\
            Called service.Service.parse_args()
            ...
            """
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_has_specified_app(self):
        """ Should have specified application object """
        self.failUnlessIs(self.test_app, self.test_instance.app)

    def test_daemon_context_has_specified_pidfile_name(self):
        """ DaemonContext component should have specified PID file path """
        expect_pidfile_name = self.test_app.pidfile
        daemon_context = self.test_instance.daemon_context
        self.failUnlessEqual(
            expect_pidfile_name, daemon_context.pidfile_name)

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


class Service_parse_args_TestCase(scaffold.TestCase):
    """ Test cases for Service.parse_args method """

    def setUp(self):
        """ Set up test fixtures """
        setup_service_fixtures(self)

        self.mock_stderr = FakeFileDescriptorStringIO()
        scaffold.mock(
            "sys.stderr",
            mock_obj=self.mock_stderr,
            tracker=self.mock_tracker)

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
        expect_exception = SystemExit
        try:
            instance.parse_args()
        except expect_exception:
            pass
        else:
            self.fail("Expected %(expect_exception)r")
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
