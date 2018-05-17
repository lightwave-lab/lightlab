Lightlab
========

A python library for remote laboratory control. Laboratory remoting greatly facilitates experimental
research through access from anywhere, large dataset gathering, storage, and analysis,
repeatability, live status and progress monitoring, intra- and inter-group collaboration.

Philosophy of a modern lab: https://www.readthedocs.io (not yet)

Includes: - A shared library of instrument drivers - Representation of state for labs of multiple
users - Driver-independent abstractions of instruments - Utilities for data structures, advanced
sweeping, search procedures, spectrum analysis, and characterization - Constructs of laboratory
virtualization for repeatability and rapid user code development - Detailed documentation of tips,
tricks, and instructions for prepping your lab for remoting

Installation
------------

From PyPI:

::

    pip install lightlab

or from source on github: (not yet)

::

    git clone <project url>

Getting started
---------------

1. Configure GPIB/ethernet communication on an instrumentation server
2. Initialize the representation of your lab's state
3. Write a driver or use an existing one
4. Read the documentation
5. Get going!

Documentation
-------------

Contains full instructions for getting started and setting up your lab and workflow.

Hosted on readthedocs here (not yet)

Contributing
------------

We welcome contributions, especially for new drivers. Fork the repo to your github user account and
clone from there. Please unittest your contributions in a repeatable virtual laboratory; test the
driver in experiment, not unittests; then create a pull request.

Supported platforms
-------------------

Server: Mac OS and Linux running ≥python3.6; not tested on Windows (to do).

Auxiliary hosts: Mac OS, Linux, Windows

