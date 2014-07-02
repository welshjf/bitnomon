# bitcoinconf.py
# Jacob Welsh, April 2014

"""Finding and loading a Bitcoin Core config file"""

import platform, os

if platform.system() == 'Windows':
	datadir = os.path.join(os.environ['APPDATA'], 'Bitcoin')
else:
	_home = os.environ['HOME']
	if platform.system() == 'Darwin':
		datadir = os.path.join(_home, 'Library/Application Support/Bitcoin')
	else:
		datadir = os.path.join(_home, '.bitcoin')

conf='bitcoin.conf'

COIN=100000000

def read():
	"""Read a bitcoin.conf file, returning its key/value pairs as a dict.

	To change datadir/conf, set datadir or conf_file in the module namespace.
	"""
	f = open(os.path.join(datadir, conf), 'r')
	lines = f.readlines()
	f.close()
	c = {}
	for line in lines:
		if len(line) == 0:
			continue
		line = line.split('#', 1)[0]
		if len(line) == 0:
			continue
		parts = line.split('=', 1)
		if len(parts) != 2:
			continue
		c[parts[0].strip()] = parts[1].strip()
	return c
