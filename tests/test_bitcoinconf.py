import unittest
import sys
import os
import contextlib

if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock

if sys.version_info < (3,):
    from StringIO import StringIO
else:
    from io import StringIO

from bitnomon import bitcoinconf

class ModuleTest(unittest.TestCase):

    "Tests for top-level module components (non-class functions)"

    @mock.patch('bitnomon.bitcoinconf.platform.system')
    def test_default_datadir(self, mock_system):

        def test_for_system(system, environ):
            mock_system.return_value = system
            with mock.patch.dict(bitcoinconf.os.environ, environ):
                # No exceptions should be raised
                bitcoinconf.default_datadir()
            with mock.patch.dict(bitcoinconf.os.environ, clear=True):
                # ConfigError should be raised when HOME/APPDATA is missing
                self.assertRaises(bitcoinconf.ConfigError,
                        bitcoinconf.default_datadir)

        test_for_system('Windows', {'APPDATA': 'test_appdata'})
        test_for_system('Darwin', {'HOME': 'test_home'})
        test_for_system('Linux', {'HOME': 'test_home'})

class ConfTest(unittest.TestCase):

    @mock.patch('bitnomon.bitcoinconf.open', create=True)
    def test_load(self, mock_open):
        mock_open.return_value = contextlib.closing(StringIO('\n'.join((
            '# comment',
            '\t # whitespace comment',
            '',
            'a=1 # trailing comment',
            'b = 2',
            '  c  =  3  ',
            'd = ',
            '=',
            ''))))
        conf = bitcoinconf.Conf()
        conf.load('test_datadir')
        mock_open.assert_called_once_with(
            os.path.join('test_datadir', 'bitcoin.conf'))
        self.assertEqual(conf, {
            'a': '1',
            'b': '2',
            'c': '3',
            'd': '',
            '': '',
            })
