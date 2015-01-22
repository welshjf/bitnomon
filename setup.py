# -*- coding: utf-8 -*-
#
# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

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

packages = ['bitnomon']
package_dir = {}
install_requires=[
    'appdirs >=1.3.0',
    'numpy',
    #'PyQt4 >=4.7.0', # Requires manual installation
    'rrdtool', # Can be substituted with 'py-rrdtool'. That's an older binding,
    # distributed with rrdtool itself, and thus more likely to be packaged in
    # Linux distros already, but lacking Python 3 support.
]
if BUNDLE:
    pg_pkgs = find_packages('deps/pyqtgraph', exclude=['examples*'])
    packages.extend('bitnomon.deps.' + pkg for pkg in pg_pkgs)
    package_dir['bitnomon.deps.pyqtgraph'] = 'deps/pyqtgraph/pyqtgraph'
else:
    # 0.9.8 is too old; 0.9.9/10 shipped with a drawing bug that affects us
    # (https://github.com/pyqtgraph/pyqtgraph/pull/136)
    install_requires.append('pyqtgraph (>0.9.10)')

setup(
    name='bitnomon',
    version=__version__,
    description='Monitoring/visualization GUI for a Bitcoin node',
    long_description="""\
Bitnomon aims to increase the interest and educational value in running a full
validating node on the Bitcoin peer-to-peer network by presenting the details
of its activities in a clear and user-friendly manner.

Currently, besides displaying the basic information like network difficulty,
block count, and peer count, it plots the transactions in the memory pool,
block arrival times, and inbound/outbound network traffic. Traffic data is
stored for up to a year, at decreasing resolutions, using a round-robin
database in the standard RRDtool format.

It supports Bitcoin Core, that is, the “Satoshi” clients bitcoind and
bitcoin-qt, version 0.9+, or alternatives with a compatible JSON-RPC interface.
It is a Qt application written in Python, and thus should support all the same
platforms as Bitcoin Core itself.""",
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
    install_requires=install_requires,
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
