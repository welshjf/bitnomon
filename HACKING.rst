Developer Notes
===============

There are some extra requirements for building or running the code from the
repository. First, fetch the submodule for the bundled PyQtGraph::

    git submodule update --init

Install the PyQt or PySide dev tools. For Red Hat/Fedora::

    sudo yum install {PyQt4-devel|pyside-tools}

For Debian/Ubuntu::

    sudo apt-get install {pyqt4-dev-tools|pyside-tools}

This is sufficient for building an sdist. To run the code from the repository,
you'll need to install the dependencies in the README, plus the bundled
PyQtGraph::

    cd deps/pyqtgraph
    python setup.py install --user

Back at the top level, run ``make``, then either run the bitnomon package
directly using::

    python -m bitnomon

Or install in development mode using one of::

    pip install --user [--no-index] --editable .
    python setup.py develop --user

This will link the working tree into your site-packages, so you can just run
``bitnomon`` (assuming ~/.local/bin is in your PATH) without having to
re-install to pick up changes.

Testing
-------

To run the tests with Python 2 you will need the mock package (``python-mock``
on Debian/Ubuntu/Fedora/Red Hat). Then run one of::

    python setup.py test
    python run_unit_tests.py

For Python 3 (see below), just run with the corresponding interpreter. Unit
test coverage is mostly limited to the "pure" parts, as I'm not aware of a
useful way to test the GUI code. There is a manual testing checklist at
testing.html.

Also try to keep things free of ``pylint`` issues, within reason::

    pylint bitnomon

Style
-----

Use camelCase for consistency with Qt. Otherwise, PEP8.

Release Process
---------------

Notes for the maintainer:

* Update __version__ in bitnomon/__init__.py

* Finalize release notes

* Create, sign, and push a version tag

* make clean; python setup.py sdist; sign and upload to PyPI

* Add placeholder to release notes; bump __version__ to NEXT.dev0; push

* Build sdist bundle/installers/debs/rpms, signing where possible; upload

* Update web page; announce

Bundling
--------

Currently, all releases of Bitnomon contain a bundled copy of a git version of
PyQtGraph. This is because none of its releases are satisfactory. As a young
library, it has no beta testing process, and 0.9.10 shipped with a drawing bug
that noticeably affects Bitnomon. The fix has been submitted
(https://github.com/pyqtgraph/pyqtgraph/pull/136) but timetable is unknown. The
previous release 0.9.8 lacks API used by Bitnomon, and even if that were worked
around, lacks important performance optimizations for scatter plot drawing.

For Linux distributors willing to maintain a satisfactory PyQtGraph package,
bundling can be disabled in bitnomon/__init__.py.

install_freedesktop is also bundled, to prevent unexpected auto-download from
PyPI (see setup.cfg). This is only needed at install time (build time for
RPM/deb).

PySide
------

See the note in the README about PyQt vs. PySide. One or the other must be
pre-selected at sdist build time; PyQtGraph style autodetection is explicitly
avoided, to prevent user experience problems resulting from an inferior binding
being attributed to Bitnomon.

The differences are smoothed over in bitnomon/qtwrapper.py, which is generated
by the Makefile from qtwrapper-pyqt.in or qtwrapper-pyside.in. (For now it's
just done by copying one or the other, as I didn't want to add extra build
requirements like m4/Jinja/whatever).

To void the (figurative) warranty and use PySide instead of PyQt::

    make clean
    make PYSIDE=1

Python 3
--------

Python 2 and 3 are both supported. Be advised that at time of writing, there's
still a memory leak when using Python 3, even with PyQt. Also, the
python-rrdtool package provided by common Linux distributions (“py-rrdtool“ on
PyPI) does not support Python 3, so setup.py will pull in “rrdtool” instead.
Pip will compile the extension module for you, but you'll need a C compiler
plus the Python and rrdtool headers installed.
