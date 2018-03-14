Making and changing the lab state
=================================

One time: Hosts and benches
---------------------------

First you need to add some hosts and benches to the lab. This usually happens only once. Suppose we have a computer called "alice" that is a host. It connects to some instruments and is running VISA server. It is physically located on Bob's bench::

    from lightlab.laboratory.state import lab
    from lightlab.laboratory.instruments import Host, Bench

    # Start by making a host. This is a real computer.
    aliceHost = Host(name='alice', hostname='alice.school.edu',
                  mac_address='00:00:00:00:00:00', os='windows')
    assert aliceHost.isLive() # Sends a ping request
    lab.updateHost(aliceHost)

    # Then a bench. This is not strictly necessary but useful by convention
    bobBench = Bench(name='bob')
    lab.updateBench(bobBench)

    # Save it
    lab.saveState()

Instruments
-----------

Instruments can be configured many times, for example, if they move. An example of setting one of them is below. You can copy the ipynb into your operating directory as a template to run with jupyter.

.. toctree::

    labSetup.ipynb

Now you get that instrument from any other notebook with the command::

    from lightlab.laboratory.state import lab
    keithley = lab.instruments_dict['Keithley 21']


