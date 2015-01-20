# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""Pythonic QSettings wrapper. Smooths over the differences between PySide and
PyQt4 API 2 (does not support PyQt's older QVariant API)."""

import sys
from .qtwrapper import QtCore

class QSettingsGroup(object):
    #pylint: disable=too-few-public-methods

    """Context manager for a QSettings group. Build a model by subclassing this
    and adding properties using qSettingsProperty."""

    def __init__(self, group):
        self.group = group
        self.settings = None

    def __enter__(self):
        self.settings = QtCore.QSettings()
        self.settings.beginGroup(self.group)
        return self

    def __exit__(self, *_):
        self.settings.endGroup()
        del self.settings
        return False

def qSettingsProperty(key, default=None, valueType=None):
    #pylint: disable=missing-docstring

    """Constructs a property for accessing a QSettings value. Specify the
    Python type in valueType for cases where type information may not be
    retained by the backend (bool, int, float)."""

    def getter(self):
        val = self.settings.value(key)
        if val is None:
            return default
        try:
            if valueType is None:
                return val
            elif valueType is bool:
                return val == 'true' or val == True
            else:
                return valueType(val)
        except TypeError:
            sys.stderr.write(
                'qsettings: TypeError getting %s as %s (value: %s)\n' %
                (key, valueType.__name__, repr(val)))
            return None

    def setter(self, value):
        self.settings.setValue(key, value)

    def deleter(self):
        self.settings.remove(key)

    return property(getter, setter, deleter)
