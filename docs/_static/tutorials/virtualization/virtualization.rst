Virtualization
==============================================
Virtual experiments are meant to behave exactly like a real lab would, except by using code calls to simulators rather than real instruments. This is useful for several reasons

1. Developing/debugging procedures quickly and safely

2. Validating that procedures will work and not go out of range before running on a real device

3. Unit testing code that refers to instruments in a repeatable virtual environment

.. contents:: In this section
    :local:

.. currentmodule:: lightlab.laboratory.virtualization

Procedural abstraction
----------------------
A procedure is automated code that uses instruments. It could just be a simple sweep, or it could be a complex interactive search. The goal of a procedure could be extracting parameters from a device (see the demo in lightlab/notebooks/Examples), controlling something (such as a peak tracker), or calibrating something.

.. figure:: compare.pdf
    :alt: Comparison
    :align: center

    Comparison of a real experiment and a virtual experiment. A key difference is where state is held.

In a real setting, the procedure is given reference to a hardware :py:class:`~lightlab.laboratory.instruments.Instrument`. The instrument contains a driver that talks to the actual piece of equipment. This equipment is hooked up to a real-life device.

In a virtual setting, we can use a :py:class:`~VirtualInstrument` to provide a partial API that matches the real Instrument. In the example, the provided methods are ``setVoltage`` and ``measCurrent``. The virtual setting needs a model to determine what will be measured given a particular actuation.

Why separate VirtualInstrument and the simulation model?
********************************************************
Instead, we could make a class called ``VirtualKeithleyWithDiodeAttached`` that provides the same methods. It's ``getVoltage`` method would do the diode computation. There are a few reasons why we argue not to do that.

1. Keeping state in one place
    In the real experiment, the entire "state" of the lab can be described by what is in the drivers (which should match the configuration of the actual equipment). Similarly, for virtual, you should not have to go digging around the simulator to figure out the entire "state".

2. Functional simulators
    Easy to test and debug. Easy to compose into larger simulators.

3. Enforces the proper namespace
    Your procedure should not be able to directly see your model. It should only be interacting with Instrument-like things

4. Avoid creating a special purpose instrument for every experiment
    You can re-use VirtualKeithley with a different model in its ``viResistiveRef``.

Clearly, ``VirtualKeithleyWithDiodeAttached`` is a bad instrument because it is not re-usable. It is a bad simulator because it cannot be composed with other simulators, and it is difficult to unit test because the return of ``getVoltage`` depends on history. These points come into play when simulation models get more complicated.

Dual Instruments
----------------
:py:class:`~DualInstrument` wraps two instruments: one real and one virtual. The procedure can be given a reference to the dual instrument, just as it was before. The dual construct makes sure that there is an exact correspondence between the two cases.

.. figure:: dual.pdf
    :alt: Dual experimental setup
    :align: center

    A dual experiment for testing ``myProcedure``. It can run either as virtual or as real by flipping a switch in ``myDualKeithly``, without rewriting any code in ``myProcedure``

Dual instrument is :py:class:`~Virtualizable` which means it has an attribute ``virtual`` that controls the switch. More useful: it provides context managers called ``asReal`` and ``asVirtual``. The benefit of context managers is they allow entry and exit operations, in this case, usually hardware warmup and cooldown methods. They can also be used to synchonize multiple Virtualizable things in more complex cases. See :py:meth:`~Virtualizable.synchronize`.

.. todo::

    Fix the notebook referred to here and reference it.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
