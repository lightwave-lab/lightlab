# Sphinx documentation variables
CODEDIR       = lightlab
# DOCDEFAULT can be html or latexpdf
DOCDEFAULT       = html
SPHINXOPTS    = -j4

# Server ports (excluding Jupyter)
DOCHOSTPORT = 8049

venv: venv/bin/activate
venv/bin/activate:
	test -d venv || virtualenv -p python3 --prompt "(lightlab-venv) " --distribute venv
	touch venv/bin/activate

dev-requirements: venv dev-requirements.txt
	( \
		source venv/bin/activate; \
		pip install -r dev-requirements.txt; \
	)

devbuild: venv setup.py dev-requirements
	source venv/bin/activate; python setup.py develop
	./cleannbline -v -r 5 notebooks lightlab docs

test: devbuild
	( \
		source venv/bin/activate; \
		py.test -s tests; \
	)

test-lint: devbuild
	( \
		source venv/bin/activate; \
		py.test --pylint -m pylint --pylint-error-types=EF lightlab; \
	)

test-nb: devbuild
	( \
		source venv/bin/activate; \
		py.test -s notebooks/Tests --nbval --sanitize-with ipynb_pytest_santize.cfg; \
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
	cd monitoring && python3 -m http.server $(shell cat .monitorhostport)

dochost: docs
	source venv/bin/activate && \
	$(MAKE) -C docs $(DOCDEFAULT) && \
	cd docs/_build/$(DOCDEFAULT) && \
	python3 -m http.server $(DOCHOSTPORT)

.PHONY: devbuild test clean purge dochost monitorhost
