HUGO ?= hugo
.PHONY: dev build preview check
dev:
	$(HUGO) server --environment preview --buildDrafts --disableFastRender
build:
	$(HUGO) --environment production --cleanDestinationDir --minify
preview:
	$(HUGO) --environment preview --buildDrafts --destination preview --baseURL http://localhost:8765/
check: build
	python3 scripts/check.py public

ROUTE ?= russian-trail
ROUTE_PYTHON ?= tools/route-generator/.venv/bin/python
.PHONY: route-setup route
route-setup:
	python3 -m venv tools/route-generator/.venv
	$(ROUTE_PYTHON) -m pip install -r tools/route-generator/requirements.txt
route:
	$(ROUTE_PYTHON) tools/route-generator/render.py "route-sources/$(ROUTE)/route.json"
