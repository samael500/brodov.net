"""Check public output: metadata, local assets, and absence of drafts."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, unquote, urljoin
import json
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else 'public')
preview = '--preview' in sys.argv

class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.assets = []
        self.links = []
        self.ids = set()
        self.canonical = ''
        self.in_schema = False
        self.schema = ''
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'): self.ids.add(a['id'])
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if a.get('srcset'): self.assets.extend(item.strip().split()[0] for item in a['srcset'].split(','))
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
parsed = {}
for path in pages:
    page = Page(); page.feed(path.read_text()); parsed[path.resolve()] = page
assert pages, 'No HTML output'
for path in pages:
    p = parsed[path.resolve()]
    if 'http-equiv="refresh"' in path.read_text() or 'http-equiv=refresh' in path.read_text():
        assert p.canonical, (path, "Alias without canonical")
        continue
    for key in ['description', 'og:title', 'og:description', 'og:image', 'twitter:card']:
        assert p.meta.get(key), (path, key)
    assert urlparse(p.canonical).scheme in ('http', 'https'), path
    assert urlparse(p.meta['og:image']).scheme in ('http', 'https'), path
    relative = path.relative_to(root).as_posix()
    actual = '/' + (relative[:-10] if relative.endswith('index.html') else relative)
    assert urlparse(p.canonical).path == actual, (path, 'Incorrect canonical', p.canonical)
    assert p.meta.get('og:url') == p.canonical, (path, 'OG URL differs from canonical')
    assert p.meta.get('twitter:image') == p.meta['og:image'], (path, 'Social images differ')
    for link in p.links:
        target = urlparse(urljoin(p.canonical, link))
        if target.scheme not in ('http', 'https') or target.netloc != urlparse(p.canonical).netloc: continue
        dest = root / unquote(target.path.lstrip('/'))
        if dest.is_dir(): dest /= 'index.html'
        assert dest.is_file(), (path, 'Broken internal link', link)
        if target.fragment and dest.resolve() in parsed:
            assert unquote(target.fragment) in parsed[dest.resolve()].ids or target.fragment == 'frame-last', (path, 'Missing anchor', link)
    for url in p.assets + [p.meta['og:image']]:
        if re.fullmatch(r'https://mc\.yandex\.ru/watch/[1-9][0-9]*', url):
            assert not preview, (path, 'Analytics leaked into preview')
            continue
        asset = root / unquote(urlparse(url).path.lstrip('/'))
        assert asset.is_file(), (path, 'Missing asset', asset)
    if p.schema: assert json.loads(p.schema)['@type'] == 'BlogPosting'
    if preview: assert p.meta.get('robots') == 'noindex, nofollow', path
    else: assert 'Черновик' not in path.read_text(), path
if not preview:
    for md in Path('content/posts').rglob('index.md'):
        if 'draft: true' in md.read_text().split('---')[1]:
            assert not (root / md.parent / 'index.html').exists()
            assert not (root / 'posts' / md.parent.name).exists(), ('Draft media leaked', md.parent.name)
            for feed in ('index.xml', 'sitemap.xml'):
                assert '/posts/' + md.parent.name + '/' not in (root / feed).read_text(), ('Draft in feed', md.parent.name)
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
for css in root.rglob('*.css'):
    for raw in re.findall(r'url\(([^)]+)\)', css.read_text()):
        raw = raw.strip(' \"\'')
        if raw.startswith(('data:', 'http:', 'https:')): continue
        asset = root / raw.lstrip('/') if raw.startswith('/') else css.parent / raw
        assert asset.is_file(), (css, 'Missing CSS resource', raw)
assert '404.html' not in (root / 'sitemap.xml').read_text()
assert 'noindex' in parsed[(root / '404.html').resolve()].meta.get('robots', '')
print(f'OK: {len(pages)} pages, metadata and assets checked; preview={preview}')
