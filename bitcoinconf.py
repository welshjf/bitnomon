# bitcoinconf.py

"""Bitcoin Core global and user-configurable parameters"""

import platform
import os

COIN=100000000

class ConfigError(Exception):
    pass

def default_datadir():
    "Return the OS-dependent default data directory for Bitcoin Core."
    try:
        if platform.system() == 'Windows':
            return os.path.join(os.environ['APPDATA'], 'Bitcoin')
        else:
            home = os.environ['HOME']
            if platform.system() == 'Darwin':
                return os.path.join(home, 'Library/Application Support/Bitcoin')
            else:
                return os.path.join(home, '.bitcoin')
    except KeyError as e:
        raise ConfigError('Missing environment variable {}'.format(e))

class Conf(dict):

    "Dictionary representing a bitcoin.conf file."

    def load(self, datadir=None, filename='bitcoin.conf'):
        """Load keys/values from file.

        Arguments:
        datadir -- Bitcoin data directory. If None, use the OS-dependent
                   default.
        filename -- Name of config file within datadir.
        """
        if datadir is None:
            datadir = default_datadir()
        f = open(os.path.join(datadir, filename), 'r')
        lines = f.readlines()
        f.close()
        for line in lines:
            line = line.split('#', 1)[0]
            parts = line.split('=', 1)
            if len(parts) != 2:
                continue
            self[parts[0].strip()] = parts[1].strip()
