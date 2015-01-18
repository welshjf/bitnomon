# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""Help -> About dialog"""

from . import qtwrapper, __version__
import pyqtgraph
import rrdtool

from .ui_about import Ui_aboutDialog

class AboutDialogUi(Ui_aboutDialog):

    """Extends the uic-generated UI class for the "About" dialog to perform
    version string substitution"""

    def retranslateUi(self, aboutDialog):
        super(AboutDialogUi, self).retranslateUi(aboutDialog)
        output_text = self.label.text().format(
            version=__version__,
            home_url='https://www.welshcomputing.com/code/bitnomon.html',
            pg_version=pyqtgraph.__version__,
            pyqt='PySide' if qtwrapper.IS_PYSIDE else 'PyQt',
            pyqt_version=qtwrapper.__version__,
            qt_version=qtwrapper.QtCore.qVersion(),
            rrd_version=rrdtool.__version__,
        )
        self.label.setText(output_text)

class AboutDialog(qtwrapper.QtGui.QDialog):

    '"About" dialog widget'

    def __init__(self, parent=None):
        super(AboutDialog, self).__init__(parent)
        self._ui = AboutDialogUi()
        self._ui.setupUi(self)
