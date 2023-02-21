.. _installation_instructions:


Installation Instructions
================================================

.. _pre-requisites:

Pre-requisites
--------------

    If you intend to perform any kind of experiment automation, please read this section carefully. However, to load and visualize data, or to run a virtual experiment, the following is not needed.

Hardware
^^^^^^^^

    In order to enjoy lightlab's experiment control capabilities, we assume that you have VISA compatible hardware: at least one computer with a GPIB card or USB-GPIB converter; one instrument; and your favorite VISA driver installed. Just kidding, there is a one-company monopoly on that (see :ref:`below <pyvisa-reference>`).

.. _pyvisa-reference:

pyvisa
^^^^^^

    We rely heavily on pyvisa_ for instrument control. It provides a wrapper layer for a VISA backend that you have to install in your computer prior to using lightlab. This is typically going to be a *National Instruments* backend, but the pyvisa team is working on a new pure-python backend (pyvisa-py_). Refer to pyvisa_installation_ for installation instructions. If you need to install in ubuntu, see :ref:`ubuntu_installation`.

.. warning::

    Currently we are also working with *python3*. This might present some minor inconvenience in installation, but it allows us to write code that will be supported in the long term. All dependencies are easily available in python3 and are automatically installed with pip.

Proceed with installing lightlab once you have something that looks like the following output::

    >>> import pyvisa
    >>> rm = pyvisa.ResourceManager()
    >>> print(rm.list_resources())
    ('GPIB0::20::INSTR', 'GPIB1::24::INSTR', 'ASRL1::INSTR', 'ASRL2::INSTR', 'ASRL3::INSTR', 'ASRL4::INSTR')

.. _pyvisa: https://github.com/pyvisa/pyvisa
.. _pyvisa_installation: http://pyvisa.readthedocs.io/en/stable/getting.html
.. _pyvisa-py: https://github.com/pyvisa/pyvisa-py

Installation in personal computer
---------------------------------

Regular users can install lightlab with pip::

    $ pip install lightlab

For more experienced users: install the lightlab package like any other python package, after having downloaded the project from github.::

    $ python3 install setup.py

If you are new to python programming, jupyter notebooks, you might want to sit down and patiently read the :ref:`getting-started` Pages.


.. contents:: More detailed installation instructions
    :depth: 4


.. include:: advanced_installation.rst
.. include:: sysadmin.rst
