#!/usr/bin/python

import sys
import time
import random

sys.path.insert(0, '..')
import rrdmodel

m = rrdmodel.RRDModel('.')

year_minutes = 60*24*365
start = (int(time.time()) - year_minutes*60) * 1000
recv_total = 0
send_total = 0
one_percent = year_minutes / 100
for minute in xrange(year_minutes):
    recv_total += int(random.random()**8 * 20000000)
    send_total += int(random.random()**8 * 20000000)
    m.update(start + 60000*minute, (recv_total, send_total))
    percent, remainder = divmod(minute, one_percent)
    if remainder == 0:
        sys.stderr.write('\r' + str(percent) + '%')
sys.stderr.write('\n')
