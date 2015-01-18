"""Monitoring GUI for a Bitcoin Core node"""

__version__ = '0.1'

# Whether to bundle dependencies (pyqtgraph) inside the package
BUNDLE = True

if BUNDLE:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'deps'))
