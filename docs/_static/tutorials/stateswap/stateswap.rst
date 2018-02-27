State swapping
==============

Suppose you read the part about consistency in drivers, you understand how code can represent a state of physical reality that is accurate to a certain extent. It is common to be interested in multiple states of instrumentation, devices under test, and even physical vs. modeled reality. Swapping seemlessly between them is necessary for making robust virtualization code, but it presents dangers. All of this consistency can be brought down by an error thrown during the swap.

State swappers protect from those errors, bringing you back to a known state if anything goes wrong.

.. toctree::
    :maxdepth: 2
    :caption: Demo

    /ipynbs/StateSwappingDemo.ipynb

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
