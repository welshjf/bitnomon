# Import our chosen Qt binding first so pyqtgraph doesn't have to guess
from qtwrapper import QtCore
import pyqtgraph

class RRDPlotItem(pyqtgraph.PlotDataItem):

    def __init__(self, *args, **kwargs):
        super(RRDPlotItem, self).__init__(*args, **kwargs)

    def getData(self):
        # Stub
        return super(RRDPlotItem, self).getData()
