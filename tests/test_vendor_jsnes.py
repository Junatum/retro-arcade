"""Offline fixture tests for the one-time official JSNES package importer."""
import base64
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts import vendor_jsnes


def tar_fixture():
    data = {
        'package/package.json': json.dumps({'name': 'jsnes', 'version': '2.1.0', 'license': 'Apache-2.0'}).encode(),
        'package/LICENSE': b'Apache License\nVersion 2.0',
        'package/src/nes.js': b'import Controller from "./controller.js";\nexport default class NES {}\n',
        'package/src/controller.js': b'import {x} from "./utils.js";\nexport default class Controller {}\n',
        'package/src/utils.js': b'export const x = true;\n',
        'package/src/browser/index.js': b'// unrelated browser integration must not be copied\n',
    }
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for name, contents in data.items():
            info = tarfile.TarInfo(name)
            info.size = len(contents)
            archive.addfile(info, io.BytesIO(contents))
    return stream.getvalue()


class VendorJsnesTests(unittest.TestCase):
    def test_manifest_source_closure_integrity_and_license(self):
        tarball = tar_fixture()
        sri = 'sha512-' + base64.b64encode(hashlib.sha512(tarball).digest()).decode()
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(vendor_jsnes, 'ROOT', Path(tmp)):
                self.assertEqual(vendor_jsnes.vendor(tarball, sri), 0)
                target = Path(tmp) / 'web/vendor/jsnes'
                files = list(target.rglob('*.js'))
                self.assertEqual(len(files), 3)
                self.assertFalse((target / 'src/browser/index.js').exists())
                self.assertTrue((Path(tmp) / 'LICENSES/JSNES.txt').exists())
                mf = json.loads((target / 'manifest.json').read_text())
                self.assertEqual(set(mf['files']), {'src/nes.js', 'src/controller.js', 'src/utils.js'})
                self.assertEqual(mf['npm_integrity'], sri)
                self.assertEqual(hashlib.sha256((target / 'src/nes.js').read_bytes()).hexdigest(), mf['files']['src/nes.js'])
        with self.assertRaises(ValueError):
            vendor_jsnes.verify_integrity(tarball + b'changed', sri)

    def test_rejects_modules_escaping_jsnes_source_tree(self):
        src = b'import X from "../../outside.js";\n'
        arc = tar_fixture()
        with tarfile.open(fileobj=io.BytesIO(arc), mode='r:gz') as tf:
            files = {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}
        files['package/src/nes.js'] = src
        stream = io.BytesIO()
        with tarfile.open(fileobj=stream, mode='w:gz') as tar:
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        with self.assertRaises(ValueError):
            vendor_jsnes.unpack_source(stream.getvalue())


if __name__ == '__main__':
    unittest.main()
