"""Read Desktop's stories HTML as inert text, preserving line breaks and links."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from .importer import inside


class StoriesHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.entry_depth = None
        self.caption_depth = None
        self.date_depth = None
        self.entries = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'div':
            self.depth += 1
            if 'entry' in classes:
                if self.current is not None:
                    raise ValueError('Nested story entry')
                self.entry_depth = self.depth
                self.current = {'paths': set(), 'parts': [], 'entities': [], 'date_parts': []}
            elif self.current is not None and 'info' in classes:
                self.date_depth = self.depth
            elif self.current is not None and 'text' in classes:
                self.caption_depth = self.depth
        if self.current is None:
            return
        if self.caption_depth is not None:
            if tag == 'br':
                self.current['parts'].append('\n')
            if tag == 'a' and attrs.get('href', '').startswith(('http://', 'https://')):
                self.current['entities'].append({'url': attrs['href']})
        elif tag == 'a' and 'href' in attrs:
            ref = urlsplit(attrs['href'])
            if not ref.scheme and not ref.netloc:
                self.current['paths'].add(unquote(ref.path))

    def handle_endtag(self, tag):
        if tag != 'div':
            return
        if self.date_depth == self.depth:
            self.date_depth = None
        if self.caption_depth == self.depth:
            self.caption_depth = None
        if self.entry_depth == self.depth:
            self.entries.append(self.current)
            self.current = None
            self.entry_depth = None
        self.depth -= 1

    def handle_data(self, data):
        if self.current is not None and self.date_depth is not None:
            self.current['date_parts'].append(data)
        if self.current is not None and self.caption_depth is not None:
            self.current['parts'].append(data)


def captions_from_html(source):
    source = Path(source).resolve()
    path = inside(source, 'lists/stories.html')
    if not path.is_file():
        return None
    parser = StoriesHTML()
    parser.feed(path.read_text(encoding='utf-8'))
    parser.close()
    if parser.current is not None:
        raise ValueError('Incomplete stories HTML')
    result = {}
    for entry in parser.entries:
        paths = {inside(source, str(Path('lists') / p)) for p in entry['paths']}
        if len(paths) > 1:
            raise ValueError('Ambiguous story media link')
        media = paths.pop() if paths else None
        date = ''.join(entry['date_parts']).strip()
        value = {'media_path': media, 'caption': ''.join(entry['parts']).strip(), 'entities': entry['entities']}
        if date in result:
            raise ValueError('Conflicting story captions')
        result[date] = value
    return result
