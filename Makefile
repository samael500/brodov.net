HUGO ?= hugo
.PHONY: dev build preview check sun-calendar
dev preview: SUN_CALENDAR_FLAGS = --noindex
dev: sun-calendar
	python3 tools/stories/content.py --preview
	$(HUGO) server --environment preview --buildDrafts --disableFastRender
build: sun-calendar
	python3 tools/stories/content.py
	$(HUGO) --environment production --cleanDestinationDir --minify
preview: sun-calendar
	python3 tools/stories/content.py --preview
	$(HUGO) --environment preview --buildDrafts --cleanDestinationDir --destination preview --baseURL http://localhost:8765/
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

.PHONY: stories-setup stories-test
stories-setup:
	python3 -m venv tools/.stories-venv
	tools/.stories-venv/bin/pip install -r tools/requirements-stories.txt
stories-test:
	tools/.stories-venv/bin/python -m unittest discover -s tests -p 'test_stories*.py'

sun-calendar:
	python3 vendor/sun-calendar/generate.py --output-dir static/sun-calendar $(SUN_CALENDAR_FLAGS)
