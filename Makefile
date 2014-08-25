ifdef PYQT
 UIC=pyuic4
 RCC=pyrcc4 -py3
 M4_OPTS=-D PYQT
else
 UIC=pyside-uic
 RCC=pyside-rcc
endif

generated=ui_main.py ui_about.py bitnomon_rc.py qtwrapper.py
all: $(generated)

ui_main.py: main.ui
	$(UIC) main.ui -o ui_main.py
ui_about.py: about.ui
	$(UIC) about.ui -o ui_about.py
bitnomon_rc.py: res/bitnomon.qrc
	$(RCC) res/bitnomon.qrc -o bitnomon_rc.py
qtwrapper.py: qtwrapper.m4
	m4 $(M4_OPTS) qtwrapper.m4 > qtwrapper.py

clean:
	rm -f *.pyc $(generated)
