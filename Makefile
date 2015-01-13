ifdef PYSIDE
 UIC=pyside-uic
 RCC=pyside-rcc
 QTWRAPPER_SRC=qtwrapper-pyside.in
else
 UIC=pyuic4
 RCC=pyrcc4 -py3
 QTWRAPPER_SRC=qtwrapper-pyqt.in
endif

generated=bitnomon/ui_main.py \
	  bitnomon/ui_about.py \
	  bitnomon/bitnomon_rc.py \
	  bitnomon/qtwrapper.py \

all: $(generated)

bitnomon/ui_%.py: bitnomon/res/%.ui
	$(UIC) $< -o $@

bitnomon/%_rc.py: bitnomon/res/%.qrc
	$(RCC) $< -o $@

bitnomon/qtwrapper.py: bitnomon/$(QTWRAPPER_SRC)
	cp $< $@

testing.html: testing.html.m4
	m4 -P $< > $@

clean:
	rm -f bitnomon/*.pyc bitnomon/__pycache__ $(generated)
