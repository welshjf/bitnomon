import sip
sip.setapi("QDate", 2)
sip.setapi("QDateTime", 2)
sip.setapi("QString", 2)
sip.setapi("QTextStream", 2)
sip.setapi("QTime", 2)
sip.setapi("QUrl", 2)
sip.setapi("QVariant", 2)
from PyQt4 import QtCore, QtGui, QtNetwork
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot
IS_PYSIDE = False
__version__ = QtCore.PYQT_VERSION_STR
