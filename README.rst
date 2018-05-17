Lightlab
========

A python library for remote laboratory control. Laboratory remoting facilitates experimental research:
* access from anywhere
* large dataset gathering, storage, and analysis
* repeatability
* real-time status and progress monitoring,
* intra- and inter-group collaboration

This package includes:
* A shared library of instrument drivers
* Representation of state for labs of multiple users
* Driver-independent abstractions of instruments
* Utilities for data structures, advanced sweeping, search procedures, spectrum analysis, and characterization
* Constructs of laboratory virtualization for repeatability and rapid user code development
* Detailed documentation of tips, tricks, and instructions for prepping your lab for remoting

Here is our `philosophy <http://lightlab.readthedocs.io/en/development/_static/gettingStarted/engineersGuide.html>`__ of how a modern lab can look.

Installation
------------

From PyPI:

::

    pip install lightlab

From source:

::

    git clone git@github.com:lightwave-lab/lightlab.git
    cd lightlab
    make venv

Getting started
---------------

1. Configure GPIB/ethernet communication on an `instrumentation server <http://lightlab.readthedocs.io/en/latest/_static/gettingStarted/sysadmin.html>`__
2. Initialize the representation of your `lab state <http://lightlab.readthedocs.io/en/latest/_static/developers/labState.html>`__
3. `Write a driver <http://lightlab.readthedocs.io/en/latest/_static/tutorials/drivers/drivers.html>`__ or use an existing one
4. Read about advanced features and `tutorials <http://lightlab.readthedocs.io/en/latest/_static/tutorials/index.html>`__
5. Get going!

Readthedocs: `lightlab.readthedocs.io <http://lightlab.readthedocs.io/en/latest/>`_

Github: https://github.com/lightwave-lab/lightlab

Supported platforms
-------------------

Server: Mac OS and Linux running ≥python3.6; not tested on Windows (to do).

Auxiliary hosts: Mac OS, Linux, Windows

