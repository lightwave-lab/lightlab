SHELL := /bin/bash

# different tests
TESTARGS = -s --cov=lightlab --cov-config .coveragerc
TESTARGSNB = --nbval-lax --sanitize-with ipynb_pytest_santize.cfg

# For devbuild, testbuild
REINSTALL_DEPS = $(shell find lightlab -type f) venv setup.py

# DOCTYPE_DEFAULT can be html or latexpdf
DOCTYPE_DEFAULT = html

DOCHOSTPORT_FILE = .dochostport
# Server ports for CI hosting. You can override by making a file .dochostport
DOCHOSTPORT_DEFAULT = 8049

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

test: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) tests; \
	)

test-lint: testbuild
	( \
		source venv/bin/activate; \
		py.test --pylint -m pylint --pylint-error-types=EF lightlab; \
	)

test-nb: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) notebooks/Tests; \
	)

test-all: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) tests notebooks/Tests; \
	)

clean:
	rm -rf dist
	rm -rf lightlab.egg-info
	rm -rf build
	rm -rf venvinfo

purge: clean
	rm -rf venv

pip-freeze: venv
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
venvinfo/docreqs~: $(REINSTALL_DEPS) doc-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r doc-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	@mkdir -p venvinfo
	@touch venvinfo/docreqs~

docs: docbuild
	source venv/bin/activate; $(MAKE) -C docs $(DOCTYPE_DEFAULT)

dochostfileexist:
	test -f $(DOCHOSTPORT_FILE) || echo $(DOCHOSTPORT_DEFAULT) > $(DOCHOSTPORT_FILE)

dochost: docs dochostfileexist
	( \
		source venv/bin/activate; \
		cd docs/_build/$(DOCTYPE_DEFAULT); \
		python3 -m http.server $(shell cat $(DOCHOSTPORT_FILE)); \
	)

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "--- environment ---"
	@echo "  venv              document it"
	@echo "  pip-freeze        document it"
	@echo "  pip-update        document it"
	@echo "  clean             document it"
	@echo "  purge             document it"
	@echo "--- development ---"
	@echo "  devbuild          document it"
	@echo "--- testing ---"
	@echo "  testbuild         document it"
	@echo "  test              document it"
	@echo "  test-lint         document it"
	@echo "  test-nb           document it"
	@echo "  test-all          document it"
	@echo "--- documentation ---"
	@echo "  docbuild          document it"
	@echo "  docs              document it"
	@echo "  dochost           document it"
	@echo "--- jupyter server ---"
	@echo "  server-config     document it"
	@echo "  jupyter           document it"
	@echo "  getjpass          document it"
	@echo "  jupyter-password  document it"
	@echo "--- monitor server ---"
	@echo "  monitorhost       document it"


.PHONY: help test docs test-nb test-all clean purge dochost monitorhost
