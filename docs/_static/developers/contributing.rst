Contributing to ``lightlab``
============================
We follow this `Git branching workflow <http://nvie.com/posts/a-successful-git-branching-model/>`_. Feature branches should base off of development; when they are done, they must pass tests and test-nb's; finally they are merged to development.

Testing ``lightlab``
--------------------
First off, your change should not break existing code. You can run automated tests like this::

    make test-unit
    make test-nb

The test-nb target runs the **notebooks** in notebooks/Tests. This is a cool feature because it allows you to go in with jupyter and see what's happening if it fails. We recommend using the `nbval <https://github.com/computationalmodelling/nbval>`_ approach. It checks for no-exceptions, not accuracy of results. If you want to check for accuracy of results, do something like::

    x = 1 + 1
    assert x == 2

in the cell.

**Make tests for your features!** It helps a lot. Again, **Never put hardware accessing methods in a unittest**.

To run just one test, use a command like::

    $ source venv/bin/activate
    $ py.test --nbval-lax notebooks/Tests/TestBook.ipynb

Documenting
-----------
Documenting as you go is helpful for other developers and code reviewers.  So useful that we made a whole :doc:`tutorial <docYourCode>` on it. We use auto-API so that docstrings in code make it into the official documentation.

For non-hardware features, a good strategy is to use tests that are both functional and documentation by example. In cases where visualization is helpful, use notebook-based, which can be linked from this documentation or in-library docstrings :ref:`like this </ipynbs/Tests/TestPeakAssistant.ipynb>`. Otherwise, you can make `pytest <https://docs.pytest.org/en/latest/>`_ unittests in the tests directory, which can be linked like this: :py:mod:`~tests.test_virtualization`.

For new hardware drivers, as a general rule, document its basic behavior in ``lightlab/notebooks/BasicHardwareTests``. Make sure to save with outputs. Finally, link it in the docstring like this::

    class Tektronix_DPO4034_Oscope(VISAInstrumentDriver, TekScopeAbstract):
    ''' Slow DPO scope. See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope
    ...

Linting
-------
As of now, we don't require strict `PEP-8 <https://www.python.org/dev/peps/pep-0008/>`_ compliance, but we might in the future. However, we try to follow as many of their guidelines as possible:

.. figure:: images/sublimelinter_example_bad.png
    :alt: bad pep8 example

    Example of valid python code that violates some of the PEP8 guidelines.

.. figure:: images/sublimelinter_example_good.png
    :alt: good pep8 example

    Fixing the PEP8 violations of the previous figure.

Sometimes the linter is wrong. You can tell it to ignore lines by adding comment flags like the following example:

.. code:: python

    x = [x for x in sketchy_iterable]  # pylint: disable=not-an-iterable
    from badPractice import *  # noqa

``# noqa`` is going to ignore pyflakes linting, whereas ``# pylint`` configures `pylint` behavior.

If you use Sublime editor
-------------------------
Everyone has their favorite editor. We like `Sublime Text <https://www.sublimetext.com>`_. If you use Sublime, `here <https://github.com/SublimeLinter/SublimeLinter-flake8>`_ is a good linter. It visually shows what is going on while you code, saving lots of headaches

Sublime also helps you organize your files, autocomplete, and manage whitespace. This is :doc:`sublime-lightlab`. Put it in the ``lightlab/`` directory and call it something like ``sublime-lightlab.sublime-project``.

By the way, you can make a command-line Sublime by doing this in Terminal (for MacOS)::

    ln -s "/Applications/Sublime Text.app/Contents/SharedSupport/bin/subl" /usr/local/bin/subl

Adding a new package
--------------------
Two ways to do this. The preferred method is to add it to the package requirements in ``setup.py``. The other way is in the venv. In that case, make sure you freeze the new package to the requirements file::

    $ source venv/bin/activate
    $ pip install <package>
    $ make pip-freeze
    $ git commit -m "added package <package> to venv"

.. warning::

    If your code imports an external package, the sphinx documentation will try to load it and fail. The solution is to mock it. Lets say your source file wants to import::

        import scipy.optimize as opt

    For this to pass and build the docs, you have to go into the ``docs/sphinx/conf.py`` file. Then add that package to the list of mocks like so::

        MOCK_MODULES = [<other stuff>, 'scipy.optimize']
