# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""Representation and display of age data"""

# Import our chosen Qt binding first so pyqtgraph doesn't try to guess
from . import qtwrapper #pylint: disable=unused-import
import pyqtgraph
from math import ceil, log

def ageOfTime(now, time):
    """Convert a time in seconds to an age in the standard format,
    based on the current time."""
    return (now-time)/60.

def genericTickSpacing(idealUnitsPerTick):
    """Returns (major, minor) tick spacing such that:
      - both are either one or two times a power of 10
      - major is the least such >= idealUnitsPerTick
      - minor is the next smallest
    """
    l = log(idealUnitsPerTick, 10)
    l_ceil = ceil(l)
    l_frac = l_ceil - l
    powerOfTen = 10**l_ceil
    if l_frac < 0.69897: # log_10(5)
        return (powerOfTen, powerOfTen/5)
    else:
        return (powerOfTen/5, powerOfTen/10)

class AgeAxisItem(pyqtgraph.AxisItem):
    #pylint: disable=too-many-ancestors, too-many-public-methods

    def __init__(self, *args, **kwargs):
        super(AgeAxisItem, self).__init__(*args, **kwargs)
        super(AgeAxisItem, self).enableAutoSIPrefix(False)

    @staticmethod
    def tickSpacing(minVal, maxVal, size):
        idealPxSpacing = size/20+50
        unitsPerPx = (maxVal - minVal)/size
        idealUnitsPerTick = unitsPerPx*idealPxSpacing
        major, minor = genericTickSpacing(idealUnitsPerTick)
        if major < 60:
            return [(major, 0), (minor, 0)]
        elif idealUnitsPerTick < 60:
            return [(60, 0), (10, 0)]
        elif idealUnitsPerTick < 360:
            return [(360, 0), (60, 0)]
        elif idealUnitsPerTick < 720:
            return [(720, 0), (120, 0)]
        elif idealUnitsPerTick < 1440:
            return [(1440, 0), (360, 0)]
        else:
            major, minor = genericTickSpacing(idealUnitsPerTick/1440)
            return [(major*1440, 0), (minor*1440, 0)]

    @staticmethod
    def tickStrings(values, scale, spacing):
        minutePrecision = max(0, int(ceil(-log(spacing, 10))))
        def formatValue(v):
            if v < 0:
                return '-' + formatValue(-v)
            #minutes = v/60.
            hours, minutes = divmod(v, 60.)
            days, hours = divmod(int(hours), 24)
            if days == 0:
                if hours == 0:
                    return '%.*f' % (minutePrecision, minutes)
                else:
                    return '%d:%02.*f' % (hours, minutePrecision, minutes)
            else:
                return '%d:%02d:%02.*f' % (days, hours,
                        minutePrecision, minutes)
        return [formatValue(v) for v in values]
