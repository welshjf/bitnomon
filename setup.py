# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

from setuptools import setup, find_packages
from setuptools.command.sdist import sdist as _sdist
from distutils import log
import subprocess
import platform
import sys
import codecs
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

if sys.version_info[0] < 3:
    RRDTOOL = 'py-rrdtool'
    # This is the older binding distributed with rrdtool itself; it lacks
    # Python 3 support but is more widely available in Linux distributions.
else:
    RRDTOOL = 'rrdtool'

with codecs.open('README.rst', encoding='utf-8') as f:
    README = f.read()
with codecs.open('CHANGES.rst', encoding='utf-8') as f:
    CHANGES = f.read()

options = dict(
    name='bitnomon',
    version=__version__,
    description='Monitoring/visualization GUI for a Bitcoin node',
    long_description=README + '\n\n' + CHANGES,
    author='Jacob Welsh',
    author_email='jacob@welshcomputing.com',
    url='https://www.welshcomputing.com/code/bitnomon.html',
    license='Apache License 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: MacOS X',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
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
    keywords='bitcoin blockchain monitoring visualization pyqtgraph rrdtool',
    packages=['bitnomon'],
    install_requires=[
        'appdirs >=1.3.0',
        'numpy',
        #'PyQt4 >=4.7.0', # Installation doesn't provide metadata
        RRDTOOL,
    ],
    entry_points={
        'gui_scripts': [
            'bitnomon=bitnomon.main:main',
        ],
    },
    test_suite='tests',
    test_loader='run_unit_tests:Loader',
    cmdclass={'sdist': sdist},
)

# Bundle PyQtGraph if needed
if BUNDLE:
    pg_pkgs = find_packages('deps/pyqtgraph', exclude=['examples*'])
    options['packages'].extend('bitnomon.deps.' + pkg for pkg in pg_pkgs)
    options['package_dir'] = {
        'bitnomon.deps.pyqtgraph': 'deps/pyqtgraph/pyqtgraph',
    }
else:
    # 0.9.8 is too old; 0.9.9/10 shipped with a drawing bug that affects us
    # (https://github.com/pyqtgraph/pyqtgraph/pull/136)
    options['install_requires'].append('pyqtgraph >0.9.10')

# Desktop integration
system = platform.system()
if system == 'Darwin':
    options['setup_requires'] = ['py2app']
    options['options'] = {'py2app': dict(
        iconfile='bitnomon.icns',
        plist={
            'CFBundleIdentifier': 'com.welshcomputing.bitnomon',
        },
    )}
elif system == 'Windows':
    pass
else:
    options['setup_requires'] = ['install_freedesktop']
    options['desktop_entries'] = {
        'bitnomon': {
            'Name': 'Bitnomon',
            'GenericName': 'Bitcoin Node Monitor',
            'Categories': 'System;Monitor;DataVisualization;',
        },
    }
    icondir = lambda size, icons: ('share/icons/hicolor/%s/apps' % size,
            ['bitnomon/res/%s/%s' % (size, icon) for icon in icons])
    options['data_files'] = [
        icondir('16x16', ['bitnomon.png']),
        icondir('32x32', ['bitnomon.png']),
        icondir('48x48', ['bitnomon.png']),
        icondir('128x128', ['bitnomon.png']),
        icondir('256x256', ['bitnomon.png']),
        icondir('scalable', ['bitnomon.svg']),
    ]

setup(**options)
