========
Bitnomon
========

Monitoring/visualization GUI for a Bitcoin node

Home page: https://www.welshcomputing.com/code/bitnomon.html

Description
===========

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
platforms as Bitcoin Core itself.

License
=======

Copyright (c) 2015 Jacob Welsh <jacob@welshcomputing.com>

This program is free software under the MIT/X11 license; see the file LICENSE
for details.

The Bitnomon developers place no restrictions on its code beyond the above,
however some parts may be considered derivatives of works under other free
software licenses, as follows:

  * bitnomon/qbitcoinrpc.py: GNU Lesser General Public License, version 2.1 or
    later; see the file and lgpl-2.1.txt for details

  * The entire program when combined with PyQt: GNU General Public License

Supported Platforms
===================

The primary target platform is X11 on Linux. In principle, all the code is
portable to Windows and Mac OS X, but installation may be more difficult there.
Bundled releases including all dependencies may be available at some point.
Other Unix-like systems should work too but are not tested.

Installing
==========

Non-Python dependencies: Qt 4, rrdtool

PyPI dependencies: PyQt4, numpy, rrdtool, appdirs

Fedora/Red Hat:

  * Base: `sudo yum install PyQt4 numpy rrdtool python-setuptools`

Ubuntu 14.04:

  * Base: `sudo apt-get install python-qt4 python-numpy rrdtool
    python-setuptools`

  * Full: `sudo apt-get install python-appdirs python-rrdtool`

This assumes you have downloaded a source release (not the Git repository).

To install system-wide:

    sudo python setup.py install

To install for the current user (requires $HOME/.local/bin in $PATH):

    python setup.py install --user

Hacking
=======

Update submodules and setup.py install the bundled pyqtgraph

Fedora/Red Hat:

    sudo yum install PyQt4-devel [or pyside-tools] python-mock

Ubuntu 14.04:

    sudo apt-get install pyqt4-dev-tools [or pyside-tools] python-mock

`make`, then run using one of:

`python setup.py develop --user`, put ~/.local/bin in `$PATH`, and run `bitnomon`

`python -m bitnomon`

Not `python bitnomon` -- that doesn't add project dir to sys.path

Testing
-------

`python setup.py test` or just `python run_unit_tests.py`

`pylint bitnomon`

Style
-----

Release Process
---------------

Bundling Note
-------------

PyQt Note
---------

Bitnomon can use either PySide or PyQt as its Qt binding. PyQt is recommended,
because there is a memory leak at least as of PySide 1.2.1.

PySide, like Qt itself, is available under the LGPL. PyQt is only available
under the GPL or a commercial license from Riverbank Computing Limited. If you
use or distribute Bitnomon with PyQt, you may be subject to the additional
restrictions of the GPL.
