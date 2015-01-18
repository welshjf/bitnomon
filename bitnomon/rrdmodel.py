# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

import os
import time
import decimal

import rrdtool

class RRDModel(object):

    "Round-robin database model."

    # Needs refactoring into a generic RRDModel base class and a specific
    # implementation for traffic data.

    step = 60
    consolidation = (
        (1, 360),    # every minute for 6 hours
        (10, 432),   # every 10 mins for 3 days
        (60, 336),   # every hour for 2 weeks
        (1440, 365), # every day for a year
    )

    def __init__(self, data_dir):
        self.rrd_file = os.path.join(data_dir, 'traffic.rrd')
        if not os.path.exists(self.rrd_file):
            self.create()

    def create(self):
        "Create a new RRD file."
        data_source_type = 'DERIVE'
        # would prefer start = 0, but the black magic that is rrd_parsetime.c
        # doesn't accept a second count before 1980
        start = str(86400*365*20)
        step = str(self.step)
        heartbeat = step
        min_val = '0'
        max_val = 'U'
        consolidation = ['RRA:AVERAGE:0.5:%d:%d' % (res, count)
            for (res, count) in self.consolidation]
        args = [self.rrd_file, '--start', start, '--step', step]
        args.append(':'.join(('DS', 'inbound', data_source_type, heartbeat,
                min_val, max_val)))
        args.extend(consolidation)
        args.append(':'.join(('DS', 'outbound', data_source_type, heartbeat,
                min_val, max_val)))
        args.extend(consolidation)
        rrdtool.create(*args)

    def update(self, t, vals):
        """Add a record to the RRD.

        t -- timestamp in milliseconds, or None for current time
        vals -- iterable of sample values"""
        if t is None:
            time_str = 'N'
        else:
            time_str = str(decimal.Decimal(t) / 1000)
        rrdtool.update(self.rrd_file,
                ':'.join([time_str] + [str(v) for v in vals]))

    def fetch(self, start, end=None, resolution=1):
        """Fetch data from the RRD.

        start -- integer start time in seconds since the epoch, or negative for
                 relative to end
        end -- integer end time in seconds since the epoch, or None for current
               time
        resolution -- resolution in seconds"""
        if end is None:
            end = int(time.time())
        if start < 0:
            start += end
        end -= end % resolution
        start -= start % resolution
        time_span, _, values = rrdtool.fetch(self.rrd_file, 'AVERAGE',
                '-s', str(int(start)),
                '-e', str(int(end)),
                '-r', str(resolution))
        ts_start, ts_end, ts_res = time_span
        times = range(ts_start, ts_end, ts_res)
        return zip(times, values)

    def fetch_all(self):
        step = self.step
        latest = rrdtool.last(self.rrd_file)
        consolidation = tuple(reversed(sorted(self.consolidation)))
        result = []
        for i in range(len(consolidation)):
            res, count = consolidation[i]
            start = latest - step*res*count
            if i+1 < len(consolidation):
                nextRes, nextCount = consolidation[i+1]
                end = latest - step*nextRes*(nextCount+1)
            else:
                end = latest
            result.extend(self.fetch(start, end, step*res))
        return result

class RRA(object):

    """Simple in-memory round-robin archive.

    RRA(int) -> RRA of the given size, initialized to None.
    RRA(iterable) -> RRA matching the size and contents of iterable."""

    def __init__(self, arg):
        if isinstance(arg, int):
            if arg < 2:
                # Need one item for update() and two for differences()
                raise ValueError("RRA must have at least two items")
            self.data = [None]*arg
            self.oldest = 0
        else:
            self.data = []
            for item in arg:
                self.data.append(item)
            self.oldest = 0

    def __getitem__(self, i):
        if i >= len(self.data) or i < -len(self.data):
            raise IndexError
        return self.data[(self.oldest + i) % len(self.data)]

    def __iter__(self):
        "Return a generator for items, oldest to newest."
        i = self.oldest
        for i in xrange(self.oldest, len(self.data)):
            yield self.data[i]
        for i in xrange(0, self.oldest):
            yield self.data[i]

    def __len__(self):
        return len(self.data)

    def __repr__(self):
        return 'RRA({})'.format(list(self))

    def __str__(self):
        return str(list(self))

    def update(self, v):
        "Insert a new item, overwriting the oldest."
        self.data[self.oldest] = v
        self.oldest += 1
        if self.oldest == len(self.data):
            self.oldest = 0

    def clear(self):
        "Reset all items to None."
        self.data = [None]*len(self.data)
        self.oldest = 0

    def difference(self, i1, i2):
        "Return self[i1] - self[i2], or None if undefined."
        v1 = self[i1]
        if v1 is None:
            return None
        v2 = self[i2]
        if v2 is None:
            return None
        return v1 - v2

    def differences(self, undef_val=None):
        """Return an iterable of the differences between subsequent items.

        undef_val -- value to return instead of None for undefined intervals"""
        return RRADiffSequence(self, undef_val)

class RRADiffSequence(object):
    #pylint: disable=too-few-public-methods

    """Iterable for RRA item differences.

    This can't be implemented as a generator within RRA because random access
    is assumed by pyqtgraph.PlotDataItem.setData."""

    def __init__(self, rra, undef_val):
        self.rra = rra
        self.rra_len = len(rra)
        self.undef_val = undef_val
        self.i = 1

    def __getitem__(self, i):
        if i < 0:
            i += self.rra_len - 1
        if i < 0:
            raise IndexError
        val = self.rra.difference(i+1, i)
        return val if val is not None else self.undef_val

    def __iter__(self):
        "Return a generator for differences, oldest to newest."
        for i in xrange(1, self.rra_len):
            val = self.rra.difference(i, i-1)
            yield val if val is not None else self.undef_val

    def __len__(self):
        return self.rra_len - 1
