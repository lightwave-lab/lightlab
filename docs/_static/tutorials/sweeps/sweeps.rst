Doing sweeps
============

.. contents:: In this section
    :local:

.. note:: this section is probably more appropriately named actuate/measure setups. This includes sweeps but it also includes command-control (more than just sweeps), as well as peak search and binary search.

.. todo:: relabel accordingly

Sweeps are incredibly common in experiments because they are about repeated measurements of one thing as it changes in relation to other things.

Sweeps are like loops, but with some special properties. That's why the package provides a generalized sweeper class for taking care of a lot of the common issues.

.. image:: characterize-1d.pdf
    :alt: A sweep
    :align: center


Basic concepts
--------------

A typical sweep might look like this::

    actVals = np.linspace(0, 1, 10)
    measVals = np.zeros(len(actVals))
    for i, vA in enumerate(actVals):
        actuate(vA)
        measVals[i] = measure()
    plt.plot(actVals, measVals)

There are a few things going on here. Every time a measurement is taken, it is paired with an actuation. In other words, something in the lab changes that you control, and then you look at what happened.

    #. An actuation `procedure`: ``actuate``
    #. A measurement `function`: ``measure``
    #. A series of actuation arguments: ``actVals``
    #. Corresponding measurement results: ``measVals`` (pre-allocated)
    #. Post processing, in this case, plotting

The role of the ``for`` loop is to get one argument and pass it to the actuation procedure, then take one measurement and store it in the pre-allocated array.

A major problem here is that the important information is distributed all throughout the for loop structure. We would like to specify those things upfront. The :py:func:`~lightlab.util.sweep.simpleSweep` function does this in a bare bones version.

.. toctree::

    /ipynbs/Tests/SimpleSweep.ipynb


**Challenges of more advanced sweeps**

* The code gets difficult to read
* Often they are repeated with only small changes *somewhere* in the loop
* They can take a long time
* Processing and analysis occur only after they complete

The information can be distributed all throughout the code. This is especially the case when there are multiple dimensions, intermediate monitoring (e.g. plotting) and analysis (e.g. peak picking), and various data formats. What if we want to make a small change? The location in code is not obvious.

Since they take a long time, we want to get intermediate information out to the user via progress printing and reporting, maybe even visualization. Progress reporting can tell you when the sweep is likely to finish, so you can decide whether there's enough time to get a coffee or to get some sleep.

Intermediate analysis can also show you how it's going to decide whether to continue or stop. The relevant information could require lots of processing, such as if you want to know how a peak is moving. We want to put arbitrarily advanced analysis within the loop, and connect it to intermediate plotting.

The worst is when you finish a sweep and the bulk processing at the end throws an exception. You have to repeat the sweep. Or if you are returning to an old notebook to fix up a figure for a paper. You have to repeat the sweep. We want convenient ways to save the data an reload it as if the sweep had just occured fresh.

:py:class:`~lightlab.util.sweep.Sweeper` is a way to re-organize the for-actuate-measure setup. All of the important information can be specified at the beginning. All of the bells and whistles like monitoring and plotting happen under the hood. It has two important subclasses, :py:class:`~lightlab.util.sweep.NdSweeper` and :py:class:`~lightlab.util.sweep.CommandControlSweeper`.

.. toctree::
    :maxdepth: 2

    ndSweeper
    cmdCtrlSweeper
    sweeperOptions


Other actuate-measure situations
--------------------------------
Peak search and binary search can be done interactively with a peaked or monotonic (respectively) system. Those examples are found in here

.. toctree::
    :maxdepth: 2

    /ipynbs/Tests/TestPeakAndBinarySearch.ipynb

.. todo:: Currently peak search is like a n-point 1-D Nelder Meade search. That could be extended to multiple dimensional optimization.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
