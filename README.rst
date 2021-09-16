Lightlab
========

.. image:: https://travis-ci.org/lightwave-lab/lightlab.svg?branch=development
    :target: https://travis-ci.org/lightwave-lab/lightlab

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

From source (developer mode):

::

    git clone https://github.com/lightwave-lab/lightlab.git
    cd lightlab
    pip install -e .  # install in editable mode.

Getting started
---------------

1. Configure GPIB/ethernet communication on a `personal computer or instrumentation server <https://lightlab.readthedocs.io/en/latest/_static/installation/index.html>`__
2. Initialize the representation of your `lab state <http://lightlab.readthedocs.io/en/latest/_static/developers/labState.html>`__
3. `Write a driver <http://lightlab.readthedocs.io/en/latest/_static/tutorials/drivers/drivers.html>`__ or use an existing one
4. Read about advanced features and `tutorials <http://lightlab.readthedocs.io/en/latest/_static/tutorials/index.html>`__
5. Get going! Need more help? Have suggestions? File an `issue <https://github.com/lightwave-lab/lightlab/issues>`__

Readthedocs: `lightlab.readthedocs.io <http://lightlab.readthedocs.io/en/latest/>`_

Github: https://github.com/lightwave-lab/lightlab

Supported platforms
-------------------

Server: Mac OS and Linux running ≥python3.6; not tested on Windows (to do).

Auxiliary hosts: Mac OS, Linux, Windows

Acknowledgements
----------------

This  material  is  based  in part upon  work  supported  by  the  National Science Foundation under Grant Number E2CDA-1740262. Any  opinions,  findings,  and  conclusions  or  recommendations expressed  in  this  material  are  those  of  the  author(s)  and  do  not necessarily reflect the views of the National Science Foundation.
