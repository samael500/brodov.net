"""Deterministic logo export. Requires Pillow only for asset editing."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageColor

MASTER = Path(__file__).resolve().parents[1] / 'design/logo-master'
parser = argparse.ArgumentParser()
parser.add_argument('--color', default='#35312f')
parser.add_argument('--background', default=None)
parser.add_argument('--hide', nargs='*', choices=['illustration', 'wordmark', 'tagline'], default=[])
parser.add_argument('--width', type=int, help='Optional output width; otherwise keep native pixels')
parser.add_argument('--trim', action='store_true', help='Crop transparent margins without modifying visible pixels')
parser.add_argument('--trim-bottom', action='store_true', help='Remove unused bottom margin, retaining 14 px below the layers')
parser.add_argument('--social-base', action='store_true', help='Export the blank opaque paper base for Hugo social compositions')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
for name, digest in json.loads((MASTER / 'sha256.json').read_text()).items():
    assert hashlib.sha256((MASTER / name).read_bytes()).hexdigest() == digest, f'Master changed: {name}'
assert args.width is None or args.width > 0
assert not args.output.resolve().is_relative_to(MASTER.resolve()), 'Never overwrite master assets'
manifest = json.loads((MASTER / 'layers.json').read_text())
canvas = Image.new('RGBA', tuple(manifest['canvas']), (0, 0, 0, 0))
color = ImageColor.getrgb(args.color)
for item in manifest['layers']:
    if item['id'] in args.hide:
        continue
    layer = Image.open(MASTER / item['file']).convert('RGBA')
    colored = Image.new('RGBA', layer.size, color + (255,))
    colored.putalpha(layer.getchannel('A'))
    canvas.alpha_composite(colored, tuple(item['offset']))
if args.trim:
    canvas = canvas.crop(canvas.getbbox())
if args.trim_bottom:
    canvas = canvas.crop((0, 0, canvas.width, canvas.getbbox()[3] + 14))
if args.width is not None and args.width != canvas.width:
    canvas = canvas.resize((args.width, round(canvas.height * args.width / canvas.width)), Image.Resampling.LANCZOS)
if args.background:
    paper = Image.new('RGBA', canvas.size, ImageColor.getrgb(args.background) + (255,))
    paper.alpha_composite(canvas)
    canvas = paper
if args.social_base:
    assert 'tagline' in args.hide, 'Hide the archived tagline for current branding'
    root = MASTER.parent.parent
    paper = Image.new('RGBA', (1200, 630), '#faf8f3')
    grain = Image.open(root / 'static/images/paper-grain.png').convert('RGBA')
    texture = Image.new('RGBA', paper.size)
    for y in range(0, paper.height, grain.height):
        for x in range(0, paper.width, grain.width):
            texture.alpha_composite(grain, (x, y))
    texture.putalpha(texture.getchannel('A').point(lambda a: round(a * .018)))
    paper.alpha_composite(texture)
    canvas = paper.convert('RGB')
args.output.parent.mkdir(parents=True, exist_ok=True)
canvas.save(args.output)
print(args.output)
