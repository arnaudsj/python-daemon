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

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of Service should be created """
        self.failUnlessIsInstance(self.test_instance, service.Service)

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
