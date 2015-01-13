import unittest
from bitnomon import age

class StaticTest(unittest.TestCase):

    "Tests for module functions / static methods"

    def test_ageOfTime(self):
        now = 60
        self.assertEqual(age.ageOfTime(now, 60), 0)
        self.assertEqual(age.ageOfTime(now, 30), 0.5)
        self.assertEqual(age.ageOfTime(now, 0), 1)

    def test_genericTickSpacing(self):
        self.assertEqual(age.genericTickSpacing(.05),     (.1, .02))
        self.assertEqual(age.genericTickSpacing(1),       (1,  .2))
        self.assertEqual(age.genericTickSpacing(2),       (2,  1))
        self.assertEqual(age.genericTickSpacing(2.0001),  (10, 2))
        self.assertEqual(age.genericTickSpacing(10.0001), (20, 10))

    # The best test for AgeAxisItem.tickSpacing is to run the age_tester.py
    # utility and zoom it from small to large scales, making sure the ticks
    # don't get too big or small and they snap to hours/days at the medium
    # sizes, and testing with both small and large window sizes.

    def testTickStrings(self):
        minutes = 60
        self.assertEqual(
            age.AgeAxisItem.tickStrings([0.1, 0.2, 0.1*3], 1, 0.01),
            ['0.10', '0.20', '0.30'])
        self.assertEqual(
            age.AgeAxisItem.tickStrings(
                [0, 60, 1440, 1440+61, 1440*500], 1, 1),
            ['0', '1:00', '1:00:00', '1:01:01', '500:00:00'])
