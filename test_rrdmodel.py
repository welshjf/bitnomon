import unittest
import sys

if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock

import rrdmodel

class RRDModelTest(unittest.TestCase):

    def setUp(self):
        with mock.patch('rrdmodel.RRDModel.create') as mock_create:
            self.mock_create = mock_create
            with mock.patch('rrdmodel.os.path.exists') as mock_path_exists:
                mock_path_exists.return_value = False
                self.model = rrdmodel.RRDModel('test_data_dir')
        self.patcher = mock.patch('rrdmodel.rrdtool')
        self.mock_rrdtool = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_init(self):
        self.mock_create.assert_called_once_with()

    def test_create(self):
        self.model.create()
        self.assertEqual(self.mock_rrdtool.create.called, True)

    def test_update(self):
        self.model.update(0, (1, 2))
        self.assertEqual(self.mock_rrdtool.update.called, True)

    def test_fetch(self):
        self.mock_rrdtool.fetch.return_value = [
            (0, 30, 10),
            ('a', 'b'),
            [(None, 0), (1, 2), (3, 4)]
        ]
        self.assertEqual(
            list(self.model.fetch(1, 31, 10)),
            [
                (0, (None, 0)),
                (10, (1, 2)),
                (20, (3, 4)),
            ]
        )

    def test_fetch_all(self):
        def mock_fetch(start, end, res):
            times = range(start - (start % res), end - (end % res) + 1, res)
            values = [(time, time) for time in times]
            return zip(times, values)
        self.model.fetch = mock_fetch

        def assertIncreasing(times):
            for i in range(len(times)-1):
                cur = times[i]
                nxt = times[i+1]
                if nxt <= cur:
                    raise AssertionError(
                        'Non-increasing elements %d: %d and %d: %d out of %d' %
                        (i, cur, i+1, nxt, len(times)))

        # Check the times at the junction of two resolution levels, where the
        # latest sample is a multiple of the coarser resolution
        year = 60*60*24*365
        self.mock_rrdtool.last.return_value = year
        times = tuple(zip(*self.model.fetch_all()))[0]
        assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year)
        self.assertEqual(times[-61], year - 3600)
        self.assertEqual(times[-62], year - 3600 - 600)

        # And where it's just above one
        self.mock_rrdtool.last.return_value = year + 1
        times = tuple(zip(*self.model.fetch_all()))[0]
        assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year)
        self.assertEqual(times[-61], year - 3600)
        self.assertEqual(times[-62], year - 3600 - 600)

        # And where it's just below one
        self.mock_rrdtool.last.return_value = year + 599
        times = tuple(zip(*self.model.fetch_all()))[0]
        assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year + 540)
        self.assertEqual(times[-61], year - 3600 + 540)
        self.assertEqual(times[-62], year - 3600)

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
