Making and changing the lab state
=================================

One time: Hosts and benches
---------------------------

First you need to add some hosts and benches to the lab. This usually happens only once. Suppose we have a computer called "brian" that is a host `and` the centralized instrumentation server. It is physically located on Bert's bench::

    from lightlab.laboratory.state import lab
    from lightlab.laboratory.instruments import Host, Bench

    # Start by making a host. This is a real computer.
    brianHost = Host(name='brian',  # This is its key that will go into labstate
                     hostname='labdns-brian.school.edu',  # This depends on your DNS naming conventions
                     mac_address='00:00:00:00:00:00',
                     is_instrumentation_server=True,  # You need exactly one of these. This is where lightlab code is installed
                     os='linux-centos')
    assert brianHost.isLive()  # Sends a ping request
    lab.updateHost(brianHost)
    lab.saveState()

Next, let's add a remote host called "gunther". It connects to some instruments and is running VISA server that will be contacted by the central server (brian)::

    guntherHost = Host(name='gunther',into labstate
                       hostname='labdns-gunther.school.edu',
                       mac_address='00:00:00:00:00:01',
                       os='windows')
    assert guntherHost.isLive()
    lab.updateHost(guntherHost)
    lab.saveState()

Next, a bench. Benches are not strictly necessary but useful by convention::

    bertBench = Bench(name='bert')
    lab.updateBench(bertBench)
    lab.saveState()

.. note::

    For ``isLive`` to work, the host must be configured to respond to pings.

Instruments
-----------

Instruments can be configured many times, for example, if they move. An example of setting one of them is below. You should copy this ipynb into your operating (``myWork``) directory as a template to run with jupyter.

.. toctree::

    /ipynbs/Others/labSetup.ipynb

Now you get that instrument from any other notebook with the command::

    from lightlab.laboratory.state import lab
    keithley = lab.instruments_dict['Keithley 21']


