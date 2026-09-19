import asyncio
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from stories.content import collect,prepare,month_key,count_label,page,read_front
from stories.exporter import export_archive,list_source,FloodDelay,ExpiredReference,atomic_json
from stories.importer import import_selection
from stories.review import create_review
from stories.media import image_derivative
from PIL import Image

NOW=dt.datetime(2026,9,19,tzinfo=dt.timezone.utc)
def item(n,**kw):return dict(id=n,status='available',kind='image',media_id=str(n),date='2026-08-31T22:10:00+00:00',caption='Цветы #цветыикроссовки',entities=[],privacy={'public':True},**kw)
class Fake:
 def __init__(self):self.calls=[];self.items=[item(3),item(2),item(1)];self.downloads=0;self.fail=False;self.expired=False;self.flood=False
 async def page(self,source,offset,limit):
  self.calls.append((source,offset))
  if source=='pinned':return [self.items[0]] if not offset else []
  if source=='active':return [self.items[0]]
  return [x for x in self.items if not offset or x['id']<offset][:2]
 async def refresh(self,sid):return next(x for x in self.items if x['id']==sid)
 async def download(self,item,path):
  self.downloads+=1
  if self.flood:self.flood=False;raise FloodDelay(2)
  if self.expired:self.expired=False;raise ExpiredReference()
  if self.fail:self.fail=False;path.write_bytes(b'partial');raise OSError()
  Image.new('RGB',(80,120),'blue').save(path,'JPEG')

class StoriesTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.archive=self.root/'archive'
 def tearDown(self):self.tmp.cleanup()
 def run_export(self,gateway,**kwargs):return asyncio.run(export_archive(gateway,self.archive,42,**kwargs))
 def short(self,slug,date='2026-08-20T12:00:00+03:00',draft=False):
  bundle=self.root/'content/shorts'/slug;bundle.mkdir(parents=True)
  Image.new('RGB',(30,40)).save(bundle/'photo.jpg')
  page(bundle/'index.md',{'title':slug,'date':date,'draft':draft,'cover':{'src':'photo.jpg'},'frames':[{'kind':'image','src':'photo.jpg'}]})
 def test_moscow_boundary(self):
  self.assertEqual(month_key('2026-08-31T21:00:00Z'),'2026-09')
  self.assertEqual(month_key('2026-08-31T20:59:59Z'),'2026-08')
 def test_counts(self):
  self.assertEqual([count_label(x) for x in (0,1,2,5,11,21,22,23)],['0 историй','1 история','2 истории','5 историй','11 историй','21 история','22 истории','23 истории'])
 def test_groups_counts_years_and_drafts(self):
  self.assertFalse(prepare(self.root,now=NOW))
  for n in range(23):self.short(f'a{n:02}')
  self.short('older','2025-08-10T12:00:00Z');self.short('draft',draft=True);self.short('future','2099-01-01T00:00:00Z')
  groups=prepare(self.root,now=NOW);self.assertEqual(len(groups['2026-08']),23);self.assertEqual(len(groups['2025-08']),1)
  self.assertEqual(len(collect(self.root,True,NOW)['2026-08']),24)
  meta,_=read_front(self.root/'.shorts-generated/shorts/2026/08/_index.md');self.assertEqual(len(meta['storyrefs']),23)
 def test_repeated_page_stops(self):
  class Repeated(Fake):
   async def page(self,*args):return self.items[:1]
  records,status=asyncio.run(list_source(Repeated(),'archive'));self.assertEqual(status,'stopped_no_progress');self.assertEqual(len(records),1)
 def test_empty(self):
  g=Fake();g.items=[]
  async def page_(*args):return []
  g.page=page_;m=self.run_export(g);self.assertFalse(m['stories']);self.assertTrue(create_review(self.archive).is_file())
 def test_dedup_and_resume(self):
  g=Fake();m=self.run_export(g);self.assertEqual(len(m['stories']),3);self.assertEqual(g.downloads,3)
  self.assertEqual(m['stories']['42-3']['sources'],['archive','pinned','active'])
  self.run_export(g);self.assertEqual(g.downloads,3);self.assertIn(('archive',1),g.calls)
 def test_partial_retry(self):
  g=Fake();g.fail=True;m=self.run_export(g);self.assertEqual(m['stories']['42-3']['status'],'error')
  self.run_export(g);self.assertEqual(g.downloads,4);self.assertFalse(list(self.archive.rglob('*.jpg.part')))
 def test_flood_and_expired(self):
  g=Fake();g.flood=True;g.expired=True;wait=[]
  async def sleep(s):wait.append(s)
  m=self.run_export(g,sleep=sleep);self.assertEqual(wait,[2]);self.assertTrue(all(x['status']=='complete' for x in m['stories'].values()))
 def test_source_unavailable_and_skipped(self):
  g=Fake();base=g.page
  async def page_(source,offset,limit):
   if source=='pinned':raise OSError()
   return await base(source,offset,limit)
  g.page=page_;g.items.append({'id':0,'status':'deleted'})
  m=self.run_export(g);self.assertEqual(m['sources']['pinned']['status'],'unavailable');self.assertEqual(m['stories']['42-0']['status'],'deleted')
 def test_import_selection_preserves_editorial_changes(self):
  g=Fake();self.run_export(g)
  selection={'stories':[{'slug':'flowers','keys':['42-3','42-2'],'frames':{'42-3':{'alt':'Синие цветы'}}}]}
  result=import_selection(self.archive,selection,self.root);self.assertEqual(result[0]['status'],'created')
  p=self.root/'content/shorts/flowers/index.md';meta,_=read_front(p)
  self.assertTrue(meta['draft']);self.assertIn('цветыикроссовки',meta['tags']);self.assertEqual(len(meta['frames']),2)
  meta['title']='Авторская редактура';page(p,meta);old=p.read_bytes()
  g.items[0]['caption']='Новая подпись';self.run_export(g)
  result=import_selection(self.archive,selection,self.root);self.assertEqual(p.read_bytes(),old);self.assertTrue(result[0]['changed_source'])
  review=create_review(self.archive).read_text();self.assertIn('исходник изменён',review)
 def test_escape_caption(self):
  g=Fake();g.items[0]['caption']='</script><script>alert(1)</script><img onerror=x>'
  self.run_export(g);s=create_review(self.archive).read_text();self.assertNotIn('<script>alert(1)</script>',s);self.assertIn('&lt;img',s)
 def test_does_not_delete_missing(self):
  g=Fake();self.run_export(g);g.items=g.items[:1];m=self.run_export(g);self.assertEqual(len(m['stories']),3)
 def test_no_upscale_or_exif(self):
  src=self.root/'source.jpg';dest=self.root/'dest.jpg';im=Image.new('RGB',(80,40));exif=im.getexif();exif[274]=6;im.save(src,exif=exif)
  image_derivative(src,dest)
  with Image.open(dest) as output:self.assertEqual(output.size,(40,80));self.assertFalse(output.getexif())
 def test_video_record_and_download(self):
  g=Fake();g.items[0]['kind']='video';m=self.run_export(g);self.assertTrue(m['stories']['42-3']['media'].endswith('.mp4'))
 def test_owner_rejected(self):
  self.run_export(Fake())
  with self.assertRaises(ValueError):asyncio.run(export_archive(Fake(),self.archive,43))
 def test_checksum_mismatch_redownload(self):
  g=Fake();m=self.run_export(g);(self.archive/m['stories']['42-3']['media']).write_bytes(b'corrupt');self.run_export(g);self.assertEqual(g.downloads,4)
 def test_duplicate_selection_rejected(self):
  self.run_export(Fake())
  with self.assertRaises(ValueError):import_selection(self.archive,{'stories':[{'slug':'bad','keys':['42-3','42-3']}]},self.root)

if __name__=='__main__':unittest.main()
