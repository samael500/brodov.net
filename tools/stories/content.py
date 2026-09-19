"""Front matter and deterministic monthly archives in Europe/Moscow."""
import argparse
import datetime as dt
import json
from pathlib import Path
import shutil
import tomllib
from zoneinfo import ZoneInfo
import yaml

ROOT = Path(__file__).resolve().parents[2]
ZONE = ZoneInfo('Europe/Moscow')
MONTHS = ('январь февраль март апрель май июнь июль август сентябрь октябрь ноябрь декабрь').split()

def read_front(path):
    text = Path(path).read_text()
    if text.startswith('{'):
        data, pos = json.JSONDecoder().raw_decode(text)
        return data, text[pos:].lstrip()
    delim = text.splitlines()[0] if text else ''
    if delim not in ('---', '+++'):
        raise ValueError(f'Нет front matter: {path}')
    _, front, body = text.split(delim, 2)
    return (yaml.safe_load(front) if delim == '---' else tomllib.loads(front)), body.lstrip()

def timestamp(value):
    if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
        value = dt.datetime.combine(value, dt.time())
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZONE)
    return value.astimezone(ZONE)

def month_key(value):
    return timestamp(value).strftime('%Y-%m')

def count_label(n):
    word = 'историй' if 11 <= n % 100 <= 14 else ('история' if n % 10 == 1 else 'истории' if n % 10 in (2,3,4) else 'историй')
    return f'{n} {word}'

def page(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')

def collect(root, preview=False, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    groups = {}
    for path in sorted((Path(root)/'content/shorts').glob('*/index.md')):
        meta, _ = read_front(path)
        date = timestamp(meta['date'])
        if (meta.get('draft', False) and not preview) or date > now:
            continue
        if meta.get('expiryDate') and timestamp(meta['expiryDate']) <= now:
            continue
        if meta.get('publishDate') and timestamp(meta['publishDate']) > now:
            continue
        frames = meta.get('frames', [])
        if not frames:
            raise ValueError(f'Нет кадров: {path}')
        for frame in frames:
            if frame.get('kind') not in ('image','video'):
                raise ValueError(f'Неизвестный тип кадра: {path}')
            for key in ('src', 'poster'):
                if frame.get(key):
                    asset = (path.parent/frame[key]).resolve()
                    if not asset.is_relative_to(path.parent.resolve()) or not asset.is_file():
                        raise ValueError(f'Отсутствующий или внешний ресурс {key}: {path}')
            if frame['kind']=='video' and not frame.get('poster'):
                raise ValueError(f'Видео без poster: {path}')
        cover=meta.get('cover',{})
        if not isinstance(cover,dict) or not cover.get('src'):
            raise ValueError(f'Обложка не задана: {path}')
        asset=(path.parent/cover['src']).resolve()
        if not asset.is_relative_to(path.parent.resolve()) or not asset.is_file():
            raise ValueError(f'Обложка отсутствует: {path}')
        groups.setdefault(month_key(date), []).append({'path':'/shorts/'+path.parent.name, 'date':date})
    for stories in groups.values():
        stories.sort(key=lambda x:(-x['date'].timestamp(), x['path']))
    return groups

def prepare(root=ROOT, preview=False, now=None):
    root=Path(root)
    groups=collect(root,preview,now)
    out=root/'.shorts-generated'
    if out.exists(): shutil.rmtree(out)
    out.mkdir()
    for key, stories in sorted(groups.items()):
        year, month=key.split('-'); label=MONTHS[int(month)-1]
        page(out/f'shorts/{year}/{month}/_index.md', {
            'title':f"А что за поворотом · {label} '{year[-2:]}",
            'description':f'{label.capitalize()} {year} — {count_label(len(stories))} из бортового журнала.',
            'type':'short-month','date':stories[0]['date'].isoformat(),
            'monthkey':key, 'monthname':label,'storyrefs':[s['path'] for s in stories],
            'social_title':f'А что за поворотом\n{label} {year}',
            'outputs':['HTML'],
        })
        page(out/f'shorts/{year}/_index.md',{'title':f'А что за поворотом · {year}', 'type':'short-year','outputs':['HTML']})
    return groups

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--preview',action='store_true');p.add_argument('--root',type=Path,default=ROOT)
    a=p.parse_args();groups=prepare(a.root,a.preview)
    print(f'Shorts: {len(groups)} months, {sum(map(len,groups.values()))} stories; preview={a.preview}')
