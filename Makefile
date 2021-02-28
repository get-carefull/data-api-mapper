SHELL=/bin/bash

lint:
	./setup.py flake8
	flake8 scripts/*

test: lint
	python ./test/test.py -v

install:
	-rm -rf dist
	python setup.py bdist_wheel
	pip install --upgrade dist/*.whl

release-major:
	$(eval export TAG=$(shell git describe --tags --match 'v*.*.*' | perl -ne '/^v(\d+)\.(\d+)\.(\d+)/; print "v@{[$$1+1]}.0.0"'))
	$(MAKE) release

release-minor:
	$(eval export TAG=$(shell git describe --tags --match 'v*.*.*' | perl -ne '/^v(\d+)\.(\d+)\.(\d+)/; print "v$$1.@{[$$2+1]}.0"'))
	$(MAKE) release

release-patch:
	$(eval export TAG=$(shell git describe --tags --match 'v*.*.*' | perl -ne '/^v(\d+)\.(\d+)\.(\d+)/; print "v$$1.$$2.@{[$$3+1]}"'))
	$(MAKE) release

release:
	@if ! git diff --cached --exit-code; then echo "Commit staged files before proceeding"; exit 1; fi
	@if [[ -z $$TAG ]]; then echo "Use release-{major,minor,patch}"; exit 1; fi
	@if ! type -P pandoc; then echo "Please install pandoc"; exit 1; fi
	@if ! type -P sponge; then echo "Please install moreutils"; exit 1; fi
	@if ! type -P http; then echo "Please install httpie"; exit 1; fi
	@if ! type -P twine; then echo "Please install twine"; exit 1; fi
	$(eval REMOTE=$(shell git remote get-url origin | perl -ne '/([^\/\:]+\/.+?)(\.git)?$$/; print $$1'))
	$(eval GIT_USER=$(shell git config --get user.email))
	$(eval GH_AUTH=$(shell if grep -q '@github.com' ~/.git-credentials; then echo $$(grep '@github.com' ~/.git-credentials | python3 -c 'import sys, urllib.parse as p; print(p.urlparse(sys.stdin.read()).netloc.split("@")[0])'); else echo $(GIT_USER); fi))
	$(eval RELEASES_API=https://api.github.com/repos/${REMOTE}/releases)
	$(eval UPLOADS_API=https://uploads.github.com/repos/${REMOTE}/releases)
	git pull
	git clean -x --force $$(python setup.py --name)
	sed -i -e "s/version=\([\'\"]\)[0-9]*\.[0-9]*\.[0-9]*/version=\1$${TAG:1}/" setup.py
	git add setup.py
	TAG_MSG=$$(mktemp); \
	    echo "# Changes for ${TAG} ($$(date +%Y-%m-%d))" > $$TAG_MSG; \
	    git log --pretty=format:%s $$(git describe --abbrev=0)..HEAD >> $$TAG_MSG; \
	    $${EDITOR:-nano} $$TAG_MSG; \
	    if [[ -f Changes.md ]]; then cat $$TAG_MSG <(echo) Changes.md | sponge Changes.md; git add Changes.md; fi; \
	    if [[ -f Changes.rst ]]; then cat <(pandoc --from markdown --to rst $$TAG_MSG) <(echo) Changes.rst | sponge Changes.rst; git add Changes.rst; fi; \
	    git commit -m ${TAG}; \
	    git tag --sign --annotate --file $$TAG_MSG ${TAG}
	git push --follow-tags
	$(MAKE) install
	$(MAKE) release-pypi

release-pypi:
	python setup.py sdist bdist_wheel
	twine upload dist/*.tar.gz dist/*.whl --sign --verbose


.PHONY: release
