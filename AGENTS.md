# Repository workflow

- All new changes must be made on `dev`, never directly on the production branch.
- The production/default branch is currently `main` (called “master” by the user).
  Do not rename it without an explicit request.
- Before merging, open a pull request from `dev` to `main` for the repository
  owner's review. Run relevant checks and describe the concrete changes in the PR.
- Never merge or push directly to `main` to bypass the owner's review.
- An instruction to publish starts the PR/review workflow; it does not waive review.
- Merge only after the owner's review and explicit approval. Deploy only the
  approved production branch after merge, never `dev` or an unreviewed commit.
- Preserve unrelated local changes; stage only files belonging to the current task.

# Brand invariants

Persistent product, editorial, illustration, workflow, and roadmap context is
kept in `docs/PROJECT-CONTEXT.md`. Keep accepted decisions separate from open
questions when updating it.

The approved logo is a fixed asset, not a generation prompt.

- `vendor/brodov-style/brand/logo-master/` is immutable v1. Never overwrite its PNG, layers, SVG,
  or manifest. Verify `sha256.json` before deriving assets.
- NEVER send the master to an image generator for recoloring, background
  changes, resizing, removing text, or compositing. Use `vendor/brodov-style/scripts/logo.py` or
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
- Approved page palette (22.09.2026, “Чуть нежнее”): ink #35312F, paper #FFFDF9,
  secondary text #77675B, dividers #E9DED3. OG compositions also use #FFFDF9
  as approved on 23.09.2026. Existing logo and map/image pixels keep their
  original colors (including #FAF8F3); do not recolor the source artwork.
- The pizza article text and four illustrations are approved and published at
  `/posts/pizza/` with date 2026-09-13. Do not change its text, date, URL, or
  metadata as part of unrelated work.
- Do not modify maks.live or its repository; use a separate new repository for brodov.net.

- Route maps and homepage thumbnails must follow the approved route-map rules
  in `docs/PROJECT-CONTEXT.md` (section «Карты маршрутов — утверждённые правила»).
  Keep full-map and thumbnail styling separate: route strokes are 1.8 pt and
  2.5 pt respectively; previews are chosen independently of article photos.
