The ``Sweeper`` class: features and options
-------------------------------------------

Progress monitoring
***************************
Use :py:meth:`~lightlab.util.sweep.Sweeper.setMonitorOptions` to set and get. To see how the sweep is coming along, you can choose to print to stdout or to serve a page available anywhere online. If plotting is also set up, you can live plot every point in your notebook as it is being taken. Here are the options

:stdoutPrint: Print the sweep index to stdout to see progress
:cmdCtrlPrint: (only with CommandControlSweeper) Print the sweep index, command value, and measured value to see the errors
:livePlot: Refresh plots every data point when in an IPython notebook. Options specified in ``setPlotOptions`` will be used.
:plotEvery: Number of points to wait before refreshing live plot
:runServer: Print the sweep index to a file that is served online

.. note:: If your actuate-measure routine is fast, then live plotting can slow down the sweep with the need to refresh graphics. Set ``plotEvery`` to an integer more than 1 to do less plotting.

.. warning:: Live plotting is not yet supported for surf plots, and there are a few bugs with 1D command-control plots.

If ``runServer==True``, to serve the page, you must first start the server (see :doc:`here </_static/developers/developer>`), making sure to set up the right domain, domainHostName, monitorServerDir, and monitorServerPort. If you are using ``Sweeper``, it configures your sweep to write to the server.

.. note::

    To instead do it manually, you would make a :py:class:`~lightlab.util.io.ProgressWriter`::

        prog = io.ProgressWriter(swpName, swpShape, runServer=True)

    and then call ``prog.update()`` every inner-loop iteration.


Plotting
***************************
.. todo::

    Another bug when using xKey equal to the major sweep axis. It sometimes only displays movement along x=constant lines.

Use :py:meth:`~lightlab.util.sweep.Sweeper.setPlotOptions` to set and get. Different plots are available for different kinds of sweeps. Some of the options are only valid with a given type. For most purposes, the best options are detected automatically, so you don't have to set them. Here are the options.

**NdSweeper**

:plType (str):
            - ``'curves'`` (1D or 2D)
                Standard line plots. If 2D, a set of lines with a legend will be produced.
            - ``'surf'`` (2D only)
                Standard surface color plot
:xKey (str, tuple): Abscissa variable(s)
:yKey (str, tuple): Ordinate variable(s)
:cmap-surf: colormap
:cmap-curves: colormap

A grid of axes will be produced that depends on the length of the tuples xKey and yKey. If both xKey and yKey are strings, only one plot axis is made. By default, the x (y) keys are filled with the actuation (measurement) variables that are detected to be scalar.


**CommandControlSweeper**

:plType (str):
            - ``'curves'`` (1D only)
                A line plot :cite:`Tait:15cont` showing mean and variances of measured vs. command
            - ``'cmdErr'`` (1D or 2D)
                A special grid plot :cite:`Tait:16multi` showing mean quivers and variance ellipses

Saving and loading
******************
``Sweeper`` provides two sets of save/load. The file is determined by the ``io.fileDir`` variable and the object's ``savefile`` attribute. These can be combined with a gathering boolean to determine whether you want to retake the sweep or load it from a saved version.

``save`` and ``load`` do just the ``data`` attribute.

.. code-block:: python

    swp = NdSweeper(...)
    ...
    swp.savefile = 'dummy'
    if isGathering:
        swp.gather()
        swp.save()
    else:
        swp.load()

Saving the entire object is good if the domains change, which is particularly important for command-control types. The problem is that references to bound functions cannot be pickled. The ``saveObj`` and ``cls.loadObj`` methods try to do the entire object, while leaving out the actuation and measurement function references.

.. code-block:: python

    myfile = 'dummy'
    if isGathering:
        swp = CommandControlSweeper(...)
        ...
        swp.gather()
        swp.saveObj(myfile)
    else:
        swp = sUtil.CommandControlSweeper.loadObj(myfile)

.. todo:: NdSweeper has no loadObj yet. This seems reasonable to do by stripping the bound references. Consider deprecating saving/loading just data and the savefile attribute.

.. bibliography:: /lightwave-bibliography.bib

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
