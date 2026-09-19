"""Offline, escaped contact sheet. Selection stays local until downloaded."""
import html
import json
from pathlib import Path
from urllib.parse import quote
from .exporter import read_json
from .importer import inside

def create_review(archive):
    archive=Path(archive);manifest=read_json(archive/'manifest.json');imports=read_json(archive/'imports.json',{})
    cards=[];data=[]
    for key,entry in sorted(manifest['stories'].items(),key=lambda kv:(kv[1].get('date',''),kv[0]),reverse=True):
        meta=read_json(inside(archive,entry['source']),{})
        escaped=lambda s:html.escape(str(s),quote=True)
        media=''
        if entry.get('status')=='complete':
            url=quote(entry['media'],safe='/')
            media=(f'<img src="{url}" loading="lazy" alt="">' if entry['kind']=='image' else f'<video src="{url}" controls playsinline preload="none"></video>')
        audience=', '.join(k for k,v in meta.get('privacy',{}).items() if v) or 'аудитория не указана'
        changed=key in imports and imports[key]['source_hash']!=entry.get('source_hash')
        caption=meta.get('caption','')
        caption_note='<p>Отдельная подпись отсутствует в экспорте.</p>' if meta.get('caption_available') is False else ''
        status=entry['status']+(' · исходник изменён' if changed else '')
        cards.append(f'''<article>{media}<p>{escaped(meta.get('date',''))} · {escaped(key[:36]+'…' if len(key)>36 else key)}</p><p>{escaped(audience)} · {escaped(status)}</p><p class="caption">{escaped(caption)}</p>{caption_note}
<label><input type="checkbox" data-key="{escaped(key)}" {'disabled' if entry['status']!='complete' else ''}> Выбрать</label>
<label>Группа (одинаковая для кадров одной истории)<input class="group" type="text" placeholder="Необязательно"></label>
<label>Порядок кадра<input class="order" type="number" min="1" value="1"></label>
<label>Заголовок истории<input class="title" type="text"></label>
<label>Описание изображения (alt)<input class="alt" type="text"></label></article>''')
        data.append({'key':key,'date':meta.get('date',''),'caption':caption})
    encoded=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    sources=html.escape(json.dumps(manifest.get('sources',{}),ensure_ascii=False,indent=2))
    script='''const source=JSON.parse(document.querySelector('#source').textContent);document.querySelector('#save').onclick=()=>{const groups=new Map();for(const checkbox of document.querySelectorAll('input[data-key]:checked')){const card=checkbox.closest('article'),key=checkbox.dataset.key,group=card.querySelector('.group').value.trim()||key;if(!groups.has(group))groups.set(group,[]);groups.get(group).push({key,order:Number(card.querySelector('.order').value),title:card.querySelector('.title').value,alt:card.querySelector('.alt').value});}const stories=[...groups.values()].map(items=>{items.sort((a,b)=>a.order-b.order);const first=source.find(x=>x.key===items[0].key);let hash=2166136261;for(const c of items.map(x=>x.key).join('-'))hash=Math.imul(hash^c.charCodeAt(0),16777619);return {slug:'story-'+first.date.slice(0,10)+'-'+(hash>>>0).toString(16),title:items.find(x=>x.title)?.title||'',keys:items.map(x=>x.key),frames:Object.fromEntries(items.map(x=>[x.key,{alt:x.alt}]))};});const blob=new Blob([JSON.stringify({version:1,stories},null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='selection.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};'''
    result='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Отбор собственных историй</title><style>body{font:17px/1.5 system-ui;background:#faf8f3;color:#35312f;padding:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:24px}article{padding:16px;border:1px solid #d6d0c7;border-radius:16px;min-width:0}img,video{width:100%;height:300px;object-fit:contain}.caption{white-space:pre-wrap;overflow-wrap:anywhere}label{display:block;margin:12px 0}input:not([type=checkbox]){width:100%;box-sizing:border-box}button{padding:14px;font:inherit}pre{white-space:pre-wrap}</style><h1>Отбор историй</h1><p>Выбери кадры. Для одной истории задай им одинаковую группу и порядок. Подписи сохраняются; изменения можно внести в черновике. Ничего не публикуется автоматически.</p><button id="save">Скачать selection.json</button><details><summary>Полнота выгрузки</summary><pre>'''+sources+'</pre></details><main>'+''.join(cards)+'</main><script type="application/json" id="source">'+encoded+'</script><script>'+script+'</script></html>'
    (archive/'review.html').write_text(result)
    return archive/'review.html'
