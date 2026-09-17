# Brand invariants

Persistent product, editorial, illustration, workflow, and roadmap context is
kept in `docs/PROJECT-CONTEXT.md`. Keep accepted decisions separate from open
questions when updating it.

The approved logo is a fixed asset, not a generation prompt.

- `design/logo-master/` is immutable v1. Never overwrite its PNG, layers, SVG,
  or manifest. Verify `sha256.json` before deriving assets.
- NEVER send the master to an image generator for recoloring, background
  changes, resizing, removing text, or compositing. Use `scripts/logo.py` or
  the existing named SVG layers. Preserve geometry and alpha coverage.
- Exploratory generative variants are separate candidates and cannot replace
  the master without explicit approval of the new drawing by the user.
- A genuinely approved drawing revision gets a new version directory and a
  new manifest; preserve v1 and document the change.
- Three layers: illustration, wordmark, tagline. The wordmark is approved
  hand-adjusted Literata-derived lettering without distress. The current
  tagline is raster lettering, not a real editable PT Sans text object.
- `master.svg` contains raster alpha masks. Do not describe it as a vector
  tracing. True vectorization is a separate task requiring visual approval.
- Approved palette: warm ink #35312F and light paper #FAF8F3.
- The pizza article text and four illustrations are approved and published at
  `/posts/pizza/` with date 2026-09-13. Do not change its text, date, URL, or
  metadata as part of unrelated work.
- Do not modify maks.live or its repository; use a separate new repository for brodov.net.

- Route maps and homepage thumbnails must follow the approved route-map rules
  in `docs/PROJECT-CONTEXT.md` (section «Карты маршрутов — утверждённые правила»).
  Keep full-map and thumbnail styling separate: route strokes are 1.8 pt and
  2.5 pt respectively; previews are chosen independently of article photos.
