import sys
import os
import rrdtool

import main

class RRDModel(object):

    def __init__(self):
        self.rrd_file = os.path.join(main.data_dir, 'traffic.rrd')
        if not os.path.exists(self.rrd_file):
            self.create()

    def create(self):
        rrdtool.create(self.rrd_file,
                '--step', '1',
                'DS:inbound:COUNTER:2:0:U',
                'RRA:AVERAGE:0.5:1:1000',
                'RRA:AVERAGE:0.5:2:1000',
                'RRA:AVERAGE:0.5:4:1000',
                'RRA:AVERAGE:0.5:8:1000',
                'RRA:AVERAGE:0.5:16:1000',
                'RRA:AVERAGE:0.5:32:1000',
                'RRA:AVERAGE:0.5:64:1000',
                'RRA:AVERAGE:0.5:128:1000',
                'RRA:AVERAGE:0.5:256:1000',
                'RRA:AVERAGE:0.5:512:1000',
                'RRA:AVERAGE:0.5:1024:1000',
                'RRA:AVERAGE:0.5:2048:1000',
                'RRA:AVERAGE:0.5:4096:1000',
                'RRA:AVERAGE:0.5:8192:1000',
                'RRA:AVERAGE:0.5:16384:1000',
                'RRA:AVERAGE:0.5:32768:1000',
                'DS:outbound:COUNTER:2:0:U',
                'RRA:AVERAGE:0.5:1:1000',
                'RRA:AVERAGE:0.5:2:1000',
                'RRA:AVERAGE:0.5:4:1000',
                'RRA:AVERAGE:0.5:8:1000',
                'RRA:AVERAGE:0.5:16:1000',
                'RRA:AVERAGE:0.5:32:1000',
                'RRA:AVERAGE:0.5:64:1000',
                'RRA:AVERAGE:0.5:128:1000',
                'RRA:AVERAGE:0.5:256:1000',
                'RRA:AVERAGE:0.5:512:1000',
                'RRA:AVERAGE:0.5:1024:1000',
                'RRA:AVERAGE:0.5:2048:1000',
                'RRA:AVERAGE:0.5:4096:1000',
                'RRA:AVERAGE:0.5:8192:1000',
                'RRA:AVERAGE:0.5:16384:1000',
                'RRA:AVERAGE:0.5:32768:1000',
                )
