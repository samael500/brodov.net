import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from stories.desktop import ingest_desktop
from stories.exporter import digest
from stories.importer import import_selection
from stories.review import create_review
from stories.content import read_front


class DesktopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / 'export'
        self.source.mkdir()
        self.out = self.base / 'archive'
        Image.new('RGB', (40, 60), 'blue').save(self.source / 'photo.jpg')
        self.row = {'date': 'wrong-local-date', 'date_unixtime': '1788215400',
                    'pinned': True, 'media': 'photo.jpg'}

    def tearDown(self):
        self.temp.cleanup()

    def write(self, rows):
        (self.source / 'result.json').write_text(json.dumps({'stories': rows, 'contacts': ['not copied']}))

    def test_repeat_renumber_and_draft(self):
        self.write([self.row])
        manifest = ingest_desktop(self.source, self.out)
        key, entry = next(iter(manifest['stories'].items()))
        self.assertEqual(entry['sha256'], digest(self.source / 'photo.jpg'))
        from datetime import datetime, timezone
        self.assertEqual(entry['date'], datetime.fromtimestamp(int(self.row['date_unixtime']), timezone.utc).isoformat())
        meta = json.loads((self.out / entry['source']).read_text())
        self.assertEqual(meta['privacy'], {})
        self.assertFalse(meta['caption_available'])
        self.assertNotIn('contacts', next((self.out / 'exports').glob('*.json')).read_text())
        self.assertIn('Отдельная подпись отсутствует', create_review(self.out).read_text())
        (self.source / 'photo.jpg').rename(self.source / 'renumbered.jpg')
        self.row['media'] = 'renumbered.jpg'
        self.write([self.row, self.row])
        again = ingest_desktop(self.source, self.out)
        self.assertEqual(list(again['stories']), [key])
        self.assertEqual(again['stories'][key]['source_hash'], entry['source_hash'])
        selection = {'stories': [{'slug': 'sample', 'keys': [key]}]}
        root = self.base / 'blog'
        import_selection(self.out, selection, root)
        path = root / 'content/shorts/sample/index.md'
        front, _ = read_front(path)
        self.assertTrue(front['draft'])
        self.assertTrue(front['date'].endswith('+03:00'))
        self.assertEqual(front['frames'][0]['caption'], '')
        before = path.read_bytes()
        import_selection(self.out, selection, root)
        self.assertEqual(path.read_bytes(), before)
        self.write([])
        self.assertIn(key, ingest_desktop(self.source, self.out)['stories'])

    def test_missing_unsupported_and_video(self):
        (self.source / 'clip.mp4').write_bytes(b'video-fixture')
        (self.source / 'other.bin').write_bytes(b'unsupported')
        self.write([dict(self.row, media=m) for m in ('missing.jpg', 'clip.mp4', 'other.bin')])
        m = ingest_desktop(self.source, self.out)
        self.assertEqual(sorted(e['status'] for e in m['stories'].values()), ['complete', 'missing', 'unsupported'])
        self.assertIn('<video', create_review(self.out).read_text())

    def test_escape_paths_and_symlinks(self):
        for name in ('../escape.jpg', '/tmp/escape.jpg', 'link.jpg'):
            if name == 'link.jpg':
                (self.source / name).symlink_to(self.base / 'outside.jpg')
            self.write([dict(self.row, media=name)])
            with self.assertRaises(ValueError):
                ingest_desktop(self.source, self.out)
            self.assertFalse(self.out.exists())

    def test_caption_escape_corruption_and_new_media(self):
        self.write([dict(self.row, caption='<script>alert(1)</script>')])
        m = ingest_desktop(self.source, self.out)
        entry = next(iter(m['stories'].values()))
        self.assertNotIn('<script>alert(1)</script>', create_review(self.out).read_text())
        (self.out / entry['media']).write_bytes(b'broken')
        ingest_desktop(self.source, self.out)
        self.assertEqual(digest(self.out / entry['media']), entry['sha256'])
        Image.new('RGB', (40, 60), 'red').save(self.source / 'photo.jpg')
        self.assertEqual(len(ingest_desktop(self.source, self.out)['stories']), 2)
        self.assertEqual(digest(self.out / entry['media']), entry['sha256'])

    def test_separate_archives(self):
        self.write([self.row])
        with self.assertRaises(ValueError):
            ingest_desktop(self.source, self.source / 'out')
        self.out.mkdir()
        (self.out / 'manifest.json').write_text('{"owner_id":42}')
        with self.assertRaises(ValueError):
            ingest_desktop(self.source, self.out)
