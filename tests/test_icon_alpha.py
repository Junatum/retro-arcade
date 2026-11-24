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


def png_alpha_info(content, corner=(0, 0)):
    """Read RGBA or tRNS-indexed PNG alpha and visible bounds without Pillow."""
    if not content.startswith(PNG_MAGIC):
        raise AssertionError('PNG signature missing')
    if len(content) < 33:
        raise AssertionError('PNG header is incomplete')
    width, height, depth, color, compression, filtering, interlace = struct.unpack_from(
        '>IIBBBBB', content, 16
    )
    if (width == 0 or height == 0 or depth != 8 or color not in (3, 6)
            or compression != 0 or filtering != 0 or interlace != 0):
        raise AssertionError('Only non-interlaced 8-bit RGBA or indexed PNG is supported')

    compressed = bytearray()
    transparency = None
    palette_size = 0
    offset = 8
    while offset + 12 <= len(content):
        size = struct.unpack_from('>I', content, offset)[0]
        kind = content[offset + 4:offset + 8]
        if offset + size + 12 > len(content):
            raise AssertionError('Invalid PNG chunk length')
        payload = content[offset + 8:offset + 8 + size]
        if kind == b'PLTE':
            if size % 3:
                raise AssertionError('Invalid indexed PNG palette')
            palette_size = size // 3
        elif kind == b'tRNS':
            transparency = payload
        elif kind == b'IDAT':
            compressed.extend(payload)
        offset += size + 12
        if kind == b'IEND':
            break

    if color == 3 and (not palette_size or not transparency
                       or len(transparency) > palette_size
                       or all(alpha == 255 for alpha in transparency)):
        raise AssertionError('Indexed PNG must have a transparent palette entry')

    bpp = 4 if color == 6 else 1
    stride = width * bpp
    pixels = zlib.decompress(compressed)
    if len(pixels) != (stride + 1) * height:
        raise AssertionError('Unexpected PNG scanline length')
    previous = bytearray(stride)
    minimum_x, minimum_y = width, height
    maximum_x, maximum_y = -1, -1
    corner_alpha = None
    cursor = 0
    for y in range(height):
        filter_type = pixels[cursor]
        cursor += 1
        row = bytearray(pixels[cursor:cursor + stride])
        cursor += stride
        for i in range(stride):
            left = row[i - bpp] if i >= bpp else 0
            above = previous[i]
            upper_left = previous[i - bpp] if i >= bpp else 0
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
            alpha = (row[x * 4 + 3] if color == 6
                     else transparency[row[x]] if row[x] < len(transparency) else 255)
            if (x, y) == corner:
                corner_alpha = alpha
            if alpha:
                minimum_x, minimum_y = min(minimum_x, x), min(minimum_y, y)
                maximum_x, maximum_y = max(maximum_x, x), max(maximum_y, y)
        previous = row
    if maximum_x < 0:
        raise AssertionError('Empty image')
    return ((width, height), corner_alpha,
            (minimum_x, minimum_y, maximum_x + 1, maximum_y + 1))


def png_dimensions_and_corner_alpha(content, corner=(0, 0)):
    size, alpha, _ = png_alpha_info(content, corner)
    return size, alpha


def png_alpha_bounds(content):
    return png_alpha_info(content)[2]


class RetroArcadeIconAlphaTests(unittest.TestCase):
    @staticmethod
    def _sample_indexed_png(alpha_values):
        """Tiny 8-bit palette PNG: transparent outer pixels, colored center."""
        def chunk(kind, data):
            return (struct.pack('>I', len(data)) + kind + data
                    + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff))
        header = struct.pack('>IIBBBBB', 3, 3, 8, 3, 0, 0, 0)
        palette = bytes([0, 0, 0, 255, 0, 255])
        # Rows use PNG filter 0; palette index 1 is the center pixel.
        raw = b'\x00\x00\x00\x00' + b'\x00\x00\x01\x00' + b'\x00\x00\x00\x00'
        return (PNG_MAGIC + chunk(b'IHDR', header) + chunk(b'PLTE', palette)
                + (chunk(b'tRNS', bytes(alpha_values)) if alpha_values is not None else b'')
                + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))

    def test_indexed_png_with_trns_keeps_transparency_and_visible_bounds(self):
        sample = self._sample_indexed_png([0, 255])
        self.assertEqual(png_dimensions_and_corner_alpha(sample), ((3, 3), 0))
        self.assertEqual(png_alpha_bounds(sample), (1, 1, 2, 2))

    def test_opaque_or_missing_trns_is_not_accepted_as_transparency(self):
        for values in (None, [255, 255]):
            with self.subTest(transparency=values):
                with self.assertRaisesRegex(AssertionError, 'transparent palette entry'):
                    png_dimensions_and_corner_alpha(self._sample_indexed_png(values))

    def test_full_size_icon_has_transparent_background(self):
        image = (WEB / 'app-icon.png').read_bytes()
        for corner in ((0, 0), (511, 0), (0, 511), (511, 511)):
            with self.subTest(corner=corner):
                size, alpha = png_dimensions_and_corner_alpha(image, corner)
                self.assertEqual(size, (512, 512))
                self.assertEqual(alpha, 0)

    def test_app_icon_uses_canvas_without_excess_padding(self):
        bounds = png_alpha_bounds((WEB / 'app-icon.png').read_bytes())
        left, top, right, bottom = bounds
        self.assertLessEqual(max(left, top, 512 - right, 512 - bottom), 4,
                             f'Excess transparent margin around icon: {bounds}')

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
