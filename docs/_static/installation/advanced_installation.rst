.. _advanced_installation:

Server Installation Instructions (Advanced)
-------------------------------------------

The :mod:`~lightlab.laboratory.state` module saves information about instruments, benches, and remote hosts in a file called ``~/.lightlab/labstate.json``. Normally you wouldn't have to change the location of this file. But if you so desired to, it suffices to use the shell utility ``lightlab``::

    $ lightlab config set labstate.filepath '~/.lightlab/newlocation.json'
    $ lightlab config get labstate.filepath
    labstate.filepath: ~/.lightlab/newlocation.json

It is also possible to set a system default for all users with the ``--system`` flag::


    $ sudo lightlab config --system set labstate.filepath /usr/local/etc/lightlab/labstate.json
    Password:
    ----saving /usr/local/etc/lightlab.conf----
    [labstate]
    filepath = /usr/local/etc/lightlab/labstate.json


But all users must have write access to that file in order to make their own alterations. A backup is generated every time a new version of labstate is saved in the following format ``labstate_{timestamp}.json``.
