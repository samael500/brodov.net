"""Explicit selection -> new draft bundles; never rewrite existing editorial work."""
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
from .content import ROOT,timestamp,page
from .exporter import read_json,atomic_json,digest
from .media import image_derivative,video_derivative

def inside(base,relative):
    p=(Path(base)/relative).resolve()
    if not p.is_relative_to(Path(base).resolve()):raise ValueError('Path escapes archive')
    return p

def import_selection(archive,selection,root=ROOT):
    archive=Path(archive).resolve();root=Path(root).resolve()
    manifest=read_json(archive/'manifest.json')
    selection=read_json(selection) if isinstance(selection,(str,Path)) else selection
    index_path=archive/'imports.json';imports=read_json(index_path,{})
    results=[];seen=set()
    for story in selection.get('stories',[]):
        keys=story['keys']
        if not keys or len(set(keys))!=len(keys) or seen.intersection(keys):raise ValueError('Duplicate or empty selection')
        seen.update(keys)
        slug=story['slug']
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug):raise ValueError('Invalid slug')
        dest=root/'content/shorts'/slug
        known={imports[k]['slug'] for k in keys if k in imports}
        if known and known!={slug}:raise ValueError('A selected frame already belongs to another story')
        if dest.exists():
            if not known or any(k not in imports for k in keys):raise ValueError(f'Slug already exists or selection changed: {slug}')
            results.append({'slug':slug,'status':'preserved','changed_source':any(imports[k]['source_hash']!=manifest['stories'][k]['source_hash'] for k in keys if k in imports)})
            continue
        entries=[]
        for key in keys:
            entry=manifest['stories'][key]
            if entry['status']!='complete':raise ValueError(f'Incomplete media: {key}')
            media=inside(archive,entry['media']);meta=read_json(inside(archive,entry['source']))
            if digest(media)!=entry['sha256']:raise ValueError('Source checksum mismatch')
            entries.append((key,entry,meta,media))
        dest.parent.mkdir(parents=True,exist_ok=True)
        # Build in a private staging directory outside Hugo; publish draft atomically.
        with tempfile.TemporaryDirectory(prefix='draft-',dir=archive) as temp:
            stage=Path(temp);frames=[]
            for i,(key,entry,meta,media) in enumerate(entries):
                override=story.get('frames',{}).get(key,{})
                caption=override.get('caption',meta.get('caption',''))
                if 'caption' not in override:
                    for entity in meta.get('entities',[]):
                        url=entity.get('url','')
                        if url.startswith(('https://','http://')) and url not in caption:caption+='\n'+url
                alt=override.get('alt','')
                if entry['kind']=='image':
                    name=f'frame-{i+1}.jpg';image_derivative(media,stage/name)
                    frame={'kind':'image','src':name,'alt':alt,'caption':caption}
                else:
                    name=f'frame-{i+1}.mp4';poster=f'frame-{i+1}-poster.jpg'
                    details=video_derivative(media,stage/name,stage/poster)
                    frame={'kind':'video','src':name,'poster':poster,'alt':alt,'caption':caption,'duration':details.get('duration')}
                frames.append(frame)
            date=timestamp(story.get('date',entries[0][2]['date']))
            title=story.get('title') or next((f['caption'].split('\n')[0][:65] for f in frames if f['caption'].strip()),f'Короткая история · {date:%d.%m.%Y}')
            description=next((f['caption'][:180] for f in frames if f['caption'].strip()),f'Фотоистория из журнала «Бродов нет», {date:%d.%m.%Y}.')
            tags=story.get('tags',[])
            if any('#цветыикроссовки' in f['caption'].lower() for f in frames) and 'цветыикроссовки' not in tags:tags=[*tags,'цветыикроссовки']
            cover_index=int(story.get('cover_frame',0));cover=frames[cover_index]
            pos=story.get('cover_position','50% 50%')
            if not re.fullmatch(r'(?:100|[0-9]{1,2})(?:\.\d+)?% (?:100|[0-9]{1,2})(?:\.\d+)?%',pos):raise ValueError('Invalid cover position')
            page(stage/'index.md',{'title':title,'description':description,'social_title':title[:65],
                'date':date.isoformat(),'draft':True,'type':'shorts','tags':tags,
                'cover':{'src':cover.get('poster',cover['src']),'position':pos,'alt':cover['alt']},'frames':frames})
            stage.rename(dest)
        for key,entry,meta,media in entries:imports[key]={'slug':slug,'source_hash':entry['source_hash']}
        atomic_json(index_path,imports)
        results.append({'slug':slug,'status':'created','missing_alt':any(not f['alt'] for f in frames)})
    return results
