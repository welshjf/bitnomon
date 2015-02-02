========
Bitnomon
========

Monitoring/visualization GUI for a Bitcoin node

.. image:: https://www.welshcomputing.com/code/img/bitnomon-icon.png
   :alt: Icon

Home page: https://www.welshcomputing.com/code/bitnomon.html

About
=====

Bitnomon aims to increase the interest and educational value in running a full
node on the Bitcoin peer-to-peer network by presenting a clear view of its
activities.

It is a Python/Qt application and works with Bitcoin Core version 0.9+ (or
alternatives with a compatible JSON-RPC interface). It must be run on the same
system as the node, unless you are comfortable securing the API for remote
access yourself.

Features
--------

* Basic information like difficulty, block and peer count

* Transactions in the memory pool, plotted by age versus fee, with “high
  priority” transactions highlighted

* Block arrival times (as seen by Bitnomon, up to the last 24 blocks)

* Inbound and outbound network traffic: total, recent averages, and plotted
  over time; data is stored for up to a year, at decreasing resolutions, using
  a round-robin database in the standard RRDtool format

* Interactive panning/zooming of plots

* Full screen mode

Supported Platforms
-------------------

The primary target platform is X11 on Linux/UNIX. In principle, all the code is
portable to Windows and Mac OS X, but these have not yet been a priority. Known
working:

* Fedora 20
* CentOS 7
* Debian 7 (Wheezy)
* Ubuntu 12.04 LTS

Installing
==========

First, install the dependencies that can't be installed from PyPI (or at least
are easier with the system package manager).

Fedora/Red Hat::

    sudo yum install PyQt4 numpy rrdtool-python python-pip

Debian/Ubuntu::

    sudo apt-get install python-qt4 python-numpy python-rrdtool python-pip

Then ``pip`` can download the rest (but see “More Secure Install,” below)::

    pip install [--user] bitnomon

Or if you already have the source distribution::

    pip install [--user] bitnomon-<version>.tar.bz2

The ``--user`` option causes Bitnomon to be installed in your home directory
(under ~/.local). If you prefer a system-wide install, omit it and use
``sudo``. Either way, uninstalling is simple::

    pip uninstall bitnomon

A launcher icon will be installed to the system menu, or you can run
``bitnomon`` from the command line. For the latter to work with a user install,
you may need to add ~/.local/bin to your PATH, for example by adding at the
beginning of ~/.bashrc::

    export PATH="$HOME/.local/bin:$PATH"

More Secure Install
-------------------

The ``pip install`` command (as well as ``easy_install`` and ``setup.py
install``) is subject to automatically downloading and executing code from PyPI
(the Python Package Index). Newer versions of pip at least enforce HTTPS, but
this still leaves openings for attack, such as the PyPI web infrastructure,
third party uploaders, and certificate authorities.

To mitigate this risk, I am providing a PGP-signed bundle of Bitnomon and its
PyPI dependencies, available from the home page. Once you have downloaded and
verified the signature, run::

    tar xf bitnomon-<version>-bundle.tar
    pip install [--user] --no-index -f bitnomon-<version>-bundle bitnomon

(If your ``pip`` is too old to understand a local directory for -f, such as on
Ubuntu 12.04, then you must explicitly specify the files to install.)

License
=======

Copyright 2015 Jacob Welsh

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this software except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Parts of Bitnomon may be considered derivatives of works under other free
software licenses, specifically:

* bitnomon/qbitcoinrpc.py: GNU Lesser General Public License, version 2.1 or
  later; see the file itself and lgpl-2.1.txt for details

PyQt Note
---------

Bitnomon can use either PySide or PyQt. PyQt is the default and recommended
binding (in part because there is a slow but steady memory leak at least as of
PySide 1.2.1). However, it is only available under the GPL or a commercial
license from Riverbank Computing Limited. If you use or redistribute Bitnomon
with PyQt, you may be subject to the additional restrictions of the GPL. PySide
is available under the LGPL, like Qt itself.
