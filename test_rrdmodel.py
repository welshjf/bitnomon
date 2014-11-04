import unittest
import sys

if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock

import rrdmodel

class RRDModelTest(unittest.TestCase):

    @mock.patch('rrdmodel.os.path.exists')
    @mock.patch('rrdmodel.RRDModel.create')
    def setUp(self, mock_create, mock_path_exists):
        mock_path_exists.return_value = False
        self.model = rrdmodel.RRDModel('test_data_dir')
        self.mock_create = mock_create

    def test_init(self):
        self.mock_create.assert_called_once_with()

    @mock.patch('rrdmodel.rrdtool')
    def test_create(self, mock_rrdtool):
        self.model.create()
        self.assertEqual(mock_rrdtool.create.called, True)

    @mock.patch('rrdmodel.rrdtool')
    def test_update(self, mock_rrdtool):
        self.model.update(0, (1, 2))
        self.assertEqual(mock_rrdtool.update.called, True)

    @mock.patch('rrdmodel.rrdtool')
    def test_fetch(self, mock_rrdtool):
        mock_rrdtool.fetch.return_value = [
            (0,30,10),
            ('a','b'),
            [(None,None), (1,2), (3,4)]
        ]
        self.assertEqual(
            self.model.fetch(0,30,10),
            [(20, (1,2)), (30, (3,4))]
        )

class RRATest(unittest.TestCase):

    def setUp(self):
        self.a = rrdmodel.RRA((1,2,3))
        self.a.update(4.0)

    def test_init_degenerate(self):
        with self.assertRaises(ValueError):
            rrdmodel.RRA(1)

    def test_getitem(self):
        self.assertEqual(self.a[0], 2)
        self.assertEqual(self.a[2], 4.0)
        self.assertEqual(self.a[-1], 4.0)
        self.assertEqual(self.a[-3], 2)
        with self.assertRaises(IndexError):
            self.a[3]
        with self.assertRaises(IndexError):
            self.a[-4]

    def test_iter(self):
        self.assertEqual(tuple(self.a), (2,3,4.0))

    def test_len(self):
        self.assertEqual(len(self.a), 3)

    def test_str(self):
        self.assertEqual(str(self.a), '[2, 3, 4.0]')

    def test_repr(self):
        self.assertEqual(repr(self.a), 'RRA([2, 3, 4.0])')

class RRADiffTest(unittest.TestCase):

    def setUp(self):
        self.a = rrdmodel.RRA(5)
        self.a.update(10)
        self.a.update(11)
        self.a.update(None)
        self.d = self.a.differences()

    def test_difference(self):
        self.assertEqual(self.a.difference(1, 0), None)
        self.assertEqual(self.a.difference(2, 1), None)
        self.assertEqual(self.a.difference(3, 2), 1)
        self.assertEqual(self.a.difference(4, 3), None)

    def test_getitem(self):
        self.assertEqual(self.d[0], None)
        self.assertEqual(self.d[1], None)
        self.assertEqual(self.d[2], 1)
        self.assertEqual(self.d[3], None)

        self.assertEqual(self.d[-1], None)
        self.assertEqual(self.d[-2], 1)
        self.assertEqual(self.d[-3], None)
        self.assertEqual(self.d[-4], None)
        with self.assertRaises(IndexError):
            self.d[4]
        with self.assertRaises(IndexError):
            self.d[-5]

    def test_iter(self):
        self.assertEqual(tuple(self.d), (None, None, 1, None))

    def test_len(self):
        self.assertEqual(len(self.d), 4)

    def test_undef_val(self):
        self.assertEqual(self.a.differences(-1)[0], -1)
