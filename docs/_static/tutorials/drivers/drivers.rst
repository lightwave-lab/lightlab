Making drivers compatible with the lightwave package
====================================================

Drivers are hard and the original impetus for sharing this project. In ``lightlab``, there are basically two levels of abstraction. On one level: Oscilloscope. On another level: TEKTRONIX,DPO4034. All oscilloscopes have some form of acquiring a waveform, and user code makes use of that abstraction. This section is about writing low-level drivers that connect the actual instrument with the abstraction level.

If you have a scope other than a TEKTRONIX,DPO4034, you are on your own with that. Good luck. BUT, if you can make your low-level driver for that scope to meet the abstraction of "lightwave.equipment.Oscope," then your scope will be equivalent to my scope, in some sense. That means all of the rest of the package becomes available.

To help, we've created some generally useful tools to deal with synchronizing states between code and instrument and reality. Some examples are the :py:class:`~lightlab.equipment.__instrold.TekConfig` and :py:class:`~lightlab.equipment.__instrold.Configurable` classes. Often, you'd want to create a consistency between code and instrument, but it doesn't make sense to call configuration commands all the time. :py:class:`~lightlab.equipment.__instrold.Configurable` builds up a minimal notion of consistent state and updates hardware only when it might have become inconsistent.

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
