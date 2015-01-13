ifdef PYSIDE
 UIC=pyside-uic
 RCC=pyside-rcc
 QTWRAPPER_SRC=qtwrapper-pyside.py
else
 UIC=pyuic4
 RCC=pyrcc4 -py3
 QTWRAPPER_SRC=qtwrapper-pyqt.py
endif

generated=ui_main.py \
	  ui_about.py \
	  bitnomon_rc.py \
	  qtwrapper.py \

all: $(generated)

ui_%.py: %.ui
	$(UIC) $< -o $@

%_rc.py: res/%.qrc
	$(RCC) $< -o $@

qtwrapper.py: $(QTWRAPPER_SRC)
	cp $< $@

testing.html: testing.html.m4
	m4 -P $< > $@

clean:
	rm -f *.pyc $(generated)
