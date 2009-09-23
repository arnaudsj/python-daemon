# -*- coding: utf-8 -*-
#
# test/test_pidlockfile.py
# Part of python-daemon, an implementation of PEP 3143.
#
# Copyright © 2008–2009 Ben Finney <ben+python@benfinney.id.au>
#
# This is free software: you may copy, modify, and/or distribute this work
# under the terms of the Python Software Foundation License, version 2 or
# later as published by the Python Software Foundation.
# No warranty expressed or implied. See the file LICENSE.PSF-2 for details.

""" Unit test for pidlockfile module.
    """

import __builtin__
import os
from StringIO import StringIO
import itertools
import tempfile
import errno
import time

import scaffold

from daemon import pidlockfile


class FakeFileDescriptorStringIO(StringIO, object):
    """ A StringIO class that fakes a file descriptor. """

    _fileno_generator = itertools.count()

    def __init__(self, *args, **kwargs):
        self._fileno = self._fileno_generator.next()
        super_instance = super(FakeFileDescriptorStringIO, self)
        super_instance.__init__(*args, **kwargs)

    def fileno(self):
        return self._fileno


class Exception_TestCase(scaffold.Exception_TestCase):
    """ Test cases for module exception classes. """

    def __init__(self, *args, **kwargs):
        """ Set up a new instance. """
        super(Exception_TestCase, self).__init__(*args, **kwargs)

        self.valid_exceptions = {
            pidlockfile.PIDFileError: dict(
                min_args = 1,
                types = (Exception,),
                ),
            pidlockfile.PIDFileParseError: dict(
                min_args = 2,
                types = (pidlockfile.PIDFileError, ValueError),
                ),
            }


def setup_pidfile_fixtures(testcase):
    """ Set up common fixtures for PID file test cases. """
    testcase.mock_tracker = scaffold.MockTracker()

    testcase.mock_current_pid = 235
    testcase.mock_other_pid = 8642
    testcase.mock_pidfile_empty = FakeFileDescriptorStringIO()
    testcase.mock_pidfile_current = FakeFileDescriptorStringIO(
        "%(mock_current_pid)d\n" % vars(testcase))
    testcase.mock_pidfile_other = FakeFileDescriptorStringIO(
        "%(mock_other_pid)d\n" % vars(testcase))
    testcase.mock_pidfile_bogus = FakeFileDescriptorStringIO(
        "b0gUs")
    testcase.mock_pidfile_path = tempfile.mktemp()

    testcase.mock_pidfile = NotImplemented

    scaffold.mock(
        "os.getpid",
        returns=testcase.mock_current_pid,
        tracker=testcase.mock_tracker)

    def mock_path_exists(path):
        if path == testcase.mock_pidfile_path:
            result = testcase.pidfile_path_exists_func()
        else:
            result = False
        return result

    testcase.pidfile_path_exists_func = (lambda: False)

    scaffold.mock(
        "os.path.exists",
        mock_obj=mock_path_exists)

    def mock_pidfile_open_nonexist(filename, mode, buffering):
        if 'r' in mode:
            raise IOError(errno.ENOENT, "No such file %(filename)r" % vars())
        else:
            result = testcase.mock_pidfile
        return result

    def mock_pidfile_open_read_denied(filename, mode, buffering):
        if 'r' in mode:
            raise IOError(errno.EPERM, "Read denied on %(filename)r" % vars())
        else:
            result = testcase.mock_pidfile
        return result

    def mock_pidfile_open_okay(filename, mode, buffering):
        result = testcase.mock_pidfile
        return result

    testcase.mock_pidfile_open_nonexist = mock_pidfile_open_nonexist
    testcase.mock_pidfile_open_read_denied = mock_pidfile_open_read_denied
    testcase.mock_pidfile_open_okay = mock_pidfile_open_okay

    testcase.pidfile_open_func = NotImplemented

    def mock_open(filename, mode='r', buffering=None):
        if filename == testcase.mock_pidfile_path:
            result = testcase.pidfile_open_func(filename, mode, buffering)
        else:
            result = FakeFileDescriptorStringIO()
        return result

    scaffold.mock(
        "__builtin__.open",
        returns_func=mock_open,
        tracker=testcase.mock_tracker)

    def mock_pidfile_os_open_nonexist(filename, flags, mode):
        if (flags & os.O_CREAT):
            result = testcase.mock_pidfile.fileno()
        else:
            raise OSError(errno.ENOENT, "No such file %(filename)r" % vars())
        return result

    def mock_pidfile_os_open_read_denied(filename, flags, mode):
        if (flags & os.O_CREAT):
            result = testcase.mock_pidfile.fileno()
        else:
            raise IOError(errno.EPERM, "Read denied on %(filename)r" % vars())
        return result

    def mock_pidfile_os_open_okay(filename, flags, mode):
        result = testcase.mock_pidfile.fileno()
        return result

    def mock_os_open(filename, flags, mode=None):
        if filename == testcase.mock_pidfile_path:
            result = testcase.pidfile_os_open_func(filename, flags, mode)
        else:
            result = FakeFileDescriptorStringIO().fileno()
        return result

    testcase.mock_pidfile_os_open_nonexist = mock_pidfile_os_open_nonexist
    testcase.mock_pidfile_os_open_read_denied = mock_pidfile_os_open_read_denied
    testcase.mock_pidfile_os_open_okay = mock_pidfile_os_open_okay

    testcase.pidfile_os_open_func = NotImplemented

    scaffold.mock(
        "os.open",
        returns_func=mock_os_open,
        tracker=testcase.mock_tracker)

    def mock_os_fdopen(fd, mode='r', buffering=None):
        if fd == testcase.mock_pidfile.fileno():
            result = testcase.mock_pidfile
        else:
            raise OSError(errno.EBADF, "Bad file descriptor")
        return result

    scaffold.mock(
        "os.fdopen",
        returns_func=mock_os_fdopen,
        tracker=testcase.mock_tracker)


def setup_pidlockfile_fixtures(testcase):
    """ Set up common fixtures for PIDLockFile test cases. """

    setup_pidfile_fixtures(testcase)

    testcase.pidlockfile_args = dict(
        path=testcase.mock_pidfile_path,
        )
    testcase.test_instance = pidlockfile.PIDLockFile(
        **testcase.pidlockfile_args)

    scaffold.mock(
        "pidlockfile.write_pid_to_pidfile",
        tracker=testcase.mock_tracker)
    scaffold.mock(
        "pidlockfile.remove_existing_pidfile",
        tracker=testcase.mock_tracker)


class PIDLockFile_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile class. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_instantiate(self):
        """ New instance of PIDLockFile should be created. """
        instance = self.test_instance
        self.failUnlessIsInstance(instance, pidlockfile.PIDLockFile)

    def test_has_specified_path(self):
        """ Should have specified path. """
        instance = self.test_instance
        expect_path = self.mock_pidfile_path
        self.failUnlessEqual(expect_path, instance.path)


class PIDLockFile_read_pid_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.read_pid method. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_other
        self.pidfile_open_func = self.mock_pidfile_open_okay

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_gets_pid_via_read_pid_from_pidfile(self):
        """ Should get PID via read_pid_from_pidfile. """
        instance = self.test_instance
        test_pid = self.mock_other_pid
        expect_pid = test_pid
        result = instance.read_pid()
        self.failUnlessEqual(expect_pid, result)


class PIDLockFile_is_locked_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.is_locked function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_other

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_returns_true_if_pid_file(self):
        """ Should return True if PID file exists. """
        instance = self.test_instance
        expect_result = True
        self.pidfile_path_exists_func = (lambda: True)
        result = instance.is_locked()
        self.failUnlessEqual(expect_result, result)

    def test_returns_false_if_no_pid_file(self):
        """ Should return False if PID file does not exist. """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: False)
        result = instance.is_locked()
        self.failUnlessEqual(expect_result, result)


class PIDLockFile_i_am_locking_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.i_am_locking function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_current

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_returns_false_if_no_pid_file(self):
        """ Should return False if PID file does not exist. """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: False)
        self.pidfile_open_func = self.mock_pidfile_open_nonexist
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)

    def test_raises_error_if_pid_file_read_fails(self):
        """ Should raise error if PID file read fails. """
        instance = self.test_instance
        expect_result = False
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_read_denied
        expect_error = EnvironmentError
        self.failUnlessRaises(
            expect_error,
            instance.i_am_locking)

    def test_raises_error_if_pid_file_empty(self):
        """ Should raise error if PID file is empty. """
        instance = self.test_instance
        expect_result = False
        self.mock_pidfile = self.mock_pidfile_empty
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay
        expect_error = pidlockfile.PIDFileParseError
        self.failUnlessRaises(
            expect_error,
            instance.i_am_locking)

    def test_raises_error_if_pid_file_contains_bogus_pid(self):
        """ Should raise error if PID file contains a bogus PID. """
        instance = self.test_instance
        expect_result = False
        self.mock_pidfile = self.mock_pidfile_bogus
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay
        expect_error = pidlockfile.PIDFileParseError
        self.failUnlessRaises(
            expect_error,
            instance.i_am_locking)

    def test_returns_false_if_pid_file_contains_different_pid(self):
        """ Should return False if PID file contains a different PID. """
        instance = self.test_instance
        expect_result = False
        self.mock_pidfile = self.mock_pidfile_other
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)

    def test_returns_true_if_pid_file_contains_current_pid(self):
        """ Should return True if PID file contains the current PID. """
        instance = self.test_instance
        expect_result = True
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay
        result = instance.i_am_locking()
        self.failUnlessEqual(expect_result, result)


class PIDLockFile_acquire_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.acquire function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.pidfile_path_exists_func = (lambda: False)
        self.pidfile_open_func = self.mock_pidfile_open_nonexist

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_zero_timeout_raises_already_locked_if_file_exists(self):
        """ Should raise AlreadyLocked with timeout 0 if PID file exists. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: True)
        expect_error = pidlockfile.AlreadyLocked
        self.failUnlessRaises(
            expect_error,
            instance.acquire, timeout=0)

    def test_writes_pid_to_specified_file(self):
        """ Should request writing current PID to specified file. """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called pidlockfile.write_pid_to_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.acquire()
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)

    def test_raises_lock_failed_on_write_error(self):
        """ Should raise LockFailed error if write fails. """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.EBUSY, "Bad stuff", pidfile_path)
        pidlockfile.write_pid_to_pidfile.mock_raises = mock_error
        expect_error = pidlockfile.LockFailed
        self.failUnlessRaises(
            expect_error,
            instance.acquire)


class PIDLockFile_acquire_with_timeout_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.acquire function with a timeout. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.pidfile_path_exists_func = (lambda: False)
        self.pidfile_open_func = self.mock_pidfile_open_nonexist

        self.test_poll_interval = 0.5
        self.mock_time_tracker = scaffold.MockTracker()
        self.mock_system_time = 0.0
        scaffold.mock(
            "time.time",
            returns_func=self.mock_time,
            tracker=self.mock_time_tracker)
        scaffold.mock(
            "time.sleep",
            returns_func=self.mock_sleep,
            tracker=self.mock_time_tracker)

        self.mock_lock_state = False
        def mock_write_pidfile(path):
            self.mock_lock_state = True

        scaffold.mock(
            "pidlockfile.write_pid_to_pidfile",
            returns_func=mock_write_pidfile,
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def mock_time(self):
        """ Mock function for getting system time. """
        return self.mock_system_time

    def mock_sleep(self, seconds):
        """ Mock function to sleep the current process. """
        self.mock_system_time += seconds

    def test_no_timeout_writes_pidfile_if_file_not_exist(self):
        """ With no timeout, should write PID file if file does not exist. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        instance.acquire()
        self.failUnlessEqual(True, self.mock_lock_state)

    def test_no_timeout_waits_indefinitely_if_file_exists(self):
        """ With no timeout, should wait indefinitely while file exists. """
        instance = self.test_instance
        def path_exists_after_num_polls(num_polls):
            for i in range(num_polls):
                yield True
            yield False
        num_polls_before_available = 100
        self.pidfile_path_exists_func = path_exists_after_num_polls(
            num_polls_before_available).next
        instance.poll_interval = self.test_poll_interval
        expect_polls = num_polls_before_available
        expect_mock_output = (
            "Called time.sleep(%(poll_interval)r)\n"
                % vars(instance)
            ) * expect_polls
        instance.acquire()
        self.failUnlessEqual(True, self.mock_lock_state)
        self.failUnlessMockCheckerMatch(
            expect_mock_output, self.mock_time_tracker)

    def test_positive_timeout_writes_pidfile_if_file_not_exist(self):
        """ With +ve timeout, should write PID file if file does not exist. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        test_timeout = 10
        instance.acquire(test_timeout)
        self.failUnlessEqual(True, self.mock_lock_state)

    def test_positive_timeout_raises_error_if_timeout_expires(self):
        """ With +ve timeout, should raise AlreadyLocked if timeout expires. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: True)
        test_timeout = 10
        instance.poll_interval = self.test_poll_interval
        expect_polls = int(test_timeout / self.test_poll_interval) + 1
        expect_mock_output = (
            "Called time.time()\n" + (
                "Called time.time()\n" +
                "Called time.sleep(%(poll_interval)r)\n"
                    % vars(instance)
                ) * expect_polls
            + "Called time.time()\n"
            )
        expect_error = pidlockfile.AlreadyLocked
        self.failUnlessRaises(
            expect_error,
            instance.acquire, test_timeout)
        self.failUnlessMockCheckerMatch(
            expect_mock_output, self.mock_time_tracker)


class PIDLockFile_release_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.release function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_current
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_raises_not_locked_if_no_pid_file(self):
        """ Should raise NotLocked error if PID file does not exist. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        expect_error = pidlockfile.NotLocked
        self.failUnlessRaises(
            expect_error,
            instance.release)

    def test_raises_not_my_lock_if_pid_file_not_locked_by_this_lock(self):
        """ Should raise NotMyLock error if PID file not locked by me. """
        instance = self.test_instance
        self.mock_pidfile = self.mock_pidfile_other
        expect_error = pidlockfile.NotMyLock
        self.failUnlessRaises(
            expect_error,
            instance.release)

    def test_removes_existing_pidfile(self):
        """ Should request removal of specified PID file. """
        instance = self.test_instance
        self.mock_pidfile = self.mock_pidfile_current
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called pidlockfile.remove_existing_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.release()
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)


class PIDLockFile_break_lock_TestCase(scaffold.TestCase):
    """ Test cases for PIDLockFile.break_lock function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidlockfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_other
        self.pidfile_path_exists_func = (lambda: True)
        self.pidfile_open_func = self.mock_pidfile_open_okay

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_returns_none_if_no_pid_file(self):
        """ Should return None if PID file does not exist. """
        instance = self.test_instance
        self.pidfile_path_exists_func = (lambda: False)
        expect_result = None
        result = instance.break_lock()
        self.failUnlessEqual(expect_result, result)

    def test_removes_existing_pidfile(self):
        """ Should request removal of specified PID file. """
        instance = self.test_instance
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            ...
            Called pidlockfile.remove_existing_pidfile(%(pidfile_path)r)
            """ % vars()
        instance.break_lock()
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)


class pidfile_exists_TestCase(scaffold.TestCase):
    """ Test cases for pidfile_exists function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_other

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_returns_true_when_pidfile_exists(self):
        """ Should return True when pidfile exists. """
        self.pidfile_path_exists_func = (lambda: True)
        result = pidlockfile.pidfile_exists(self.mock_pidfile_path)
        self.failUnless(result)

    def test_returns_false_when_no_pidfile_exists(self):
        """ Should return False when pidfile does not exist. """
        self.pidfile_path_exists_func = (lambda: False)
        result = pidlockfile.pidfile_exists(self.mock_pidfile_path)
        self.failIf(result)


class read_pid_from_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for read_pid_from_pidfile function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_other
        self.pidfile_open_func = self.mock_pidfile_open_okay

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified pidfile filename. """
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            Called __builtin__.open(%(pidfile_path)r, 'r')
            """ % vars()
        dummy = pidlockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)

    def test_reads_pid_from_file(self):
        """ Should read the PID from the specified file. """
        pidfile_path = self.mock_pidfile_path
        expect_pid = self.mock_other_pid
        pid = pidlockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_pid, pid)

    def test_returns_none_when_file_nonexist(self):
        """ Should return None when the PID file does not exist. """
        pidfile_path = self.mock_pidfile_path
        self.pidfile_open_func = self.mock_pidfile_open_nonexist
        pid = pidlockfile.read_pid_from_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessIs(None, pid)

    def test_raises_error_when_file_read_fails(self):
        """ Should raise error when the PID file read fails. """
        pidfile_path = self.mock_pidfile_path
        self.pidfile_open_func = self.mock_pidfile_open_read_denied
        expect_error = EnvironmentError
        self.failUnlessRaises(
            expect_error,
            pidlockfile.read_pid_from_pidfile, pidfile_path)

    def test_raises_error_when_file_empty(self):
        """ Should raise error when the PID file is empty. """
        pidfile_path = self.mock_pidfile_path
        self.mock_pidfile = self.mock_pidfile_empty
        self.pidfile_open_func = self.mock_pidfile_open_okay
        expect_error = pidlockfile.PIDFileParseError
        self.failUnlessRaises(
            expect_error,
            pidlockfile.read_pid_from_pidfile, pidfile_path)

    def test_raises_error_when_file_contents_invalid(self):
        """ Should raise error when the PID file contents are invalid. """
        pidfile_path = self.mock_pidfile_path
        self.mock_pidfile = self.mock_pidfile_bogus
        self.pidfile_open_func = self.mock_pidfile_open_okay
        expect_error = pidlockfile.PIDFileParseError
        self.failUnlessRaises(
            expect_error,
            pidlockfile.read_pid_from_pidfile, pidfile_path)


class remove_existing_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for remove_existing_pidfile function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_current
        self.pidfile_open_func = self.mock_pidfile_open_okay

        scaffold.mock(
            "os.remove",
            tracker=self.mock_tracker)

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_removes_specified_filename(self):
        """ Should attempt to remove specified PID file filename. """
        pidfile_path = self.mock_pidfile_path
        expect_mock_output = """\
            Called os.remove(%(pidfile_path)r)
            """ % vars()
        pidlockfile.remove_existing_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)

    def test_ignores_file_not_exist_error(self):
        """ Should ignore error if file does not exist. """
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.ENOENT, "Not there", pidfile_path)
        os.remove.mock_raises = mock_error
        expect_mock_output = """\
            Called os.remove(%(pidfile_path)r)
            """ % vars()
        pidlockfile.remove_existing_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)

    def test_propagates_arbitrary_oserror(self):
        """ Should propagate any OSError other than ENOENT. """
        pidfile_path = self.mock_pidfile_path
        mock_error = OSError(errno.EACCES, "Denied", pidfile_path)
        os.remove.mock_raises = mock_error
        self.failUnlessRaises(
            type(mock_error),
            pidlockfile.remove_existing_pidfile,
            pidfile_path)


class write_pid_to_pidfile_TestCase(scaffold.TestCase):
    """ Test cases for write_pid_to_pidfile function. """

    def setUp(self):
        """ Set up test fixtures. """
        setup_pidfile_fixtures(self)
        self.mock_pidfile = self.mock_pidfile_current
        self.pidfile_open_func = self.mock_pidfile_open_nonexist
        self.pidfile_os_open_func = self.mock_pidfile_os_open_nonexist

    def tearDown(self):
        """ Tear down test fixtures. """
        scaffold.mock_restore()

    def test_opens_specified_filename(self):
        """ Should attempt to open specified PID file filename. """
        pidfile_path = self.mock_pidfile_path
        expect_flags = (os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        expect_mode = 0644
        expect_mock_output = """\
            Called os.open(%(pidfile_path)r, %(expect_flags)r, %(expect_mode)r)
            ...
            """ % vars()
        pidlockfile.write_pid_to_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)

    def test_writes_pid_to_file(self):
        """ Should write the current PID to the specified file. """
        pidfile_path = self.mock_pidfile_path
        self.mock_pidfile.close = scaffold.Mock(
            "mock_pidfile.close",
            tracker=self.mock_tracker)
        expect_line = "%(mock_current_pid)d\n" % vars(self)
        pidlockfile.write_pid_to_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessEqual(expect_line, self.mock_pidfile.getvalue())

    def test_closes_file_after_write(self):
        """ Should close the specified file after writing. """
        pidfile_path = self.mock_pidfile_path
        self.mock_pidfile.write = scaffold.Mock(
            "mock_pidfile.write",
            tracker=self.mock_tracker)
        self.mock_pidfile.close = scaffold.Mock(
            "mock_pidfile.close",
            tracker=self.mock_tracker)
        expect_mock_output = """\
            ...
            Called mock_pidfile.write(...)
            Called mock_pidfile.close()
            """ % vars()
        pidlockfile.write_pid_to_pidfile(pidfile_path)
        scaffold.mock_restore()
        self.failUnlessMockCheckerMatch(expect_mock_output)
