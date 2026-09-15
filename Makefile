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
