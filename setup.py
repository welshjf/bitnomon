from setuptools import setup, find_packages
from setuptools.command.sdist import sdist as _sdist
from distutils import log
import subprocess
from bitnomon import __version__, BUNDLE

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

with open('README.rst') as f:
    readme_text = f.read()

packages = ['bitnomon']
package_dir = {}
requires=[
    'appdirs (>=1.3.0)',
    'numpy',
    'PyQt4 (>=4.7.0)',
    # The binding distributed with rrdtool itself is version 1.x; we want
    # the newer one from PyPI which supports Python 3.
    'rrdtool (>=0.1.0, <1.0.0)',
]
if BUNDLE:
    pg_pkgs = find_packages('deps/pyqtgraph', exclude=['examples*'])
    packages.extend('bitnomon.deps.' + pkg for pkg in pg_pkgs)
    package_dir['bitnomon.deps.pyqtgraph'] = 'deps/pyqtgraph/pyqtgraph'
else:
    # 0.9.8 is too old; 0.9.9/10 shipped with a drawing bug that affects us
    # (https://github.com/pyqtgraph/pyqtgraph/pull/136)
    requires.append('pyqtgraph (>0.9.10)')

setup(
    name='bitnomon',
    version=__version__,
    description='Monitoring/visualization GUI for a Bitcoin node',
    long_description=readme_text,
    author='Jacob Welsh',
    author_email='jacob@welshcomputing.com',
    url='https://www.welshcomputing.com/code/bitnomon.html',
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: System :: Monitoring',
    ],
    packages=packages,
    package_dir=package_dir,
    requires=requires,
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
