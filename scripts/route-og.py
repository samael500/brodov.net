#!/usr/bin/python3
"""Export the Russian Trail map's existing SVG layer for credited OG composition.

Requires system python3-gi, gir1.2-rsvg-2.0.
The source/standalone map is never modified. The unlabelled intermediate lives
in assets/, not content/static; social-image.html supplies its visible OSM credit.
"""
from pathlib import Path
import copy
import re
import xml.etree.ElementTree as ET
import gi
gi.require_version('Rsvg', '2.0')
from gi.repository import Rsvg

root = Path(__file__).resolve().parents[1]
source = root / 'content/posts/russian-trail/route.svg'
output = root / 'assets/images/maps/russian-trail-og.png'
ns = {'s': 'http://www.w3.org/2000/svg'}
tree = ET.parse(source).getroot()
axes = copy.deepcopy(tree.find('.//s:g[@id="axes_1"]', ns))
route = axes.find('.//s:g[@id="line2d_370"]/s:path', ns)
assert route is not None and 'stroke: #a6533d' in route.attrib['style']
route.set('style', route.attrib['style'].replace('stroke-width: 1.8', 'stroke-width: 2.5'))
clip_id = re.fullmatch(r'url\(#(.+)\)', route.attrib['clip-path'])[1]
rect = tree.find(f'.//s:clipPath[@id="{clip_id}"]/s:rect', ns)
x, y, w, h = [float(rect.attrib[k]) for k in ('x', 'y', 'width', 'height')]
for node in list(axes):
    name = node.get('id', '')
    if name.startswith(('text_', 'PathCollection_')) or name == 'line2d_368':
        axes.remove(node)
svg = ET.Element('{%s}svg' % ns['s'], {'viewBox': f'{x} {y} {w} {h}', 'width': str(w), 'height': str(h)})
# Keep all defs (paths/clip paths), omit figure titles, profile and annotations.
for defs in tree.findall('.//s:defs', ns): svg.append(copy.deepcopy(defs))
svg.append(axes)
width = 1200; height = round(width * h / w)
svg.set('width', str(width)); svg.set('height', str(height))
background = ET.Element('{%s}rect' % ns['s'], {'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h), 'fill': '#faf8f3'})
svg.insert(0, background)
handle = Rsvg.Handle.new_from_data(ET.tostring(svg))
output.parent.mkdir(parents=True, exist_ok=True)
handle.get_pixbuf().savev(str(output), 'png', [], [])
print(output)
