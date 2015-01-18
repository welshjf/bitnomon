# Copyright 2015 Jacob Welsh
#
# This file is part of Bitnomon; see the README for license information.

"""Text/number formatting"""

class ByteCountFormatter(object):
    #pylint: disable=too-few-public-methods

    """Human-readable display of byte counts in various formats.

    By default, the formatter uses SI and bytes, so 1000 => "1 KB". All
    combinations of (byte, bit) x (SI, binary) are supported, though you
    probably shouldn't use bits with the binary prefixes.

    Attributes:
        unit_bits    True for bits or False for bytes
        prefix_si    True for SI or False for binary prefixes
    """

    SI_prefixes = ('k', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    binary_prefixes = ('Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi', 'Yi')

    def __init__(self):
        self.unit_bits = False
        self.prefix_si = True

    def __call__(self, count):

        """Formats a byte count using the configured settings."""

        if self.unit_bits:
            count *= 8
            unit = 'b'
        else:
            unit = 'B'

        if self.prefix_si:
            factor = 1000.
            prefixes = self.SI_prefixes
        else:
            factor = 1024.
            prefixes = self.binary_prefixes

        if abs(count) < factor:
            return u'%d %c' % (count, unit)
        size = float(count)
        prefix_index = 0
        while abs(size) >= factor and prefix_index < len(prefixes):
            size /= factor
            prefix_index += 1
        return u'%.2f %s%c' % (size, prefixes[prefix_index-1], unit)
