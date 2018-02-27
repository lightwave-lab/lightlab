N-dimensional sweeps with ``NdSweeper``
---------------------------------------
Concept
*******
.. image:: characterize-2d.pdf
    :alt: Two dimensional sweeps
    :align: center

Sweeps can occur in several dimensions of actuation and/or measurement. Suppose we want to see how some measured (dependent) variables depends on two actuated (independent) variables

.. code-block:: python
    :emphasize-lines: 5,6
    :linenos:

    aAct = np.linspace(0, 1, 10)
    bAct = np.linspace(10, 20, 3)
    measMat = np.zeros((len(aAct), len(bAct)))
    for ia, a in enumerate(aAct):
        act_1(a)
        for ib, b in enumerate(bAct):
            act_2(b)
            measMat[ia, ib] = measure()
    plt.pcolormesh(aAct, bAct, measMat)

The for loops get nested with each sub-row calling its own actuate. Measurement always happens in the inner-loop. Alternatively, all actuation can happen on the inner loop by flipping lines 4 and 5. The order and precedence of actuation calls is critical.

In the package, all of this functionality and more is implemented in the ``NdSweeper``. One specifies the domain (``aAct``, ``bAct``) and the functions to call in each dimension (``act_1`` and ``act_2``). One also specifies the measurements that should be taken (``meas_1``, ``meas_2``). The sweep is executed with the ``gather()`` method.

Usage
*****
.. toctree::
    :caption: Demo

    /ipynbs/GenericNdSweep.ipynb

``NdSweeper`` also supports a :py:meth:`~lightlab.util.sweep.NdSweeper.subsume` method which combines a N-dimensional sweep with a M-dimensional sweep into a (N+M)-dimensional sweep.

Basic data structure concept
''''''''''''''''''''''''''''
NdSweeper has attributes containing function pointers. These tell it what to do when actuating, measuring, or parsing. The actuation values are specified at the time of the actuation function. *All of these things must have name/key* that is unique within the sweep. All of their value data is stored in a common data structure that has N array-like sweep dimension(s) and one dictionary-like dimension for different data memebers. When a sweep completes, the entire grid of values for a given data member can be accessed with ``swp.data[key]``, returning an ndarray. On the other hand, *all* of the data for a given sweep point can be accessed with ``swp.data[ndindex]``, returning a dict. (Don't worry about the implementation of that structure)

Specifying actuation
''''''''''''''''''''
Actuation values are determined when specified. Their dimensions determine the sweep and data dimension. The order that they are added affects the sweep priority, such that the first sweep addded will be swept at each point of the second added, etc. An actuation function has one argument which is provided by the actuation value at that index. If there is a return, that is treated as a separate measurement. Doing on every point is specifiable.

.. automethod:: lightlab.util.sweep.NdSweeper.addActuation
    :noindex:

Specifying measurement
''''''''''''''''''''''
Measurement values are filled in point-by-point for every sweep index. They depend only on external function results, not on stored data. Measurement functions are called with no arguments. Returning is mandatory. The order does not matter theoretically, but it is preserved (first added, first called).

Special case: if the actuation method has a return type that is *not* ``NoneType``, a measurement will automatically be created to capture these values. This measurement key will be the actuation key, plus ``'-return'``.

.. automethod:: lightlab.util.sweep.NdSweeper.addMeasurement
    :noindex:

Parsers: what and how
'''''''''''''''''''''
Parsers are functions of the sweep data (which may include the results of other parsers). They have one argument, a dictionary of data members *at a given sweep point*. The order they are added is important if the execution of one parser depends on the result of another. Parsers added after the sweep is gathered will be fully calculated automatically. During the sweep, parsers are calculated at every point. They typically do not interact with hardware nor do they depend on sweep index; however, they are allowed to interact with persistent external objects, such as a plotting axis.

.. automethod:: lightlab.util.sweep.NdSweeper.addParser
    :noindex:


Static data
'''''''''''
Parsing functions can depend on values that are not measured during the sweep. Give it a name key and it can be accessed by parsers just like a measurement. When adding static data, it will expand to fit the shape of the sweep, to some extent (see the docstring). That means you can add static data that is constant using a scalar and variable using an ndarray.

.. automethod:: lightlab.util.sweep.NdSweeper.addStaticData
    :noindex:


Tricks with array actuation
***************************
Some actuation procedure can not be separated into different functions, each with one argument. Some need multiple arguments, and you may be interested in sweeping both. The memory allocation is the same::

    aAct = np.linspace(0, 1, 10)
    bAct = np.linspace(10, 20, 3)
    measMat = np.zeros((len(aAct), len(bAct)))

But the ``for`` loop is fundamentally different

.. code-block:: python
    :emphasize-lines: 3

    for ia, a in enumerate(aAct):
        for ib, b in enumerate(bAct):
            act(a, b)
            measMat[ia, ib] = measure()

What this means is that we need to restructure how the sweep is specified, and the functions the user gives it.

.. todo:: Array actuation is not currently supported by NdSweeper, but should be. Fundamentally, CommandControlSweeper is of the array actuation type, and that is implemented. Perhaps this calls for a new subclass of ``Sweeper``


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
