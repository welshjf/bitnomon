# formatting.py
# Jacob Welsh, April 2014

"""Text/number formatting"""

class ByteCountFormatter:

    """Human-readable formatting of byte counts. Stores a formatting mode
    (bit vs. byte and unit system) for consistent display in different
    parts of a program.

    By default, the formatter uses SI and bytes, so 1000 => "1 KB". All
    combinations of (byte, bit) x (SI, binary) are supported, though you
    probably shouldn't use bits with the binary prefixes.
    """

    SI_prefixes = ('k','M','G','T','P','E','Z','Y')
    binary_prefixes = ('Ki','Mi','Gi','Ti','Pi','Ei','Zi','Yi')

    def __init__(self):
        self._use_bits = False
        self._use_si = True

    def setUnitBytes(self):
        self._use_bits = False
    def setUnitBits(self):
        self._use_bits = True
    def setPrefixSI(self):
        self._use_si = True
    def setPrefixBinary(self):
        self._use_si = False

    def format(self, count):
        """Formats a byte count using the configured settings."""
        if self._use_bits:
            count *= 8
            unit = 'b'
        else:
            unit = 'B'

        if self._use_si:
            factor = 1000.
            prefixes = self.SI_prefixes
        else:
            factor = 1024.
            prefixes = self.binary_prefixes

        if abs(count) < factor:
            return u'%d %c' % (count, unit)
        size = float(count)
        prefixIndex = 0
        while abs(size) >= factor and prefixIndex < len(prefixes):
            size /= factor
            prefixIndex += 1
        return u'%.2f %s%c' % (size, prefixes[prefixIndex-1], unit)
