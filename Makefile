SHELL := /bin/bash

# different tests
TESTARGS = -s --cov=lightlab --cov-config .coveragerc
TESTARGSNB = --nbval-lax --sanitize-with ipynb_pytest_santize.cfg
# DOCDEFAULT can be html or latexpdf
DOCDEFAULT       = html

# Server ports (excluding Jupyter)
DOCHOSTPORT = 8049

venv: venv/bin/activate
venv/bin/activate:
	test -d venv || virtualenv -p python3 --prompt "(lightlab-venv) " --distribute venv
	touch venv/bin/activate

devbuild: venv setup.py dev-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r dev-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	# ./cleannbline -v -r 5 lightlab

testbuild: venv setup.py test-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r test-requirements.txt | grep -v 'Requirement already satisfied'; \
		pip install -e . | grep -v 'Requirement already satisfied'; \
	)
	# ./cleannbline -v -r 5 lightlab

test: testbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) tests; \
	)

test-lint: testbuild
	( \
		source venv/bin/activate; \
		# py.test --pylint -m pylint --pylint-error-types=EF lightlab; \
	)

test-nb: devbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) notebooks/Tests; \
	)

test-all: testbuild devbuild
	( \
		source venv/bin/activate; \
		py.test $(TESTARGS) $(TESTARGSNB) tests notebooks/Tests; \
	)

clean:
	rm -rf dist
	rm -rf lightlab.egg-info
	rm -rf build

purge: clean
	rm -rf venv

# Running Servers (incl. notebooks)
server-config: venv setup.py
	source venv/bin/activate; python setup.py server_permissions


jupyter: devbuild
	( \
		source venv/bin/activate; \
		jupyter notebook; \
	)

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

getjpass: venv
	venv/bin/python -c 'from notebook.auth import passwd; print(passwd())'

jupyter-password: venv
	( \
		source venv/bin/activate; \
		jupyter notebook password; \
	)

monitorhost:
	cd progress-monitor && python3 -m http.server $(shell cat .monitorhostport)

dochost: docs
	# source venv/bin/activate && \
	$(MAKE) -C docs $(DOCDEFAULT) && \
	cd docs/_build/$(DOCDEFAULT) && \
	python3 -m http.server $(DOCHOSTPORT)

.PHONY: test test-nb test-all clean purge dochost monitorhost
