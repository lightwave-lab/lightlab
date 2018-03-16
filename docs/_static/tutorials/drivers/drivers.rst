Drivers
====================================================

.. contents:: In this section
    :local:

Drivers are the original impetus for sharing this project. Writing drivers can be fun (the first few times). It exercises the full range of electrical engineering knowledge. It can be a snap, or it can take multiple PhD students several days to realize which cable needed a jiggle. The reward is automated, remote lab control!

The instrument abstraction
--------------------------
In ``lightlab``, there are two levels of abstraction for instrumentation

.. currentmodule:: lightlab.laboratory.instruments

1. :py:class:`~Instrument`, such as
    * :py:class:`~Oscilloscope`
    * :py:class:`~Keithley`

.. currentmodule:: lightlab.equipment.lab_instruments.visa_drivers

2. :py:class:`~lightlab.equipment.lab_instruments.VISAInstrumentDriver`, such as
    * :py:class:`~Tektronix_DPO4032_Oscope`
    * :py:class:`~Tektronix_DPO4034_Oscope`
    * :py:class:`~Keithley_2400_SM`

All oscilloscopes have some form of acquiring a waveform, and user code makes use of that abstraction. If you have a scope other than a TEKTRONIX DPO4032, you are on your own with the driver. BUT, if you can make your low-level driver for that scope to meet the abstraction of :py:class:`~Oscilloscope`, then your scope will be equivalent to my scope, in some sense. That means all of the rest of the package becomes usable with that scope.

The critical part of an Instrument child class are its ``essentialMethods`` and ``essentialProperties``. Two lists; that's it. Initialization and book keeping are all done by the super class, and implementation is done by the driver. The driver must implement all of the essential methods and properties, and then the :py:class:`~Instrument` will take on these data members as its own.

.. note::

    This above abstraction does not exactly refer to :py:mod:`lightlab.equipment.abstract_instruments`, which is somewhat under construction slash marked for deletion.

An :py:class:`~lightlab.laboratory.instruments.Instrument` refers to a category of instruments that do certain things. A :py:class:`~lightlab.equipment.lab_instruments.VISAInstrumentDriver` describes how a particular piece of equipment does it. As a rule of thumb, there is a different driver for each model of instrument; however, as in the case of Tektronix_DPO4032_Oscope and Tektronix_DPO4034_Oscope, there is substantial overlap in implementation. They inherit a common base class, Tektronix_DPO403X_Oscope, that does most of the work.

Writing a :py:class:`~lightlab.equipment.lab_instruments.VISAInstrumentDriver`
-------------------------------------------------------------------------------
For new developers, you will likely have instruments not yet contained in ``lightlab``. We encourage you to write them, test them, and then create a pull request so that others won't have to re-invent the wheel.

Basics
------
A communication session with a message-based resource has the following commands

    * open
    * close
    * write
    * read
    * query (a combination of write, then read)

The `PyVISA <http://pyvisa.readthedocs.io/en/stable/>`_ package provides the low level communication. Drivers can be GPIB, USB, serial, or TCP/IP -- the main difference is in the address. PyVISA also has a resource manager for initially finding the instrument. ``lightlab`` has a wrapper for this that works with multiple remote Hosts. See :doc:`/_static/developers/labState` for putting a Host in the labstate.

Plug your new instrument (let's say GPIB, address 23) into host "alice", then, in an ipython session

.. code-block:: python
    :emphasize-lines: 10

    > from lightlab.laboratory.state import lab
    > for resource in lab.hosts['alice'].list_resources_info():
    ...   print(resource)
    visa://alice.school.edu/USB0::0x0699::0x0401::B010238::INSTR
    visa://alice.school.edu/TCPIP0::128.112.48.124::inst0::INSTR
    visa://alice.school.edu/ASRL1::INSTR
    visa://alice.school.edu/ASRL3::INSTR
    visa://alice.school.edu/ASRL10::INSTR
    visa://alice.school.edu/GPIB0::18::INSTR
    visa://alice.school.edu/GPIB0::23::INSTR

That means the instrument is visible, and we know the full address.

    > from lightlab.equipment.lab_instruments.visa_connection import VISAObject
    > newInst = VISAObject('visa://alice.school.edu/GPIB0::23::INSTR')
    > print(newInst.instrID())
    KEITHLEY INSTRUMENTS INC.,MODEL 2400, ...

That means the instrument is responsive, and basic communication settings are correct already. Time to start writing.

Command syntax
--------------

Configuration
-------------
To help, we've created some generally useful tools to deal with synchronizing states between code and instrument and reality. Some examples are the :py:class:`~lightlab.equipment.lab_instruments.configure.tek_config.TekConfig` and :py:class:`~lightlab.equipment.lab_instruments.configure.configurable.Configurable` classes. Often, you'd want to create a consistency between code and instrument, but it doesn't make sense to call configuration commands all the time. :py:class:`~lightlab.equipment.lab_instruments.configure.configurable.Configurable` builds up a minimal notion of consistent state and updates hardware only when it might have become inconsistent.

Setup, configure, measure/actuate

Syntax

"\*IDN?"

Difference between setup and open
---------------------------------

How to read a programmer manual
-------------------------------------
You need the manual to find the right commands. They are often very long and describe everything from scratch. They sometimes refer to programming with vendor-supplied GUI software -- don't want that. You are looking for a command reference, or sometimes coding examples.

.. figure:: pmManual.pdf
    :alt: An old school manual
    :align: center
    :width: 90%

    Manual of the HP 8152A Power Meter (1982). Go to the contents and look for something like "command summary."

which turns into the following driver (simplified)

.. code-block:: python

    class HP8152(VISAInstrumentDriver):
        ''' The HP 8152 power meter

            `Manual <http://www.lightwavestore.com/product_datasheet/OTI-OPM-L-030C_pdf4.pdf>`_
        '''
        def startup(self):
            self.write('T1')

        def powerDbm(self, channel=1):
            '''
                Args:
                    channel (int): 1 (A), 2 (B), or 3 (A/B)
            '''
            self.write('CH' + str(channel))
            returnString = self.query('TRG')
            return float(returnString)


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
