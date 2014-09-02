import unittest
import sys

if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock

import rrdmodel

class RRDModelTest(unittest.TestCase):

    @mock.patch('rrdmodel.main.data_dir', new='test_data_dir')
    @mock.patch('rrdmodel.os.path.exists')
    @mock.patch('rrdmodel.RRDModel.create')
    def setUp(self, mock_create, mock_path_exists):
        mock_path_exists.return_value = False
        self.model = rrdmodel.RRDModel()
        self.mock_create = mock_create

    def test_init(self):
        self.mock_create.assert_called_once_with()

    @mock.patch('rrdmodel.rrdtool')
    def test_create(self, mock_rrdtool):
        self.model.create()
        self.assertEqual(mock_rrdtool.create.called, True)
