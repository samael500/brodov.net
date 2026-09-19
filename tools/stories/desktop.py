"""Offline Desktop export -> private archive, without Telegram credentials."""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
from .exporter import atomic_json, digest, read_json
from .importer import inside
from .desktop_html import captions_from_html


def ingest_desktop(source, out):
    source = Path(source).expanduser().resolve()
    data_path = source / 'result.json' if source.is_dir() else source
    source = data_path.parent
    out = Path(out).expanduser().resolve()
    if out == source or out.is_relative_to(source) or source.is_relative_to(out):
        raise ValueError('Source and archive must be separate directories')
    rows = read_json(data_path).get('stories')
    if not isinstance(rows, list):
        raise ValueError('Expected a Desktop JSON export with a stories array')
    manifest = read_json(out / 'manifest.json', {
        'version': 1, 'origin': 'telegram-desktop', 'stories': {}, 'sources': {},
    })
    if manifest.get('origin') != 'telegram-desktop':
        raise ValueError('Use a separate archive for Desktop exports')
    html_captions = captions_from_html(source)
    prepared = []
    rows = [dict(row) for row in rows]
    for row in rows:
        media = inside(source, row.get('media', ''))
        if html_captions is not None:
            local_date = dt.datetime.fromisoformat(row['date']).strftime('%d.%m.%Y %H:%M:%S')
            html = html_captions.get(local_date)
            if html is None or (html['media_path'] is not None and html['media_path'] != media):
                raise ValueError('Story missing or mismatched in HTML')
            row.update(caption=html['caption'], entities=html['entities'], caption_origin='desktop-html')
        date = dt.datetime.fromtimestamp(int(row['date_unixtime']), dt.timezone.utc)
        if not media.is_file() and html_captions is not None:
            candidates = [e for e in manifest['stories'].values() if e['date'] == date.isoformat() and e['status'] == 'complete']
            if len(candidates) > 1:
                raise ValueError('Ambiguous archived media for missing export file')
            if candidates:
                previous = candidates[0]
                archived = inside(out, previous['media'])
                if digest(archived) != previous['sha256']:
                    raise ValueError('Archived media checksum mismatch')
                media = archived
        prepared.append((row, media, date))
    out.mkdir(parents=True, exist_ok=True)
    os.chmod(out, 0o700)
    # Copy only stories metadata, never unrelated personal export sections.
    snapshot_hash = hashlib.sha256(json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    atomic_json(out / 'exports' / f'{snapshot_hash}.json', {'stories': rows})
    current_keys = set()
    for row, media, date in prepared:
        suffix = media.suffix.lower()
        kind = 'image' if suffix in ('.jpg', '.jpeg', '.png', '.webp') else 'video' if suffix in ('.mp4', '.mov') else 'unsupported'
        available = media.is_file() and media.stat().st_size > 0
        checksum = digest(media) if available else None
        identity = checksum or hashlib.sha256(str(row.get('media', '')).encode()).hexdigest()
        # Desktop omits story IDs. Ignore unstable numbered export filenames.
        key = f'desktop-{int(date.timestamp())}-{identity}'
        current_keys.add(key)
        folder = out / 'stories' / key
        folder.mkdir(parents=True, exist_ok=True)
        meta = {
            'date': date.isoformat(), 'caption': '', 'entities': [], 'privacy': {},
            'kind': kind, 'origin': 'telegram-desktop', 'desktop': row,
            'caption_available': False, 'media_id': checksum,
        }
        # Pinned is not an audience setting; leave privacy unknown.
        caption = row.get('caption', row.get('text'))
        if isinstance(caption, str):
            meta.update(caption=caption, caption_available=True, entities=row.get('entities', []))
        elif isinstance(caption, list):
            meta['caption'] = ''.join(x if isinstance(x, str) else x.get('text', '') for x in caption)
            meta['entities'] = [x for x in caption if isinstance(x, dict)]
            meta['caption_available'] = True
        previous = manifest['stories'].get(key)
        if previous and not meta['caption_available']:
            old = read_json(inside(out, previous['source']))
            if old.get('caption_available'):
                for field in ('caption', 'entities', 'caption_available'):
                    meta[field] = old[field]
                meta['caption_preserved_from_previous_export'] = True
        fingerprint = hashlib.sha256(json.dumps(
            {k: meta[k] for k in ('date', 'caption', 'entities', 'privacy', 'kind', 'media_id')},
            sort_keys=True, ensure_ascii=False,
        ).encode()).hexdigest()
        meta['source_hash'] = fingerprint
        atomic_json(folder / f'source-{snapshot_hash[:16]}.json', meta)
        atomic_json(folder / 'source.json', meta)
        entry = {
            'key': key, 'date': date.isoformat(), 'kind': kind,
            'source': str((folder / 'source.json').relative_to(out)),
            'source_hash': fingerprint, 'sources': ['desktop'],
            'status': 'missing' if not available else 'unsupported' if kind == 'unsupported' else 'complete',
        }
        if entry['status'] == 'complete':
            dest = folder / ('original' + suffix)
            if not dest.is_file() or digest(dest) != checksum:
                part = dest.with_suffix(dest.suffix + '.part')
                shutil.copyfile(media, part)
                os.chmod(part, 0o600)
                if digest(part) != checksum:
                    raise ValueError('Source changed while copying')
                part.replace(dest)
            entry.update(media=str(dest.relative_to(out)), sha256=checksum, bytes=dest.stat().st_size)
        manifest['stories'][key] = entry
        atomic_json(out / 'manifest.json', manifest)
    manifest['updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
    manifest['sources']['desktop'] = {
        'status': 'imported', 'records': len(rows), 'unique': len(current_keys),
        'complete': sum(manifest['stories'][k]['status'] == 'complete' for k in current_keys),
        'captions_present': sum('caption' in row or 'text' in row for row in rows),
        'nonempty_captions': sum(bool(row.get('caption', row.get('text'))) for row in rows),
        'html_matched': len(prepared) if html_captions is not None else 0,
        'snapshot': snapshot_hash,
        'note': 'Полнота относительно Telegram не проверена. Desktop не сообщает ID историй и аудиторию. Подписи могут отсутствовать.',
    }
    atomic_json(out / 'manifest.json', manifest)
    return manifest
