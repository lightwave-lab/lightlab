Making drivers compatible with the lightwave package
====================================================

Drivers are hard and the original impetus for sharing this project. In ``lightlab``, there are basically two levels of abstraction.

1. :py:class:`~Instrument`, such as :py:class:`~Oscilloscope`

2. :py:module:`~visa_drivers`, such as :py:class:`~Tektronix_DSA8300_Oscope`

All oscilloscopes have some form of acquiring a waveform, and user code makes use of that abstraction. If you have a scope other than a TEKTRONIX DSA8300, you are on your own with that. BUT, if you can make your low-level driver for that scope to meet the abstraction of :py:class:`~Oscilloscope`, then your scope will be equivalent to my scope, in some sense. That means all of the rest of the package becomes available.

This section is about writing low-level drivers that connect the actual instrument with the abstraction level.

Writing a VISAInstrumentDriver
------------------------------

Configurable
------------
To help, we've created some generally useful tools to deal with synchronizing states between code and instrument and reality. Some examples are the :py:class:`~lightlab.equipment.lab_instruments.configure.tek_config.TekConfig` and :py:class:`~lightlab.equipment.lab_instruments.configure.configurable.Configurable` classes. Often, you'd want to create a consistency between code and instrument, but it doesn't make sense to call configuration commands all the time. :py:class:`~lightlab.equipment.lab_instruments.configure.configurable.Configurable` builds up a minimal notion of consistent state and updates hardware only when it might have become inconsistent.

Difference between setup and open
---------------------------------

How to read a programmer manual
-------------------------------------


Writing an Instrument
---------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
