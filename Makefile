ifdef PYSIDE
 UIC=pyside-uic
 RCC=pyside-rcc
 QTWRAPPER_SRC=qtwrapper-pyside.in
else
 UIC=pyuic4 --from-imports
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

%.html: %.rst
	rst2html $< $@

clean:
	rm -vf $(generated)

cleaner: clean
	find . -name '*.pyc' -exec rm -vf {} +
	find . -type d -name __pycache__ -exec rmdir -v {} +
	rm -rvf bitnomon.egg-info build

bitnomon.icns:
	png2icns bitnomon.icns bitnomon/res/{16x16,32x32,48x48,128x128,256x256}/bitnomon.png
