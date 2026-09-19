"""Check public output: metadata, local assets, and absence of drafts."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote
import json
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'public')
preview = '--preview' in sys.argv

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.assets = []
        self.canonical = ''
        self.in_schema = False
        self.schema = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta': self.meta[a.get('property', a.get('name'))] = a.get('content')
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical = a['href']
        if tag == 'link' and a.get('rel') == 'stylesheet': self.assets.append(a['href'])
        if tag == 'img': self.assets.append(a['src'])
        if tag == 'script' and a.get('src'): self.assets.append(a['src'])
        if tag in ('source', 'video') and a.get('src'): self.assets.append(a['src'])
        if tag == 'video' and a.get('poster'): self.assets.append(a['poster'])
        if tag == 'script' and a.get('type') == 'application/ld+json': self.in_schema = True
    def handle_data(self, data):
        if self.in_schema: self.schema += data
    def handle_endtag(self, tag):
        if tag == 'script': self.in_schema = False

pages = list(root.rglob('*.html'))
assert pages, 'No HTML output'
for path in pages:
    p = Page(); p.feed(path.read_text())
    if 'http-equiv="refresh"' in path.read_text() or 'http-equiv=refresh' in path.read_text():
        assert p.canonical, (path, "Alias without canonical")
        continue
    for key in ['description', 'og:title', 'og:description', 'og:image', 'twitter:card']:
        assert p.meta.get(key), (path, key)
    assert urlparse(p.canonical).scheme in ('http', 'https'), path
    assert urlparse(p.meta['og:image']).scheme in ('http', 'https'), path
    for url in p.assets + [p.meta['og:image']]:
        asset = root / unquote(urlparse(url).path.lstrip('/'))
        assert asset.is_file(), (path, 'Missing asset', asset)
    if p.schema: assert json.loads(p.schema)['@type'] == 'BlogPosting'
    if preview: assert p.meta.get('robots') == 'noindex, nofollow', path
    else: assert 'Черновик' not in path.read_text(), path
if not preview:
    for md in Path('content/posts').rglob('index.md'):
        if 'draft: true' in md.read_text().split('---')[1]:
            assert not (root / md.parent / 'index.html').exists()
            assert not (root / 'posts' / md.parent.name / 'index.html').exists()
if not preview:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from stories.content import collect
    allowed = {row['path'].strip('/') for rows in collect(Path.cwd()).values() for row in rows}
    for md in Path('content/shorts').glob('*/index.md'):
        relative = 'shorts/' + md.parent.name
        if relative not in allowed:
            assert not (root / relative).exists(), ('Excluded short leaked', relative)
    for path in root.rglob('*'):
        assert not path.name.endswith(('.session', '.session-journal', '.part')), ('Private file', path)
        assert path.name not in ('source.json', 'selection.json', 'imports.json'), ('Private metadata', path)
print(f'OK: {len(pages)} pages, metadata and assets checked; preview={preview}')
