import unittest
import sys
if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock
import bitcoinconf

class TestGlobals(unittest.TestCase):

    @mock.patch('bitcoinconf.platform.system')
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
