import unittest
import sys

if sys.version_info < (3,3):
    import mock
else:
    from unittest import mock

from bitnomon import rrdmodel

class BaseRRDModelTest(unittest.TestCase):

    """No tests here, just a fixture for mocking out rrdtool etc."""

    def setUp(self):
        with mock.patch('bitnomon.rrdmodel.RRDModel.create') as mock_create:
            self.mock_create = mock_create
            with mock.patch('bitnomon.rrdmodel.os.path.exists') as mock_exists:
                mock_exists.return_value = False
                self.model = rrdmodel.RRDModel('test_data_dir')
        self.patcher = mock.patch('bitnomon.rrdmodel.rrdtool')
        self.mock_rrdtool = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

class RRDModelTest(BaseRRDModelTest):

    """Fairly stupid tests for most RRDModel methods"""

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
            (0, 30, 10), # time range / resolution
            ('a', 'b'),  # data source names
            [(None, 0), (1, 2), (3, 4)] # values
        ]
        self.assertEqual(
            list(self.model.fetch(1, 31, 10)),
            [
                (0, (None, 0)),
                (10, (1, 2)),
                (20, (3, 4)),
            ]
        )

year = 60*60*24*365

class FetchAllTest(BaseRRDModelTest):

    """Dedicated class for testing RRDModel.fetch_all because it's complicated.
    What we're most interested in checking are the times at the junction of two
    resolution levels, that being the tricky part to get right."""

    def setUp(self):
        super(FetchAllTest, self).setUp()
        def mock_fetch(start, end, res):
            # Provide dummy values for each consolidation level, but align the
            # times to the resolution as RRDtool does.
            times = range(start - (start % res), end - (end % res) + 1, res)
            values = [(time, time) for time in times]
            return zip(times, values)
        self.model.fetch = mock_fetch

    @staticmethod
    def assertIncreasing(times):
        for i in range(len(times)-1):
            cur = times[i]
            nxt = times[i+1]
            if nxt <= cur:
                raise AssertionError(
                    'Non-increasing elements %d: %d and %d: %d out of %d' %
                    (i, cur, i+1, nxt, len(times)))

    # When the latest sample's time is a multiple of the next coarser
    # resolution
    def test_at_multiple(self):
        self.mock_rrdtool.last.return_value = year
        times = tuple(t for t,_ in self.model.fetch_all())
        self.assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year)
        self.assertEqual(times[-361], year - 60*360)
        self.assertEqual(times[-362], year - 60*360 - 600)

    # And when it's just above one
    def test_above_multiple(self):
        self.mock_rrdtool.last.return_value = year + 1
        times = tuple(t for t,_ in self.model.fetch_all())
        self.assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year)
        self.assertEqual(times[-361], year - 60*360)
        self.assertEqual(times[-362], year - 60*360 - 600)

    # And when it's just below one
    def test_below_multiple(self):
        self.mock_rrdtool.last.return_value = year + 599
        times = tuple(t for t,_ in self.model.fetch_all())
        self.assertIncreasing(times)
        self.assertEqual(times[0], 0)
        self.assertEqual(times[-1], year + 540)
        self.assertEqual(times[-361], year - 60*360 + 540)
        self.assertEqual(times[-362], year - 60*360)

class RRATest(unittest.TestCase):

    """Tests for the in-memory RRA data structure"""

    def setUp(self):
        self.a = rrdmodel.RRA((1, 2, 3))
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
        self.assertEqual(tuple(self.a), (2, 3, 4.0))

    def test_len(self):
        self.assertEqual(len(self.a), 3)

    def test_str(self):
        self.assertEqual(str(self.a), '[2, 3, 4.0]')

    def test_repr(self):
        self.assertEqual(repr(self.a), 'RRA([2, 3, 4.0])')

    def test_clear(self):
        self.a.clear()
        self.assertEqual(tuple(self.a), (None, None, None))

class RRADiffTest(unittest.TestCase):

    """Tests for the RRA differencing iterable"""

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
