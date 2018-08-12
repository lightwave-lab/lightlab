How to set up this sweet documentation workflow
===============================================

Purely for informing other projects in the future. Users and developers on this project do not have to do any of this. It is setup for you.

#. Install what you need into your virtual environment::

    $ pip install Sphinx
    $ pip install sphinx_rtd_template
    $ pip install sphinxcontrib-napoleon
    $ pip freeze > requirements.txt

#. Set up the sphinx project::

    $ sphinx-quickstart

#. Advanced configure within the ``conf.py`` file

    * Specify extensions. I use these::

        extensions = ['sphinx.ext.autodoc',
            'sphinx.ext.napoleon',
            'sphinx.ext.todo',
            'sphinx.ext.mathjax',
            'sphinx.ext.ifconfig',
            'sphinx.ext.viewcode']

    * Configuration of Napoleon::

        napoleon_google_docstring = True
        napoleon_use_param = True

    * Configuration of Autodocumentation::

        autodoc_member_order = 'bysource'
        autoclass_content = 'both'

    * Template configuration for readthedocs style::

        import sphinx_rtd_theme
        html_theme = 'sphinx_rtd_theme'
        html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

    * Mock up for external modules imported in your code::

        import sys
        from unittest.mock import MagicMock

        class Mock(MagicMock):
            @classmethod
            def __getattr__(cls, name):
                    return MagicMock()

        MOCK_MODULES = ['numpy',
            'matplotlib',
            'matplotlib.pyplot',
            'matplotlib.figure',
            'scipy',
            'scipy.optimize']
        sys.modules.update((mod_name, Mock()) for mod_name in MOCK_MODULES)

#. Further documentation here

    * `Sphinx overview <http://www.sphinx-doc.org/en/stable/tutorial.html>`_
    * `ReST primer <http://www.sphinx-doc.org/en/stable/rest.html>`_
    * `Napoleon <https://sphinxcontrib-napoleon.readthedocs.io/en/latest/>`_


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
