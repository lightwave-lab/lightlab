SHELL := /usr/bin/env bash

# different tests
TESTARGS = --capture=sys --cov=lightlab --cov-config .coveragerc
TESTARGSNB = --nbval-lax

# For devbuild, testbuild
REINSTALL_DEPS = $(shell find lightlab -type f) venv setup.py

# DOCTYPE_DEFAULT can be html or latexpdf
DOCTYPE_DEFAULT = html

# Server ports for CI hosting. You can override by setting an environment variable DOCHOSTPORT
DOCHOSTPORT ?= 8049

default: help ;

venv: venv/bin/activate
venv/bin/activate:
	test -d venv || virtualenv -p python3 --prompt "(lightlab-venv) " --distribute venv
	touch venv/bin/activate

devbuild: venvinfo/devreqs~
venvinfo/devreqs~: $(REINSTALL_DEPS) dev-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r dev-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	@mkdir -p venvinfo
	touch venvinfo/devreqs~

testbuild: venvinfo/testreqs~
venvinfo/testreqs~: $(REINSTALL_DEPS) test-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r test-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	@mkdir -p venvinfo
	touch venvinfo/testreqs~

test-unit: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) tests; \
	)

test-simple: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) tests; \
	)

test-lint: testbuild
	( \
		source venv/bin/activate; \
		py.test --pylint --flake8 --pylint-rcfile=pylintrc lightlab; \
	)

test-lint-errors: testbuild
	( \
		source venv/bin/activate; \
		py.test --pylint --flake8 --pylint-rcfile=pylintrc-errors lightlab; \
	)

test-nb: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) notebooks/Tests; \
		rsync -rau notebooks/Tests/*.ipynb docs/ipynbs/Tests
	)

test-unit-all: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) tests notebooks/Tests; \
	)

test: testbuild test-unit-all test-lint ;


clean:
	rm -rf dist
	rm -rf lightlab.egg-info
	rm -rf build
	rm -rf venvinfo
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .coverage
	$(MAKE) -C docs clean

purge: clean
	rm -rf venv

pip-freeze: devbuild
	( \
		source venv/bin/activate; \
		pipdeptree -lf | grep -E '^\w+' | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U; \
		pipdeptree -lf | grep -E '^\w+' | grep -v '^\-e' | grep -v '^#' > dev-requirements.txt; \
	)

pip-update: pip-freeze
	( \
		source venv/bin/activate; \
		pip freeze --local | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U; \
	)

# Running Servers (incl. notebooks)
server-config: venv setup.py
	source venv/bin/activate; python setup.py server_permissions

jupyter: devbuild
	( \
		source venv/bin/activate; \
		cd notebooks; \
		jupyter notebook; \
	)

getjpass: venv
	venv/bin/python -c 'from notebook.auth import passwd; print(passwd())'

jupyter-password: venv
	( \
		source venv/bin/activate; \
		jupyter notebook password; \
	)

monitorhost:
	@mkdir -p progress-monitor
	cd progress-monitor && python3 -m http.server $(shell cat .monitorhostport)


docbuild: venvinfo/docreqs~
venvinfo/docreqs~: $(REINSTALL_DEPS) notebooks/Tests doc-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r doc-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	@mkdir -p venvinfo
	@touch venvinfo/docreqs~

docs: docbuild
	source venv/bin/activate; $(MAKE) -C docs $(DOCTYPE_DEFAULT)

docs-ci: docbuild
	( \
		source venv/bin/activate; \
		$(MAKE) -C docs html; \
	)


dochost: docs
	( \
		source venv/bin/activate; \
		cd docs/_build/$(DOCTYPE_DEFAULT); \
		python3 -m http.server $(DOCHOSTPORT); \
	)

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "--- environment ---"
	@echo "  venv              creates a python virtualenv in venv/"
	@echo "  pip-freeze        drops all leaf pip packages into dev-requirements.txt (Use with caution)"
	@echo "  pip-update        updates all pip packages in virtual environment"
	@echo "  clean             clean all build files"
	@echo "  purge             clean and delete virtual environment"
	@echo "--- development ---"
	@echo "  devbuild          install dev dependencies, build lightlab, and install inside venv"
	@echo "--- testing ---"
	@echo "  testbuild         install test dependencies, build lightlab, and install inside venv"
	@echo "  test-unit         perform basic unit tests"
	@echo "  test-nb           perform unit tests defined with ipynbs"
	@echo "  test-unit-all     perform basic unit tests + ipynbs"
	@echo "  test-lint         perform linting tests (warnings and errors), recommended"
	@echo "  test-lint-errors  perform linting tests (just errors)"
	@echo "  test              perform all unit tests and linting tests"
	@echo "--- documentation ---"
	@echo "  docbuild          prepare venv for documentation build"
	@echo "  docs              build documentation"
	@echo "  dochost           build documentation and start local http server"
	@echo "--- jupyter server ---"
	@echo "  server-config     prepare a server for persistent lightlab usage (see setup.py)"
	@echo "  jupyter           start a jupyter notebook for development"
	@echo "  getjpass          generate a jupyter compatible password hash"
	@echo "  jupyter-password  change your jupyter notebook user password"
	@echo "--- monitor server ---"
	@echo "  monitorhost       undocumented"


.PHONY: help default test docs test-nb test-unit test-unit-all test-lint test-lint-errors clean purge dochost monitorhost pip-freeze pip-update jupyter-password getjpass
