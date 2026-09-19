"""Resumable own-story archive. Transport is injectable for offline tests."""
import asyncio
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

class FloodDelay(Exception):
    def __init__(self, seconds): self.seconds=seconds
class ExpiredReference(Exception): pass

def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def atomic_json(path, data):
    path=Path(path);path.parent.mkdir(parents=True, exist_ok=True)
    part=path.with_suffix(path.suffix+'.part')
    with part.open('w') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    os.chmod(part,0o600);part.replace(path)

def read_json(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default

async def retry(operation, sleep=asyncio.sleep):
    while True:
        try:return await operation()
        except FloodDelay as e:
            print(f'Telegram просит подождать {e.seconds} с; прогресс сохранён. Ctrl+C — безопасная остановка.')
            await sleep(e.seconds)

async def list_source(gateway, source, limit=None, sleep=asyncio.sleep):
    records={};offset=0;seen_offsets=set()
    while True:
        batch=await retry(lambda:gateway.page(source,offset,min(limit or 100,100)),sleep)
        if not batch:return list(records.values()),'complete'
        fresh=False
        for item in batch:
            if item['id'] not in records:records[item['id']]=item;fresh=True
        if source=='active':return list(records.values()),'complete'
        next_offset=min(item['id'] for item in batch)
        if not fresh or next_offset==offset or next_offset in seen_offsets:
            return list(records.values()),'stopped_no_progress'
        if limit and len(records)>=limit:return list(records.values())[:limit],'limited'
        seen_offsets.add(offset);offset=next_offset

def source_fingerprint(item):
    # Exclude volatile file references, counters and source membership.
    value={k:item.get(k) for k in ('date','caption','entities','privacy','privacy_rules','media_id','kind')}
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

async def export_archive(gateway,out,owner,limit=None,sleep=asyncio.sleep):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);os.chmod(out,0o700)
    manifest=read_json(out/'manifest.json',{'version':1,'owner_id':owner,'stories':{},'sources':{}})
    if manifest['owner_id']!=owner:raise ValueError('Архив принадлежит другому аккаунту')
    merged={};manifest['sources']={}
    def save():atomic_json(out/'manifest.json',manifest)
    for source in ('archive','pinned','active'):
        try:
            items,status=await list_source(gateway,source,limit,sleep)
            manifest['sources'][source]={'status':status,'count':len(items)}
            for item in items:
                key=f'{owner}-{item["id"]}'
                if key not in merged:merged[key]=dict(item,sources=[])
                elif merged[key].get('status')!='available' and item.get('status')=='available':
                    merged[key]=dict(item,sources=merged[key]['sources'])
                merged[key]['sources'].append(source)
        except Exception as e:
            manifest['sources'][source]={'status':'unavailable','error':type(e).__name__}
        save()
    ordered=sorted(merged.items(),key=lambda kv:kv[1]['id'],reverse=True)
    if limit:ordered=ordered[:limit]
    manifest['limited']=bool(limit)
    manifest['updated_at']=dt.datetime.now(dt.timezone.utc).isoformat()
    for key,item in ordered:
        previous=manifest['stories'].get(key,{})
        folder=out/'stories'/key;folder.mkdir(parents=True,exist_ok=True)
        fingerprint=source_fingerprint(item)
        metadata=dict(item,owner_id=owner,source_hash=fingerprint)
        # Keep snapshots as well as the newest metadata.
        atomic_json(folder/f'source-{fingerprint[:16]}.json',metadata)
        atomic_json(folder/'source.json',metadata)
        entry=dict(previous,key=key,source=f'stories/{key}/source.json',source_hash=fingerprint,
                   sources=item['sources'],date=item.get('date',''),media_id=item.get('media_id'),changed_source=previous.get('changed_source',False) or bool(previous.get('source_hash') and previous['source_hash']!=fingerprint))
        manifest['stories'][key]=entry
        if item.get('status')!='available' or item.get('kind') not in ('image','video'):
            entry['status']=item.get('status','unavailable') if item.get('status')!='available' else 'unsupported';save();continue
        suffix='.jpg' if item['kind']=='image' else '.mp4'
        name=f'media-{item["media_id"]}{suffix}'
        dest=folder/name;part=folder/(name+'.part')
        previous_file=(out/previous.get('media','')).resolve()
        if previous.get('status')=='complete' and previous.get('media_id')==item['media_id'] and previous_file.is_relative_to(out.resolve()) and previous_file.is_file() and digest(previous_file)==previous.get('sha256'):
            entry['status']='complete';save();continue
        entry['status']='pending';save()
        try:
            for attempt in range(2):
                try:
                    if part.exists():part.unlink()
                    await retry(lambda:gateway.download(item,part),sleep)
                    if not part.is_file() or not part.stat().st_size:raise ValueError('Empty download')
                    checksum=digest(part)
                    # Never overwrite a differing immutable original.
                    if dest.exists() and digest(dest)!=checksum:dest=folder/f'media-{item["media_id"]}-{checksum[:12]}{suffix}'
                    os.chmod(part,0o600);part.replace(dest)
                    entry.update(status='complete',media=str(dest.relative_to(out)),sha256=checksum,bytes=dest.stat().st_size,kind=item['kind'])
                    entry.pop('error',None);break
                except ExpiredReference:
                    if attempt:raise
                    item=await retry(lambda:gateway.refresh(item['id']),sleep)
            save()
        except Exception as e:
            entry.update(status='error',error=type(e).__name__);save()
    # Missing stories are not deleted locally or from the blog.
    save();return manifest
