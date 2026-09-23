"""Static GPX route map for Brodov.net. Run with --help."""
from pathlib import Path
import argparse,json,math,hashlib,urllib.request,urllib.parse,xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, fontManager
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('config',type=Path)
parser.add_argument('--fetch',action='store_true',help='Fetch OSM once; ordinary renders use local cache only')
args=parser.parse_args();config_path=args.config.resolve();cfg=json.loads(config_path.read_text());base=config_path.parent
root=Path(__file__).resolve().parent
ns={'g':'http://www.topografix.com/GPX/1/1'}
gpx=base/cfg['gpx'];xml=ET.parse(gpx).getroot();segs=[s for s in xml.findall('.//g:trkseg',ns) if s.findall('g:trkpt',ns)]
if len(segs)!=1:raise SystemExit('Expected one continuous GPX track segment; split multi-segment tracks explicitly.')
pts=[]
for t in segs[0].findall('g:trkpt',ns):
 pts.append([float(t.attrib['lat']),float(t.attrib['lon']),float(t.findtext('g:ele',default='nan',namespaces=ns))])
a=np.array(pts)
if len(a)<2:raise SystemExit('At least two track points required.')
lat,lon,ele=a.T
if not np.isfinite(a[:,:2]).all() or np.any(abs(lat)>85) or np.any(abs(lon)>180):raise SystemExit('Invalid or unsupported coordinates.')
if np.ptp(lat)>5 or np.ptp(lon)>5:raise SystemExit('This local map projection supports routes within a 5-degree extent only.')
r=6371.0088;la=np.radians(lat);lo=np.radians(lon)
d=2*r*np.arcsin(np.minimum(1,np.sqrt(np.sin(np.diff(la)/2)**2+np.cos(la[:-1])*np.cos(la[1:])*np.sin(np.diff(lo)/2)**2)))
km=np.r_[0,np.cumsum(d)]
if km[-1]<=0:raise SystemExit('Track has no distance.')
x=r*np.cos(np.mean(la))*(lo-lo[0]);y=r*(la-la[0])
cache=base/cfg.get('cache','cache');cache.mkdir(parents=True,exist_ok=True)
bounds=[float(min(lat)-.025),float(min(lon)-.035),float(max(lat)+.025),float(max(lon)+.035)]
b=','.join(map(str,bounds));digest=hashlib.sha256(gpx.read_bytes()).hexdigest()
if args.fetch:
 selectors={'base':['way[waterway~"river|stream"]','way[natural=water]','way[natural=wood]','way[landuse=forest]','way[highway~"primary|secondary|tertiary"]','node[place~"town|village|hamlet"]'], 'landcover':['way[landuse~"farmland|meadow|pasture|grass|forest|orchard"]','relation[landuse~"farmland|meadow|pasture|grass|forest|orchard"]','relation[natural~"wood|water|grassland|wetland"]','way[natural~"grassland|wetland"]']}
 pending={}
 for name,sel in selectors.items():
  query='[out:json][timeout:45];('+''.join(s+'('+b+');' for s in sel)+');out geom;'
  url=cfg.get('overpass_endpoint','https://overpass-api.de/api/interpreter')+'?'+urllib.parse.urlencode({'data':query})
  req=urllib.request.Request(url,headers={'User-Agent':'BrodovRouteGenerator/1.0'})
  data=json.loads(urllib.request.urlopen(req,timeout=60).read())
  if 'remark' in data or not isinstance(data.get('elements'),list):raise SystemExit('Incomplete OSM response; cache not updated.')
  pending[name]=data
 for name,data in pending.items():(cache/(name+'.json')).write_text(json.dumps(data))
 (cache/'manifest.json').write_text(json.dumps({'gpx_sha256':digest,'bbox':bounds}))
manifest=json.loads((cache/'manifest.json').read_text())
if manifest['gpx_sha256']!=digest:raise SystemExit('GPX changed: use a separate cache or refresh with --fetch.')
ink='#35312F';paper='#FAF8F3';accent='#A6533D';muted='#82796D'
fonts=root.parent.parent/'vendor/brodov-style/fonts'
fp=FontProperties(fname=str(fonts/'literata.ttf'))
fontManager.addfont(str(fonts/'pt-sans.ttf'))
plt.rcParams.update({'font.family':'PT Sans','text.color':ink,'axes.labelcolor':muted,'xtick.color':muted,'ytick.color':muted,'font.size':10})
output=base/cfg.get('output','route');output.parent.mkdir(parents=True,exist_ok=True)
step=float(cfg.get('marker_every_km',20))
if step<=0:raise SystemExit('marker_every_km must be positive.')

import matplotlib.patheffects as pe
from matplotlib.lines import Line2D
osm=json.loads((cache/'base.json').read_text())['elements']
def proj(lon,lat):return r*np.cos(np.mean(la))*(np.radians(lon)-lo[0]),r*(np.radians(lat)-la[0])
fig=plt.figure(figsize=(10,12),facecolor=paper)
fig.text(.08,.951,cfg.get('brand','БРОДОВ НЕТ  /  ЖУРНАЛ ОБЫКНОВЕННЫХ НЕВЕРОЯТНОСТЕЙ'),fontsize=10,color=muted)
fig.text(.08,.903,cfg['title'],fontproperties=fp,fontsize=32)
fig.text(.08,.871,cfg['subtitle'],fontsize=12)
ax=fig.add_axes([.06,.31,.88,.52],facecolor=paper);ax.set_aspect('equal');ax.axis('off');ax.set_xlim(min(x)-1.5,max(x)+1.5);ax.set_ylim(min(y)-1.8,max(y)+1.8)
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch
cover=json.loads((cache/'landcover.json').read_text())['elements']
palette={'farmland':'#F3EDD9','meadow':'#E9ECDf','pasture':'#E9ECDf','grass':'#EBEEDF','grassland':'#E9ECDf','orchard':'#E0E5D3','forest':'#DDE3D1','wood':'#DDE3D1','wetland':'#E3EBE5','water':'#D3E2E5'}
def stitch(segments):
 segments=[list(g) for g in segments if len(g)>1];rings=[]
 while segments:
  line=segments.pop()
  while line[0]!=line[-1]:
   found=False
   for j,s in enumerate(segments):
    if line[-1]==s[0]:line+=s[1:]
    elif line[-1]==s[-1]:line+=s[-2::-1]
    elif line[0]==s[-1]:line=s[:-1]+line
    elif line[0]==s[0]:line=s[:0:-1]+line
    else:continue
    segments.pop(j);found=True;break
   if not found:break
  if line[0]==line[-1]:rings.append(line)
 return rings
# Avoid painting relation members twice, especially inner rings.
member_ids={m['ref'] for e in cover if e['type']=='relation' for m in e.get('members',[]) if m['type']=='way'}
for e in cover:
 t=e.get('tags',{});kind=t.get('landuse',t.get('natural'));color=palette.get(kind)
 if not color:continue
 groups=[]
 if e['type']=='way':
  if e['id'] in member_ids:continue
  g=e.get('geometry',[])
  if g:groups=[('outer',[(v['lon'],v['lat']) for v in g])]
 else:
  for role in ['outer','inner']:
   segments=[[(v['lon'],v['lat']) for v in m['geometry']] for m in e.get('members',[]) if m.get('geometry') and (m.get('role') or 'outer')==role]
   groups.extend((role,ring) for ring in stitch(segments))
 verts=[];codes=[]
 for role,g in groups:
  if len(g)<4 or g[0]!=g[-1]:continue
  xx,yy=proj(np.array([v[0] for v in g]),np.array([v[1] for v in g]));coords=np.column_stack([xx,yy]);area=np.sum(xx[:-1]*yy[1:]-xx[1:]*yy[:-1])
  if (role=='outer' and area<0) or (role=='inner' and area>0):coords=coords[::-1]
  verts.extend(coords);codes.extend([MPath.MOVETO]+[MPath.LINETO]*(len(coords)-2)+[MPath.CLOSEPOLY])
 if verts:ax.add_patch(PathPatch(MPath(verts,codes),facecolor=color,edgecolor='none',zorder=-2 if kind in ['farmland','meadow','pasture','grass','grassland'] else -1))

for e in osm:
 g=e.get('geometry');t=e.get('tags',{})
 if not g:continue
 xx,yy=proj(np.array([v['lon'] for v in g]),np.array([v['lat'] for v in g]))
 if t.get('natural')=='wood' or t.get('landuse')=='forest':ax.fill(xx,yy,color='#DDE3D1',lw=0,zorder=0)
 elif t.get('natural')=='water':ax.fill(xx,yy,color='#CADDE0',lw=0,zorder=1)
 elif 'waterway' in t:ax.plot(xx,yy,color='#AEC9D0',lw=.85 if t['waterway']=='river' else .45,zorder=1)
 elif 'highway' in t:ax.plot(xx,yy,color='#D8D0C2',lw=.75,zorder=1)
# Fade the geographic background only; labels and route remain above it.
from matplotlib.colors import to_rgb
u=np.linspace(0,1,700)
edge=np.minimum(u,1-u)
t=np.clip(edge/.065,0,1)
smooth=t*t*(3-2*t)
mask=np.ones((700,700,4))
mask[:,:,:3]=to_rgb(paper)
mask[:,:,3]=1-smooth[:,None]*smooth[None,:]
ax.imshow(mask,extent=(*ax.get_xlim(),*ax.get_ylim()),origin='lower',interpolation='bilinear',zorder=1.5,aspect='equal')

# Settlements: use source labels, select a spaced subset.
placed=[]
for e in sorted([v for v in osm if v['type']=='node'],key=lambda e:0 if e['tags'].get('place')=='town' else 1):
 t=e['tags'];name=t.get('name:ru',t.get('name',''))
 if not name:continue
 px,py=proj(e['lon'],e['lat'])
 if not (min(x)-1<px<max(x)+1 and min(y)-1<py<max(y)+1):continue
 if py<min(y)-.1 or (px>max(x)-1 and py>max(y)-2):continue
 if any((px-u)**2+(py-v)**2<15 for u,v in placed):continue
 placed.append((px,py));ax.scatter(px,py,s=7,c='#9A9184',zorder=2)
 label=ax.annotate(name,(px,py),xytext=(4,4),textcoords='offset points',fontsize=8,color='#756E64',zorder=2);label.set_path_effects([pe.withStroke(linewidth=2,foreground=paper)])
ax.plot(x,y,color=paper,lw=3.5,zorder=3);route_line,=ax.plot(x,y,color=accent,lw=1.8,zorder=4)
for target in np.arange(step,km[-1],step):
 i=np.searchsorted(km,target);ax.scatter(x[i],y[i],s=26,c=paper,edgecolors=accent,zorder=5);txt=ax.annotate(f'{target:g}',(x[i],y[i]),xytext=(7,7),textcoords='offset points',fontsize=9,zorder=6);txt.set_path_effects([pe.withStroke(linewidth=3,foreground=paper)])
closed=np.hypot(x[-1],y[-1])<.2
for px,py,label in ([(0,0,'Старт / финиш')] if closed else [(0,0,'Старт'),(x[-1],y[-1],'Финиш')]):
 ax.scatter(px,py,s=60,c=ink,edgecolors=paper,zorder=7);ax.annotate(label,(px,py),xytext=(12,-16),textcoords='offset points',fontsize=9,bbox=dict(facecolor=paper,edgecolor='none',pad=2),zorder=8)

ax.plot([.06,.06+3/(ax.get_xlim()[1]-ax.get_xlim()[0])],[.035,.035],transform=ax.transAxes,color=muted,lw=2);ax.text(.06,.05,'3 км',transform=ax.transAxes,fontsize=8,color=muted)
fig.text(.08,.283,f'Отметки через {step:g} км · © OpenStreetMap contributors · openstreetmap.org/copyright',fontsize=9,color=muted)
fig.text(.08,.247,'ПРОФИЛЬ ВЫСОТЫ',fontsize=10,color=muted)
p=fig.add_axes([.08,.105,.84,.105],facecolor=paper)
clean=ele.copy();gaps=[]
for gap in cfg.get('elevation_gaps',[]):
 left=np.searchsorted(km,float(gap['from_km']));right=np.searchsorted(km,float(gap['to_km']))
 if not 0<left<right<len(km)-1:raise SystemExit('Elevation gap must be inside the track.')
 clean[left:right+1]=np.nan;gaps.append((left,right))
valid=clean[np.isfinite(clean)]
if not len(valid):raise SystemExit('No valid elevations: profile cannot be rendered.')
ymin=float(min(valid))-5;ymax=float(max(valid))+15
stride=max(1,len(km)//2500);idx=np.unique(np.r_[np.arange(0,len(km),stride),len(km)-1,*[j for l,h in gaps for j in [l-1,l,h,h+1]]])
p.plot(km[idx],clean[idx],color=accent,lw=1);p.fill_between(km[idx],clean[idx],ymin,color=accent,alpha=.1)
for left,right in gaps:
 if np.isfinite(ele[left-1]) and np.isfinite(ele[right+1]):p.plot([km[left-1],km[right+1]],[ele[left-1],ele[right+1]],ls=':',lw=1.5,color='#537D8B')
p.set_xlim(0,km[-1]);p.set_ylim(ymin,ymax);p.set_xlabel('Расстояние по GPS, км',fontsize=9);p.set_ylabel('Высота, м',fontsize=9);p.spines[['top','right']].set_visible(False)
for k in ['left','bottom']:p.spines[k].set_color('#D8D1C6')
p.grid(axis='y',color='#E5DED3',lw=.5)
if gaps:fig.text(.08,.04,cfg.get('gap_note','Пунктир — пропуск недостоверных показаний, не восстановленный рельеф.'),fontsize=8,color=muted)
for extension in ['png','svg']:
 fig.savefig(output.with_suffix('.'+extension),dpi=170,facecolor=paper)
print(f'Rendered {output}: {len(km)} points, {km[-1]:.2f} GPS km')

# A separate homepage asset: geographic background and complete route only.
# Export from the same axes, without cropping the route or changing its geometry.
if cfg.get('preview_output'):
 # Full-size exports above keep their original stroke.
 route_line.set_linewidth(2.5)
 preview_output=base/cfg['preview_output']
 preview_output.parent.mkdir(parents=True,exist_ok=True)
 for artist in list(ax.texts)+list(ax.collections):
  artist.set_visible(False)
 # The scale bar is the only line in axes coordinates (roads use data coordinates).
 for line in ax.lines:
  if line.get_transform()==ax.transAxes:
   line.set_visible(False)
 ax.text(.02,.015,'© OpenStreetMap contributors',transform=ax.transAxes,
         fontsize=8,color=muted,zorder=10,
         bbox=dict(facecolor=paper,edgecolor='none',pad=2))
 fig.canvas.draw()
 bounds=ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
 fig.savefig(preview_output,dpi=170,facecolor=paper,bbox_inches=bounds,pad_inches=0)
 print(f'Rendered homepage preview: {preview_output}')
