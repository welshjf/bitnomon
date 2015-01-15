from setuptools import setup
from setuptools.command.sdist import sdist as _sdist
from distutils import log
import subprocess
from bitnomon import __version__

class sdist(_sdist):

    """Extend the "sdist" command to ensure the generated .py files are
    included in the source distribution. This avoids having pyuic4/pyrcc4/make
    as user-facing build requirements.

    To configure for PySide instead of PyQt, first run "make PYSIDE=1"; then
    the "make" here will have nothing to do."""

    def run(self):
        log.info("running 'make'")
        try:
            subprocess.check_call('make')
        except subprocess.CalledProcessError as e:
            raise SystemExit(e)
        _sdist.run(self)

setup(
    name='bitnomon',
    version=__version__,
    description='Bitcoin Node Monitor',
    long_description='[placeholder]',
    author='Jacob Welsh',
    author_email='jacob@welshcomputing.com',
    license='MIT',
    classifiers=[],
    packages=['bitnomon'],
    requires=[
        # 0.9.8 is too old; 0.9.9/10 shipped with a drawing bug that affects us
        # (https://github.com/pyqtgraph/pyqtgraph/pull/136)
        'pyqtgraph (>0.9.10)',
        # The binding distributed with rrdtool itself is version 1.x; we want
        # the newer one from PyPI which supports Python 3.
        'rrdtool (>=0.1.0, <1.0.0)',
    ],
    package_data={
        'bitnomon': [],
    },
    entry_points={
        'gui_scripts': [
            'bitnomon=bitnomon.main:main',
        ],
    },
    test_suite='tests',
    test_loader='run_unit_tests:Loader',
    cmdclass={'sdist': sdist},
)
