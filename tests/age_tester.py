from bitnomon import age
import pyqtgraph as pg

app = pg.QtGui.QApplication([])

p = pg.PlotItem(axisItems={'bottom': age.AgeAxisItem('bottom')})
p.showGrid(x=True)

v = pg.GraphicsView()
v.setCentralWidget(p)
v.show()
app.exec_()
