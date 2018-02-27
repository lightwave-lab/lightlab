Command-control sweeps
----------------------

**Note for documenter**
    The basics of this section should go on a different page about command-control without sweeping. Then on this page, it can focus just on the challenge of sweeping them

Concept
*******

These are special in that the actuation function attempts to invert the behavior of the physical system, such that the input is nominally seen as the measured output.

.. image:: cmdCtrl-1d.pdf
    :alt: Command and control operation
    :align: center

Since they are trying to reproduce a response equal to the input, the number of actuation and measurement dimensions are equal. So in 1D::

    ctrlVals = np.linspace(0, 1, 10)
    measVals = np.zeros(len(ctrlVals))
    for i, cVal in enumerate(ctrlVals):
        actVal = control(cVal)
        actuate(actVal)
        measVals[i] = measure()

Note that the ``actuate`` function is still there, but its argument comes from the ``control`` function. Ideally, ``ctrlVals`` will equal ``measVals``. Their difference gives us an idea of control error.


.. image:: cmdCtrl-2d.pdf
    :alt: Command and control in two dimensions
    :align: center

In 2D, the control function is rarely seperable, which means these sweeps fall into the array actuation type.

.. code-block:: python
    :emphasize-lines: 3,7

    aCtrl = np.linspace(0, 1, 10)
    bCtrl = np.linspace(10, 20, 3)
    ctrlMat = np.zeros((len(aAct), len(bAct), 2))
    measMat = np.zeros((len(aAct), len(bAct), 2))
    for ia, a in enumerate(aAct):
        for ib, b in enumerate(bAct):
            ctrlMat[ia, ib, :] = [a, b]
            actArr = control([a, b])
            actuate(actArr)
            measMat[ia, ib, :] = measure()

Notice that ``measMat`` is now 3 dimensional, with the third dimension corresponding do which variable. Highlighted lines show how to construct the expected ``ctrlMat``. It makes more sense to fill that control matrix before doing the actual sweep. This can instead be done with meshgrid commands::

    aGrid, bGrid = np.meshgrid(aCtrl, bCtrl)
    ctrlMat = np.array((aGrid, bGrid)).T # ctrlMat.shape == (10, 3, 2)

There is an advantage to doing this at first in that the sweep loop is simplified and more flexible.

.. code-block:: python

    for swpIndex in np.ndindex(ctrlMat.shape[:-1]):
        actArr = control(ctrlMat[swpIndex])
        actuate(actArr)
        measMat[swpIndex] = measure()

Voila! This structure is the same as the 1-dimensional command-control sweep: one line each for control, actuate, and measure. It takes advantage of NumPy's n-dimensional for loop iterator.


Usage
*****
.. toctree::
    :caption: Demo

    /ipynbs/GenericCmdCtrlSweep.ipynb

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
