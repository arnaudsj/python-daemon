# -*- coding: utf-8 -*-
#
# tests/test_lockfile.py
#
# Copyright © 2008–2009 Ben Finney <ben+python@benfinney.id.au>
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Unit test for lockfile module
"""

import __builtin__
import os
import sys
from StringIO import StringIO
import tempfile
import errno

import scaffold
from test_daemon import (
    FakeFileHandleStringIO,
    )

from daemon import lockfile


class Exception_TestCase(scaffold.Exception_TestCase):
    """ Test cases for module exception classes. """

    def __init__(self, *args, **kwargs):
        """ Set up a new instance """
        super(Exception_TestCase, self).__init__(*args, **kwargs)
        self.valid_exceptions = {
            lockfile.AlreadyLocked: dict(
                min_args = 0,
                types = [Exception,],
                ),
            lockfile.LockFailed: dict(
                min_args = 0,
                types = [Exception,],
                ),
            lockfile.NotLocked: dict(
                min_args = 0,
                types = [Exception,],
                ),
            lockfile.NotMyLock: dict(
                min_args = 0,
                types = [Exception,],
                ),
            }


def setup_pidlockfile_fixtures(testcase):
    """ Set up common fixtures for PIDLockFile test cases """

    setup_pidfile_fixtures(testcase)

    args = dict(
        path=testcase.mock_pidfile_path,
        )

    testcase.test_instance = lockfile.PIDLockFile(**args)

    def mock_os_path_exists(path):
        if path == testcase.mock_pidfile_path:
            result = testcase.pidfile_path_exists_func()
        else:
            result = False
        return result

    scaffold.mock(
        "os.path.exists",
        returns_func=mock_os_path_exists,
        tracker=testcase.mock_tracker)

    scaffold.mock(
        "lockfile.write_pid_to_pidfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "lockfile.remove_existing_pidfile",
        tracker=testcase.mock_tracker)

class PIDLockFile_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile class """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of PIDLockFile should be created """
        instance = self.test_instance
        self.failUnlessIsInstance(instance, lockfile.PIDLockFile)

    def test_has_specified_path(self):
        """ Should have specified path """
        instance = self.test_instance
        expect_path = self.mock_pidfile_path
        self.failUnlessEqual(expect_path, instance.path)


class PIDLockFile_is_locked_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.is_locked function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_true_if_pid_file(self):
        """ Should return True if PID file exists """
        instance = self.test_instance
        expect_result = True
        self.pidfile_path_exists_func = (lambda: True)
        result = instance.is_locked()
        self.failUnlessEqual(expect_result, result)

    def test_returns_false_if_no_pid_file(self):
        """ Should return False if PID file does not exist """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: False)
        result = instance.is_locked()
        self.failUnlessEqual(expect_result, result)


class PIDLockFile_i_am_locking_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.i_am_locking function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_false_if_no_pid_file(self):
        """ Should return False if PID file does not exist """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: False)
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)

    def test_returns_false_if_pid_file_contains_bogus_pid(self):
        """ Should return False if PID file contains a bogus PID """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_exist
        self.mock_pidfile.write("bogus\n")
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)

    def test_returns_false_if_pid_file_contains_different_pid(self):
        """ Should return False if PID file contains a different PID """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_exist
        self.mock_pidfile.write("0\n")
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)

    def test_returns_true_if_pid_file_contains_current_pid(self):
        """ Should return True if PID file contains the current PID """
        instance = self.test_instance
        expect_result = True
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_exist
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)


class PIDLockFile_acquire_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.acquire function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)
        self.pidfile_path_exists_func = (lambda: False)
        self.pidfile_open_func = self.mock_pidfile_open_nonexist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_raises_already_locked_if_file_exists(self):
        """ Should raise AlreadyLocked error if PID file exists """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: True)
        expect_error = lockfile.AlreadyLocked
        self.failUnlessRaises(
            expect_error,
            instance.acquire)

    def test_writes_pid_to_specified_file(self):
        """ Should request writing current PID to specified file """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called lockfile.write_pid_to_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.acquire()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_raises_lock_failed_on_write_error(self):
        """ Should raise LockFailed error if write fails """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.EBUSY, "Bad stuff", pidfile_path)
        lockfile.write_pid_to_pidfile.mock_raises = mock_error
        expect_error = lockfile.LockFailed
        self.failUnlessRaises(
            expect_error,
            instance.acquire)


class PIDLockFile_release_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.release function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_exist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_raises_not_locked_if_no_pid_file(self):
        """ Should raise NotLocked error if PID file does not exist """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        expect_error = lockfile.NotLocked
        self.failUnlessRaises(
            expect_error,
            instance.release)

    def test_raises_not_my_lock_if_pid_file_not_locked_by_this_lock(self):
        """ Should raise NotMyLock error if PID file not locked by me """
        instance = self.test_instance
        self.mock_pidfile = FakeFileHandleStringIO("bogus\n")
        expect_error = lockfile.NotMyLock
        self.failUnlessRaises(
            expect_error,
            instance.release)

    def test_removes_existing_pidfile(self):
        """ Should request removal of specified PID file """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called lockfile.remove_existing_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.release()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


class PIDLockFile_release_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.release function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidlockfile_fixtures(self)
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_exist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_none_if_no_pid_file(self):
        """ Should return None if PID file does not exist """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        expect_result = None
        result = instance.break_lock()
        self.failUnlessEqual(expect_result, result)

    def test_removes_existing_pidfile(self):
        """ Should request removal of specified PID file """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called lockfile.remove_existing_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.break_lock()
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())


def setup_pidfile_fixtures(testcase):
    """ Set up common fixtures for PID file test cases """

    testcase.mock_outfile = StringIO()
    testcase.mock_tracker = scaffold.MockTracker(
        testcase.mock_outfile)

    testcase.mock_pid = 235
    testcase.mock_pidfile_path = tempfile.mktemp()
    testcase.mock_pidfile = FakeFileHandleStringIO(
        "%(mock_pid)d\n" % vars(testcase))

    scaffold.mock(
        "os.getpid",
        returns=testcase.mock_pid,
        tracker=testcase.mock_tracker)

    def mock_path_exists(path):
        if path == testcase.mock_pidfile_path:
            result = testcase.pidfile_exists_func(path)
        else:
            result = False
        return result

    testcase.pidfile_exists_func = (lambda p: False)

    scaffold.mock(
        "os.path.exists",
        mock_obj=mock_path_exists)

    def mock_pidfile_open_nonexist(filename, mode, buffering):
        if 'r' in mode:
            raise IOError("No such file %(filename)r" % vars())
        else:
            result = testcase.mock_pidfile
        return result

    def mock_pidfile_open_exist(filename, mode, buffering):
        pidfile = testcase.mock_pidfile
        return pidfile

    testcase.mock_pidfile_open_nonexist = mock_pidfile_open_nonexist
    testcase.mock_pidfile_open_exist = mock_pidfile_open_exist

    testcase.pidfile_open_func = mock_pidfile_open_nonexist

    def mock_open(filename, mode='r', buffering=None):
        if filename == testcase.mock_pidfile_path:
            result = testcase.pidfile_open_func(filename, mode, buffering)
        else:
            result = FakeFileHandleStringIO()
        return result

    scaffold.mock(
        "__builtin__.open",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)


class pidfile_exists_TestCase(scaffold.TestCase):
    """ Test cases for pidfile_exists function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_returns_true_when_pidfile_exists(self):
        """ Should return True when pidfile exists """
        self.pidfile_exists_func = (lambda p: True)
        result = lockfile.pidfile_exists(self.mock_pidfile_path)
        self.failUnless(result)

    def test_returns_false_when_no_pidfile_exists(self):
        """ Should return False when pidfile does not exist """
        self.pidfile_exists_func = (lambda p: False)
        result = lockfile.pidfile_exists(self.mock_pidfile_path)
        self.failIf(result)


class read_pid_from_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for read_pid_from_pidfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidfile_fixtures(self)
        self.pidfile_open_func = self.mock_pidfile_open_exist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified pidfile filename """
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            Called __builtin__.open(%(pidfile_path)r, 'r')
            """ % vars()
        dummy = lockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_reads_pid_from_file(self):
        """ Should read the PID from the specified file """
        pidfile_path = self.mock_pidfile_path
        expect_pid = self.mock_pid
        pid = lockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_pid, pid)

    def test_returns_none_when_file_nonexist(self):
        """ Should return None when the PID file does not exist """
        pidfile_path = self.mock_pidfile_path
        self.pidfile_open_func = self.mock_pidfile_open_nonexist
        pid = lockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessIs(None, pid)


class remove_existing_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for remove_existing_pidfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidfile_fixtures(self)
        self.pidfile_open_func = self.mock_pidfile_open_exist

        scaffold.mock(
            "os.remove",
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_removes_specified_filename(self):
        """ Should attempt to remove specified PID file filename """
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            Called os.remove(%(pidfile_path)r)
            """ % vars()
        lockfile.remove_existing_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_ignores_file_not_exist_error(self):
        """ Should ignore error if file does not exist """
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.ENOENT, "Not there", pidfile_path)
        os.remove.mock_raises = mock_error
        expect_mock_output = """\
            Called os.remove(%(pidfile_path)r)
            """ % vars()
        lockfile.remove_existing_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_propagates_arbitrary_oserror(self):
        """ Should propagate any OSError other than ENOENT """
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.EACCES, "Denied", pidfile_path)
        os.remove.mock_raises = mock_error
        self.failUnlessRaises(
            mock_error.__class__,
            lockfile.remove_existing_pidfile,
            pidfile_path)


class write_pid_to_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for write_pid_to_pidfile function """

    def setUp(self):
        """ Set up test fixtures """
        setup_pidfile_fixtures(self)
        self.pidfile_open_func = self.mock_pidfile_open_nonexist

    def tearDown(self):
        """ Tear down test fixtures """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified PID file filename """
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            Called __builtin__.open(%(pidfile_path)r, 'w')
            ...
            """ % vars()
        lockfile.write_pid_to_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessOutputCheckerMatch(
            expect_mock_output, self.mock_outfile.getvalue())

    def test_writes_pid_to_file(self):
        """ Should write the current PID to the specified file """
        pidfile_path = self.mock_pidfile_path
        expect_line = "%(mock_pid)d\n" % vars(self)
        lockfile.write_pid_to_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_line, self.mock_pidfile.getvalue())
