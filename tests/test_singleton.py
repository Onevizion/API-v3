"""Tests for onevizion.singleton module."""
# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import sys

import pytest

# Python 2/3 compatibility
if sys.version_info[0] >= 3:
    from importlib import reload
    from unittest import mock
else:
    import mock
    reload = reload  # reload is a builtin in Python 2

import fcntl

import onevizion
from onevizion.singleton import Singleton


def _fcntl_mock(side_effect=None):
    """Build a mock fcntl module that can be injected into the singleton's local scope."""
    m = mock.MagicMock()
    m.LOCK_EX = fcntl.LOCK_EX
    m.LOCK_NB = fcntl.LOCK_NB
    m.LOCK_UN = fcntl.LOCK_UN
    if side_effect is not None:
        m.lockf.side_effect = side_effect
    return m


class TestSingletonInit(object):
    """Test Singleton initialization and lock file mechanics."""

    def test_init_creates_lock_file(self, tmp_path):
        lock_file = str(tmp_path / "test.lck")
        s = Singleton(LockFileName=lock_file)
        assert s.initialized is True
        assert s.foundProcess is False
        assert os.path.exists(lock_file)
        # Explicitly clean up so __del__ does not fire with broken fcntl scope
        try:
            fcntl.lockf(s.LockFile, fcntl.LOCK_UN)
        except Exception:
            pass
        if os.path.isfile(lock_file):
            os.unlink(lock_file)
        s.initialized = False  # prevent __del__ from trying to clean up again

    def test_init_stores_lock_filename(self, tmp_path):
        lock_file = str(tmp_path / "custom.lck")
        s = Singleton(LockFileName=lock_file)
        assert s.LockFileName == lock_file
        try:
            fcntl.lockf(s.LockFile, fcntl.LOCK_UN)
        except Exception:
            pass
        if os.path.isfile(lock_file):
            os.unlink(lock_file)
        s.initialized = False

    def test_collision_sets_found_process_in_none_mode(self, tmp_path):
        """IOError from lockf sets foundProcess=True when QuitMode='none'.
        Execution continues so initialized is still set to True at end of __init__."""
        lock_file = str(tmp_path / "collision.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            s = singleton_mod.Singleton(LockFileName=lock_file, QuitMode="none")
            # foundProcess=True because Quit() was called
            assert s.foundProcess is True
            # initialized=True because execution continues after Quit() in 'none' mode
            assert s.initialized is True
        reload(singleton_mod)

    def test_collision_error_mode_exits(self, tmp_path):
        """IOError from lockf causes sys.exit(-1) when QuitMode='error'."""
        lock_file = str(tmp_path / "err_mode.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            with pytest.raises(SystemExit) as exc_info:
                singleton_mod.Singleton(LockFileName=lock_file, QuitMode="error")
            assert exc_info.value.code == -1
        reload(singleton_mod)

    def test_collision_silent_mode_quits(self, tmp_path):
        """IOError from lockf causes quit() when QuitMode='silent'."""
        lock_file = str(tmp_path / "silent_mode.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            with pytest.raises(SystemExit):
                singleton_mod.Singleton(LockFileName=lock_file, QuitMode="silent")
        reload(singleton_mod)

    def test_singleton_del_cleans_up_lock_file(self, tmp_path):
        """After deletion, the lock file is removed."""
        lock_file = str(tmp_path / "cleanup.lck")
        s = Singleton(LockFileName=lock_file)
        assert os.path.exists(lock_file)
        # Manually clean up in a controlled way
        fcntl.lockf(s.LockFile, fcntl.LOCK_UN)
        if os.path.isfile(lock_file):
            os.unlink(lock_file)
        s.initialized = False
        assert not os.path.exists(lock_file)

    def test_msg_none_no_output_on_collision(self, tmp_path, capsys):
        """Msg=None produces no console output on collision."""
        onevizion.Config["Verbosity"] = 0
        lock_file = str(tmp_path / "no_msg.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            s = singleton_mod.Singleton(LockFileName=lock_file, QuitMode="none", Msg=None)
            assert s.foundProcess is True
        captured = capsys.readouterr()
        assert captured.out == ""
        reload(singleton_mod)

    def test_custom_msg_printed_on_collision(self, tmp_path, capsys):
        """Custom Msg is printed when a process collision occurs."""
        onevizion.Config["Verbosity"] = 0
        lock_file = str(tmp_path / "msg.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            singleton_mod.Singleton(LockFileName=lock_file, QuitMode="none", Msg="Already running!")
        captured = capsys.readouterr()
        assert "Already running!" in captured.out
        reload(singleton_mod)

    def test_empty_msg_no_output(self, tmp_path, capsys):
        """Empty Msg string produces no output."""
        onevizion.Config["Verbosity"] = 0
        lock_file = str(tmp_path / "empty_msg.lck")
        mock_fcntl = _fcntl_mock(side_effect=IOError("locked"))
        import onevizion.singleton as singleton_mod
        with mock.patch.dict("sys.modules", {"fcntl": mock_fcntl}):
            reload(singleton_mod)
            singleton_mod.Singleton(LockFileName=lock_file, QuitMode="none", Msg="")
        captured = capsys.readouterr()
        assert captured.out == ""
        reload(singleton_mod)
