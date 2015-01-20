# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""Bitcoin Core global and user-configurable parameters"""

import platform
import os
import base64

COIN = 100000000

class ConfigError(Exception):
    'Error loading Bitcoin config file'
    pass

class FileNotFoundError(IOError):
    'File not found'
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
        try:
            with open(os.path.join(datadir, filename)) as f:
                for line in f:
                    line = line.split('#', 1)[0]
                    parts = line.split('=', 1)
                    if len(parts) != 2:
                        continue
                    self[parts[0].strip()] = parts[1].strip()
        except IOError as e:
            if e.errno == os.errno.ENOENT:
                raise FileNotFoundError(*e.args)
            else:
                raise

    def generate(self, datadir=None, filename='bitcoin.conf'):
        "Write a suitable config file and load it"
        if datadir is None:
            datadir = default_datadir()
        if not os.path.exists(datadir):
            os.makedirs(datadir)
        password = base64.b64encode(os.urandom(16)).decode('ascii').rstrip('=')
        with open(os.path.join(datadir, filename), 'w') as f:
            if os.name == 'posix':
                os.fchmod(f.fileno(), 0o600)
            # TODO: Windows? Or, is this even necessary? Maybe Bitcoin ensures
            # non-other-readable permissions on the datadir.
            f.write((u"""\
server=1
rpcuser=local
rpcpassword=%s
"""
            ) % password)
        self.load(datadir, filename)
