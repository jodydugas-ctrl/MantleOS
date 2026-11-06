"""Repository preparation must preserve shared bytes and reproducible releases."""
import importlib.util
from pathlib import Path, PurePosixPath
import posixpath
import re
import tempfile
import tomllib
import unittest


ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools/export_kpp.py').is_file())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectExportTests(unittest.TestCase):
    def test_organ_shelves_link_to_single_canonical_manifests(self):
        files = load(ROOT / 'tools/export_kpp.py', 'project_export_shelves').source_map(ROOT)
        base = 'pantry/organs/'
        pages = {name: blob.decode() for name, blob in files.items() if name.startswith(base)}
        self.assertEqual({name.removeprefix(base) for name in pages},
                         {'README.md', 'heart/README.md', 'senses/README.md', 'nervous-system/README.md',
                          'immune-system/README.md', 'limbs/README.md', 'memory/README.md'})
        for name, content in pages.items():
            self.assertEqual(files['src/mantleos/kpp/resources/' + name], files[name])
            for target in re.findall(r'\]\(([^)]+)\)', content):
                self.assertIn(posixpath.normpath(str(PurePosixPath(name).parent / target)), files)
        for organ in ('heart', 'memory'):
            self.assertIn('../../sleep-memory-consolidation.json', pages[base + organ + '/README.md'])
        self.assertIn('../text-editor.json', pages[base + 'README.md'])

    def test_install_metadata_keeps_runtime_dependency_free_and_licenses_scoped(self):
        files = load(ROOT / 'tools/export_kpp.py', 'project_export_metadata').source_map(ROOT)
        metadata = tomllib.loads(files['pyproject.toml'].decode())
        self.assertEqual(metadata['project']['dependencies'], [])
        self.assertEqual(metadata['project']['scripts'], {'kpp': 'mantleos.kpp.cli:main'})
        self.assertIn('LicenseRef-MantleOS-Reserved', metadata['project']['license'])
        for name in ('LICENSE', 'THIRD-PARTY-NOTICES.md', 'shared/licenses/MantleOS/LICENSE'):
            self.assertIn(name, files)
        self.assertEqual(files['.gitattributes'].splitlines()[-1], b'* -text')

    def test_export_is_reproducible_from_the_new_primary_project(self):
        exporter = load(ROOT / 'tools/export_kpp.py', 'project_export_roundtrip')
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / 'first', Path(directory) / 'second'
            exporter.export(first, ROOT)
            standalone = load(first / 'tools/export_kpp.py', 'standalone_export_roundtrip')
            standalone.export(second, first)
            self.assertEqual(exporter.check(second, ROOT)['result'], 'PASS')
            refresh = load(first / 'tools/refresh_release.py', 'standalone_refresh')
            # Git worktrees use a metadata pointer FILE instead of a directory.
            # It must not become shipped source or break exact inventory checks.
            (first / '.git').write_text('gitdir: ../synthetic-metadata\n',encoding='utf8')
            self.assertEqual(refresh.refresh(first)['result'], 'PASS')
            self.assertEqual(standalone.check(first,first)['result'],'PASS')
            self.assertNotIn('.git',standalone.source_map(first))

    def test_refresh_refuses_stale_generated_views_and_unrepresented_source(self):
        exporter = load(ROOT / 'tools/export_kpp.py', 'project_export_drift')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'project'
            exporter.export(output, ROOT)
            refresh = load(output / 'tools/refresh_release.py', 'refresh_drift')
            before = (output / 'SHA256SUMS.json').read_bytes()
            readme = output / 'README.md'
            original = readme.read_bytes()
            readme.write_text('Unreviewed root-only change', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Generated views differ'):
                refresh.refresh(output)
            self.assertEqual((output / 'SHA256SUMS.json').read_bytes(), before)
            readme.write_bytes(original)
            (output / 'unexpected-source.py').write_text('pass', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unrepresented source'):
                refresh.refresh(output)
