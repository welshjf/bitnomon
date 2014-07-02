ifndef PYQT
 UIC=pyside-uic
 RCC=pyside-rcc
else
 UIC=pyuic4
 RCC=pyrcc4
endif

generated=ui_main.py ui_about.py bitnomon_rc.py
all: $(generated)

ui_main.py: main.ui
	$(UIC) main.ui -o ui_main.py
ui_about.py: about.ui
	$(UIC) about.ui -o ui_about.py
bitnomon_rc.py: res/bitnomon.qrc
	$(RCC) res/bitnomon.qrc -o bitnomon_rc.py

clean:
	rm -f *.pyc $(generated)
