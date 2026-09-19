"""Telethon adapter. Only own archive/pinned/active stories, never chats/viewers."""
import datetime as dt
from pathlib import Path
from .exporter import FloodDelay,ExpiredReference

class TelegramGateway:
    def __init__(self,client):self.client=client;self.raw={}
    async def request(self,request):
        from telethon import errors
        try:return await self.client(request)
        except errors.FloodWaitError as e:raise FloodDelay(e.seconds) from None
    def normalize(self,story):
        from telethon import types
        sid=story.id
        if not isinstance(story,types.StoryItem):return {'id':sid,'status':'deleted' if isinstance(story,types.StoryItemDeleted) else 'skipped'}
        self.raw[sid]=story
        media=story.media
        photo=getattr(media,'photo',None);doc=getattr(media,'document',None)
        if not isinstance(photo,types.Photo):photo=None
        if not isinstance(doc,types.Document):doc=None
        kind='image' if photo else 'video' if doc and getattr(doc,'mime_type','').startswith('video/') else 'unsupported'
        dimensions={}
        if photo:
            sizes=[s for s in photo.sizes if getattr(s,'w',0) and getattr(s,'h',0)]
            if sizes:
                size=max(sizes,key=lambda s:s.w*s.h);dimensions={'width':size.w,'height':size.h}
        if doc:
            dimensions['bytes']=doc.size
            for a in doc.attributes:
                if isinstance(a,types.DocumentAttributeVideo):dimensions.update(width=a.w,height=a.h,duration=a.duration)
        # Deliberately whitelist source fields; omit views/reactions/contacts.
        return {'id':sid,'status':'available','date':story.date.astimezone(dt.timezone.utc).isoformat(),
                'caption':story.caption or '', 'entities':[e.to_dict() for e in story.entities or []],
                'privacy':{k:bool(getattr(story,k,False)) for k in ('public','close_friends','contacts','selected_contacts','noforwards')},
                'privacy_rules':[x.to_dict() for x in getattr(story,'privacy',[]) or []],
                'kind':kind,'media_id':str(getattr(photo or doc,'id',sid)),**dimensions}
    async def page(self,source,offset,limit):
        from telethon.tl.functions import stories
        if source=='archive':request=stories.GetStoriesArchiveRequest(peer='me',offset_id=offset,limit=limit)
        elif source=='pinned':request=stories.GetPinnedStoriesRequest(peer='me',offset_id=offset,limit=limit)
        else:request=stories.GetPeerStoriesRequest(peer='me')
        result=await self.request(request)
        items=result.stories.stories if source=='active' else result.stories
        return [self.normalize(s) for s in items]
    async def refresh(self,sid):
        from telethon.tl.functions import stories
        result=await self.request(stories.GetStoriesByIDRequest(peer='me',id=[sid]))
        if not result.stories:raise ValueError('Story unavailable')
        return self.normalize(result.stories[0])
    async def download(self,item,path):
        from telethon import errors
        try:
            # File object prevents Telethon appending an extension to .part.
            with Path(path).open('wb') as f:
                await self.client.download_media(self.raw[item['id']].media,file=f)
        except errors.FloodWaitError as e:raise FloodDelay(e.seconds) from None
        except (errors.FileReferenceExpiredError,errors.FileReferenceInvalidError):raise ExpiredReference() from None
