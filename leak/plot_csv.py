#!/usr/bin/python3

import sys
import pyqtgraph as pg
pg.setConfigOption('antialias',True)

if len(sys.argv) < 2 or sys.argv[1] == '-':
    f = sys.stdin
else:
    f = open(sys.argv[1], 'r')

lines = iter(f)
next(lines)
pairs = map(lambda line: map(int, line.split(',')), lines)
xvals, yvals = zip(*pairs)

f.close()

pg.plot(xvals, yvals, symbol='o')
pg.QtGui.QApplication.exec_()
