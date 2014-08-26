import unittest
import formatting

class ByteCountFormatterTest(unittest.TestCase):

    def test_bytes_SI(self):
        f = formatting.ByteCountFormatter()
        # Bytes/SI is the default mode
        self.assertEqual(f.format(1), "1 B")
        self.assertEqual(f.format(1000), "1.00 kB")
        self.assertEqual(f.format(1024), "1.02 kB")
        self.assertEqual(f.format(1000*1000), "1.00 MB")
        self.assertEqual(f.format(1024*1024), "1.05 MB")
        self.assertEqual(f.format(1e27), "1000.00 YB")
        self.assertEqual(f.format(0), "0 B")
        self.assertEqual(f.format(-1), "-1 B")
        self.assertEqual(f.format(-1024), "-1.02 kB")

    def test_bits_SI(self):
        f = formatting.ByteCountFormatter()
        f.setUnitBits();
        self.assertEqual(f.format(1), "8 b")
        self.assertEqual(f.format(1000), "8.00 kb")
        self.assertEqual(f.format(1024), "8.19 kb")
        self.assertEqual(f.format(1000*1000), "8.00 Mb")
        self.assertEqual(f.format(1024*1024), "8.39 Mb")
        self.assertEqual(f.format(1e27), "8000.00 Yb")
        self.assertEqual(f.format(0), "0 b")
        self.assertEqual(f.format(-1), "-8 b")
        self.assertEqual(f.format(-1024), "-8.19 kb")

    def test_bytes_binary(self):
        f = formatting.ByteCountFormatter()
        f.setPrefixBinary();
        self.assertEqual(f.format(1), "1 B")
        self.assertEqual(f.format(1000), "1000 B")
        self.assertEqual(f.format(1024), "1.00 KiB")
        self.assertEqual(f.format(1000*1000), "976.56 KiB")
        self.assertEqual(f.format(1024*1024), "1.00 MiB")
        self.assertEqual(f.format(1e28), "8271.81 YiB")
        self.assertEqual(f.format(0), "0 B")
        self.assertEqual(f.format(-1), "-1 B")
        self.assertEqual(f.format(-1024), "-1.00 KiB")
