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


def png_alpha_bounds(content):
    """Decode RGBA PNG row filters to measure actual visible icon bounds."""
    (width, height), _ = png_dimensions_and_corner_alpha(content)
    offset = 8
    compressed = bytearray()
    while offset + 12 <= len(content):
        size = struct.unpack_from('>I', content, offset)[0]
        kind = content[offset + 4:offset + 8]
        if kind == b'IDAT':
            compressed.extend(content[offset + 8:offset + 8 + size])
        offset += size + 12
        if kind == b'IEND':
            break
    stream = zlib.decompress(compressed)
    stride = width * 4
    previous = bytearray(stride)
    minimum_x, minimum_y = width, height
    maximum_x, maximum_y = -1, -1
    cursor = 0
    for y in range(height):
        filter_type = stream[cursor]
        cursor += 1
        row = bytearray(stream[cursor:cursor + stride])
        cursor += stride
        for i in range(stride):
            left = row[i - 4] if i >= 4 else 0
            above = previous[i]
            upper_left = previous[i - 4] if i >= 4 else 0
            if filter_type == 1:
                prediction = left
            elif filter_type == 2:
                prediction = above
            elif filter_type == 3:
                prediction = (left + above) // 2
            elif filter_type == 4:
                initial = left + above - upper_left
                distances = (abs(initial - left), abs(initial - above), abs(initial - upper_left))
                prediction = (left, above, upper_left)[distances.index(min(distances))]
            elif filter_type == 0:
                prediction = 0
            else:
                raise AssertionError(f'Unsupported PNG row filter: {filter_type}')
            row[i] = (row[i] + prediction) & 255
        for x in range(width):
            if row[x * 4 + 3]:
                minimum_x, minimum_y = min(minimum_x, x), min(minimum_y, y)
                maximum_x, maximum_y = max(maximum_x, x), max(maximum_y, y)
        previous = row
    assert maximum_x >= 0, 'Empty image'
    return (minimum_x, minimum_y, maximum_x + 1, maximum_y + 1)


class RetroArcadeIconAlphaTests(unittest.TestCase):
    def test_full_size_icon_has_transparent_background(self):
        image = (WEB / 'app-icon.png').read_bytes()
        size, alpha = png_dimensions_and_corner_alpha(image)
        self.assertEqual(size, (512, 512))
        self.assertEqual(alpha, 0)

    def test_app_icon_uses_canvas_without_excess_padding(self):
        bounds = png_alpha_bounds((WEB / 'app-icon.png').read_bytes())
        left, top, right, bottom = bounds
        self.assertLessEqual(max(left, top, 512 - right, 512 - bottom), 18,
                             f'Excess transparent margin around icon: {bounds}')
        self.assertGreaterEqual(min(left, top, 512 - right, 512 - bottom), 4,
                                f'Icon artwork is clipped against canvas border: {bounds}')

    def test_ico_has_transparency_at_every_size(self):
        ico = (WEB / 'favicon.ico').read_bytes()
        self.assertEqual(ico[:4], b'\0\0\1\0')
        total = int.from_bytes(ico[4:6], 'little')
        dimensions = []
        for index in range(total):
            entry = ico[6 + index * 16:6 + (index + 1) * 16]
            length, offset = struct.unpack_from('<II', entry, 8)
            content = ico[offset:offset + length]
            size, alpha = png_dimensions_and_corner_alpha(content)
            dimensions.append(size)
            self.assertEqual(alpha, 0, f'ICO {size} corner is opaque')
            left, top, right, bottom = png_alpha_bounds(content)
            self.assertLessEqual(max(left, top, size[0] - right, size[1] - bottom),
                                 max(2, round(size[0] * 0.04)),
                                 f'ICO {size} has excessive transparent padding')
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
        embedded = base64.b64decode(href.split(',', 1)[1], validate=True)
        size, alpha = png_dimensions_and_corner_alpha(embedded)
        self.assertEqual(size, (128, 128))
        self.assertEqual(alpha, 0)
        left, top, right, bottom = png_alpha_bounds(embedded)
        self.assertLessEqual(max(left, top, 128 - right, 128 - bottom), 6,
                             'Embedded SVG icon has excessive transparent padding')


if __name__ == '__main__':
    unittest.main()
