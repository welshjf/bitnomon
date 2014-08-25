ifdef(`PYQT',
`from PyQt4 import QtCore, QtGui, QtNetwork
QtCore.Signal = QtCore.pyqtSignal
QtCore.Slot = QtCore.pyqtSlot',
`from PySide import QtCore, QtGui, QtNetwork')
