# SPDX-License-Identifier: GPL-3.0-or-later
"""Check that the bundled Retro Arcade icon has a transparent outer matte."""
import base64
import pathlib
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib

WEB = pathlib.Path(__file__).resolve().parents[1] / 'web'
PNG_MAGIC = b'\x89PNG\r\n\x1a\n'


def png_dimensions_and_corner_alpha(content):
    """Read PNG dimensions and top-left alpha using only Python's stdlib."""
    if not content.startswith(PNG_MAGIC):
        raise AssertionError('PNG signature missing')
    width, height, depth, color = struct.unpack_from('>IIBB', content, 16)
    if depth != 8 or color != 6:
        raise AssertionError('PNG must be 8-bit RGBA (not opaque RGB)')
    offset = 8
    data = bytearray()
    while offset + 12 <= len(content):
        size = struct.unpack_from('>I', content, offset)[0]
        kind = content[offset + 4:offset + 8]
        if kind == b'IDAT':
            data += content[offset + 8:offset + 8 + size]
        offset += 12 + size
        if kind == b'IEND':
            break
    decoded = zlib.decompress(data)
    # The first pixel has no left or upper neighbors, whatever the row filter.
    return (width, height), decoded[4]


class RetroArcadeIconAlphaTests(unittest.TestCase):
    def test_full_size_icon_has_transparent_background(self):
        image = (WEB / 'app-icon.png').read_bytes()
        size, alpha = png_dimensions_and_corner_alpha(image)
        self.assertEqual(size, (512, 512))
        self.assertEqual(alpha, 0)

    def test_ico_has_transparency_at_every_size(self):
        ico = (WEB / 'favicon.ico').read_bytes()
        self.assertEqual(ico[:4], b'\0\0\1\0')
        total = int.from_bytes(ico[4:6], 'little')
        dimensions = []
        for index in range(total):
            entry = ico[6 + index * 16:6 + (index + 1) * 16]
            length, offset = struct.unpack_from('<II', entry, 8)
            size, alpha = png_dimensions_and_corner_alpha(ico[offset:offset + length])
            dimensions.append(size)
            self.assertEqual(alpha, 0, f'ICO {size} corner is opaque')
        self.assertEqual(dimensions, [(16, 16), (32, 32), (48, 48)])

    def test_svg_has_small_self_contained_transparent_icon(self):
        data = (WEB / 'favicon.svg').read_bytes()
        self.assertLess(len(data), 64 * 1024, 'favicon SVG embeds an unnecessarily large image')
        root = ET.fromstring(data)
        self.assertEqual(root.tag, '{http://www.w3.org/2000/svg}svg')
        image = root.find('{http://www.w3.org/2000/svg}image')
        self.assertIsNotNone(image)
        href = image.attrib['href']
        self.assertTrue(href.startswith('data:image/png;base64,'))
        size, alpha = png_dimensions_and_corner_alpha(base64.b64decode(href.split(',', 1)[1], validate=True))
        self.assertEqual(size, (128, 128))
        self.assertEqual(alpha, 0)


if __name__ == '__main__':
    unittest.main()
