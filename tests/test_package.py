import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]


class PackageTests(unittest.TestCase):
    def test_archive_reproducible_and_runtime_only(self):
        spec = importlib.util.spec_from_file_location('build_package', ROOT / 'scripts/build-package.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        archive = module.build()
        first = archive.read_bytes()
        module.build()
        self.assertEqual(first, archive.read_bytes())
        with zipfile.ZipFile(archive) as package:
            self.assertIsNone(package.testzip())
            self.assertFalse(any(name.endswith(('.sublime-syntax', '.sublime-snippet', '.sublime-build', '.tmPreferences')) for name in package.namelist()))
            self.assertNotIn('Forge.sublime-settings', package.namelist())
            self.assertIn('LSP-Forge.py', package.namelist())
            self.assertFalse(any(name.startswith(('tests/', 'scripts/', '.git/', 'build/')) for name in package.namelist()))
            self.assertNotIn('package-metadata.json', package.namelist())
            self.assertEqual(package.read('.python-version').decode().strip(), '3.8')
        expected = archive.with_name(archive.name + '.sha256').read_text().split()[0]
        self.assertEqual(hashlib.sha256(first).hexdigest(), expected)

    def test_package_control_release_contract(self):
        data = json.loads((ROOT / 'packages.json').read_text())
        self.assertEqual(data['schema_version'], '4.0.0')
        package = data['packages'][0]
        self.assertEqual(package['name'], 'LSP-Forge')
        self.assertEqual(package['details'], 'https://github.com/forge-language/sublime-text')
        self.assertTrue(package['releases'][0]['tags'])
        self.assertEqual(package['releases'][0]['sublime_text'], '>=4132')


if __name__ == '__main__':
    unittest.main()
