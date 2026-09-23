"""Check the delivered blog/calendar resources share one package, not just a version label."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
package = ROOT / 'vendor/brodov-style'
output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'public')
for folder, glob in [('css', '*.css'), ('fonts', '*.woff2')]:
    for source in (package / folder).glob(glob):
        relative = source.relative_to(package)
        for destination in [output / 'brodov-style', output / 'sun-calendar/brodov-style']:
            assert (destination / relative).read_bytes() == source.read_bytes(), destination / relative
for css in list((output / 'brodov-style/css').glob('*.css')) + list((output / 'sun-calendar/brodov-style/css').glob('*.css')):
    for url in re.findall(r"url\(['\"]?([^)'\"]+)", css.read_text()):
        assert (css.parent / url).is_file(), (css, url)
for path in [output / 'index.html', output / 'sun-calendar/index.html']:
    assert 'brodov-style/css/brodov.css' in path.read_text(), path
print('Shared style: both outputs match the blog package; CSS/font paths resolve')
