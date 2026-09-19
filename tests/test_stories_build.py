"""Integration checks against the pinned Hugo, using an isolated site."""
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from stories.content import ROOT,page,prepare

class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[];self.assets=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=='a':self.links.append((a.get('class',''),a.get('href','')))
  if tag=='img':self.assets.append(a.get('src'))

def parsed(path):
 p=Links();p.feed(path.read_text());return p

@unittest.skipUnless(shutil.which('hugo'),'Hugo is needed for integration')
class BuildTests(unittest.TestCase):
 def test_mixed_feed_archives_rss_and_production_isolation(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   for name in ('assets','layouts','static'):shutil.copytree(ROOT/name,root/name)
   (root/'hugo.toml').write_text((ROOT/'hugo.toml').read_text().replace('pagerSize = 10','pagerSize = 3'))
   (root/'content/shorts').mkdir(parents=True);shutil.copy2(ROOT/'content/shorts/_index.md',root/'content/shorts/_index.md')
   def story(slug,date,draft=False):
    bundle=root/'content/shorts'/slug;bundle.mkdir()
    Image.new('RGB',(64,96),'green').save(bundle/'photo.jpg')
    page(bundle/'index.md',{'title':slug,'description':'Тест','type':'shorts','date':date,'draft':draft,'cover':{'src':'photo.jpg','alt':'Тестовый кадр'},'frames':[{'kind':'image','src':'photo.jpg','alt':'Тест','caption':'Подпись <script>alert(1)</script>'}]})
   for month,count in ((9,1),(8,8),(7,9),(6,23)):
    for i in range(count):story(f'm{month}-{i:02}',f'2026-{month:02}-10T12:00:00+03:00')
   story('same-month-other-year','2025-08-10T12:00:00+03:00')
   story('moscow-boundary','2026-08-31T21:01:00Z')
   story('hidden-draft','2026-09-18T12:00:00Z',True)
   story('hidden-future','2099-01-01T00:00:00Z')
   for i,date in enumerate(('2026-09-12','2026-08-15','2026-07-15','2026-06-15')):
    page(root/f'content/posts/post-{i}/index.md',{'title':f'Пост {i}','date':date,'description':'Тестовая статья','draft':False})
   now=dt.datetime(2026,9,19,tzinfo=dt.timezone.utc);groups=prepare(root,now=now)
   self.assertEqual(len(groups['2026-09']),2)
   def build():subprocess.run(['hugo','--source',str(root),'--cleanDestinationDir'],check=True,capture_output=True)
   build();public=root/'public'
   pages=[public/'index.html']+sorted((public/'page').glob('*/index.html'))
   urls=[]
   for p in pages:
    if 'http-equiv="refresh"' in p.read_text():continue
    for cls,href in parsed(p).links:
     if cls=='read':urls.append(href)
    # Monthly section heading links occur exactly once in the chronological feed.
    import re
    urls.extend(re.findall(r'<h2><a href="([^"]+/shorts/\d{4}/\d{2}/|/shorts/\d{4}/\d{2}/)"',p.read_text()))
   self.assertEqual(len(urls),9);self.assertEqual(len(set(urls)),9)
   alltext=''.join(p.read_text() for p in pages)
   self.assertNotIn('hidden-draft',alltext);self.assertNotIn('hidden-future',alltext)
   self.assertIn('Весь июль',alltext);self.assertIn('23 истории',alltext)
   # Each month archive contains every story once over its own pagination.
   for month,count in ((9,2),(8,8),(7,9),(6,23)):
    folder=public/f'shorts/2026/{month:02}'
    paths=[folder/'index.html']+sorted((folder/'page').glob('*/index.html'));cards=[]
    for p in paths:
     if 'http-equiv="refresh"' in p.read_text():continue
     cards += [url for cls,url in parsed(p).links if cls=='short-card']
    self.assertEqual(len(cards),count);self.assertEqual(len(set(cards)),count)
   xml=ET.parse(public/'index.xml');feed=[x.text for x in xml.findall('./channel/item/link')]
   self.assertEqual(len(feed),47) # 43 shorts + 4 articles
   self.assertFalse(any('/shorts/2026/' in x for x in feed))
   for slug in ('hidden-draft','hidden-future'):
    self.assertFalse((public/'shorts'/slug).exists())
    self.assertNotIn(slug,(public/'sitemap.xml').read_text())
   short=(public/'shorts/m9-00/index.html').read_text();self.assertNotIn('<script>alert(1)</script>',short)
   self.assertIn('&lt;script&gt;',short);self.assertIn('data-neighbour',short)
   first=(public/'index.html').read_bytes();build();self.assertEqual(first,(public/'index.html').read_bytes())

if __name__=='__main__':unittest.main()
