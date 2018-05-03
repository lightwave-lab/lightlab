Welcome to Lightlab's documentation!
================================================

    This package offers the ability to control multi-instrument experiments, and to collect and store data and methods very efficiently. It was developed by researchers in an integrated photonics lab (hence lightlab) with equipment mostly controlled by the GPIB protocol. It can be used as a combination of these three tasks:

    #. Multi-instrument experiment remote control and command.
    #. Structuring the entire experimental procedure and data in python code.
    #. Creating virtual experiments that can be validated in a real lab.

    We wrote this documentation with love to all young experimental researchers that are not necessarily familiar with all the software tools introduced here. We attempted to include how-tos at every step to make sure everyone can get through the initial steps.

.. todo::

    Include a simple but powerful jupyter screenshot showing a plot from an experiment run.

.. warning::

    This is not a pure software package. Lightlab needs to be run in a particular configuration. Before you continue, carefully read the :ref:`pre-requisites` and the :ref:`getting-started` sections. It contains necessary information about setup steps you need to take care before starting.


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   _static/installation/index
   _static/gettingStarted/index
   _static/developers/index
   _static/tutorials/index
   _static/misc/index

API
---

.. toctree::
   :maxdepth: 1

   API of the lightlab package <API/lightlab>
   Unit tests <TestAPI/tests>

.. note::

    This documentation contains ipython notebooks. It is possible to open them with a jupyter kernel and run them interactively to play with knobs and see more plotting features.


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
