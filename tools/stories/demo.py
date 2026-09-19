"""Generate an isolated noindex demo using local project media, never content/ in the repo."""
from pathlib import Path
import shutil
import subprocess
from .content import ROOT,page,prepare

def create_demo(out):
    out=Path(out).resolve()
    if out==ROOT or out.is_relative_to(ROOT):raise ValueError('Demo must be outside repo')
    out.mkdir(parents=True,exist_ok=True)
    for name in ('assets','layouts','static','content','config'):
        dst=out/name
        if dst.exists():shutil.rmtree(dst)
        shutil.copytree(ROOT/name,dst)
    shutil.copy2(ROOT/'hugo.toml',out/'hugo.toml')
    # Do not claim these are real Telegram stories: all visibly labelled test drafts.
    shorts=out/'content/shorts'
    for path in shorts.iterdir():
        if path.is_dir():shutil.rmtree(path)
    photos=[ROOT/'content/posts/russian-trail/trail-portrait.jpg',ROOT/'content/posts/night-swim/moon-swim.jpg',ROOT/'content/posts/night-swim/rusalka.png']
    dates=[f'2026-09-{18-i:02}T12:00:00+03:00' for i in range(12)]+['2026-08-21T12:00:00+03:00','2025-08-15T12:00:00+03:00']
    for i,date in enumerate(dates):
        bundle=shorts/f'preview-story-{i+1:02}';bundle.mkdir()
        photo=photos[i%len(photos)];shutil.copy2(photo,bundle/('photo'+photo.suffix))
        frames=[{'kind':'image','src':'photo'+photo.suffix,'alt':'Материал существующей статьи для проверки вёрстки','caption':'Тест просмотра · материал из существующей статьи. Это не новая история автора.'}]
        if i==0:
            shutil.copy2(photos[2],bundle/'landscape.png');frames.append({'kind':'image','src':'landscape.png','alt':'Иллюстрация заплыва','caption':'Проверка горизонтального кадра.\n'+('Длинная подпись должна читаться целиком, без обрезки. '*12)})
            subprocess.run(['ffmpeg','-nostdin','-v','error','-y','-f','lavfi','-i','color=c=0x35312f:s=320x240:d=2','-vf',"drawtext=text='VIDEO TEST':fontcolor=white:fontsize=24:x=(w-text_w)/2:y=(h-text_h)/2",'-c:v','libx264','-pix_fmt','yuv420p',str(bundle/'test.mp4')],check=True)
            shutil.copy2(photos[1],bundle/'poster.jpg')
            frames.append({'kind':'video','src':'test.mp4','poster':'poster.jpg','alt':'Технический видеокадр для проверки','caption':'Тест видео · воспроизведение только вручную.'})
        page(bundle/'index.md',{'title':f'Тест истории {i+1:02}','description':'Локальный пример интерфейса, не публикация автора.','date':date,'type':'shorts','draft':True,'cover':{'src':frames[0]['src'],'alt':frames[0]['alt'],'position':'50% 40%'},'frames':frames})
    prepare(out,preview=True)
    subprocess.run(['hugo','--source',str(out),'--environment','preview','--buildDrafts','--destination','preview','--cleanDestinationDir','--baseURL','http://localhost:8766/'],check=True)
    return out/'preview'

if __name__=='__main__':
    print(create_demo(ROOT.parent/'blog-preview/around-the-bend-site'))
