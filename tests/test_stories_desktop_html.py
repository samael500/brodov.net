import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from stories.desktop import ingest_desktop
from stories.exporter import read_json
from stories.review import create_review


class HTMLStoriesTests(unittest.TestCase):
    def test_enrich_missing_video_preserve_original_and_json_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/'export'; source.mkdir()
            (source/'video.mp4').write_bytes(b'original video')
            row = {'date': '2026-08-31T22:30:00', 'date_unixtime': '1788215400', 'media': 'video.mp4'}
            (source/'result.json').write_text(json.dumps({'stories': [row]}))
            out = root/'archive'; before = ingest_desktop(source, out)
            key = next(iter(before['stories']))
            (source/'lists').mkdir()
            (source/'lists/stories.html').write_text('''<div class="entry clearfix"><div class="body">
<div class="info details">31.08.2026 22:30:00</div><div class="name">Story unavailable</div>
<div class="text">#цветыикроссовки<br><br>Текст &amp; &lt;тег&gt; <b>жирный</b><br><a href="https://example.org/">ссылка</a></div>
</div></div>''')
            (source/'video.mp4').unlink()
            missing = dict(row, media='(Photo exceeds maximum size.)')
            (source/'result.json').write_text(json.dumps({'stories': [missing]}))
            after = ingest_desktop(source, out)
            self.assertEqual(list(after['stories']), [key])
            entry = after['stories'][key]
            self.assertEqual(entry['sha256'], before['stories'][key]['sha256'])
            self.assertEqual(entry['status'], 'complete')
            meta = read_json(out/entry['source'])
            self.assertEqual(meta['caption'], '#цветыикроссовки\n\nТекст & <тег> жирный\nссылка')
            self.assertEqual(meta['entities'], [{'url': 'https://example.org/'}])
            self.assertIn('&lt;тег&gt;', create_review(out).read_text())
            # A later caption-less JSON export must not erase recovered text.
            (source/'lists/stories.html').unlink()
            (source/'video.mp4').write_bytes(b'original video')
            (source/'result.json').write_text(json.dumps({'stories': [row]}))
            final = ingest_desktop(source, out)
            self.assertEqual(final['stories'][key]['source_hash'], entry['source_hash'])
            self.assertEqual(read_json(out/entry['source'])['caption'], meta['caption'])

    def test_mismatched_media_and_duplicate_dates_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/'export'; (source/'lists').mkdir(parents=True)
            row={'date':'2026-08-31T22:30:00','date_unixtime':'1788215400','media':'video.mp4'}
            (source/'result.json').write_text(json.dumps({'stories':[row]}))
            html='<div class="entry"><div class="info">31.08.2026 22:30:00</div><a href="../wrong.mp4">media</a><div class="text">caption</div></div>'
            for content in (html, html+html):
                (source/'lists/stories.html').write_text(content)
                with self.assertRaises(ValueError): ingest_desktop(source, root/'archive')
                self.assertFalse((root/'archive').exists())
