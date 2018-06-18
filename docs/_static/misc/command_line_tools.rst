Command-line tools
==================

These are installed with lightlab.

lightlab config
---------------

The ``lightlab config`` tool manipulates an `ini-style <https://docs.python.org/3/library/configparser.html>`_ file that contains some configuration information for lightlab. This file can be stored in ``/usr/local/etc/lightlab.conf`` and/or ``~/.lightlab/config.conf``. Values defined in the second overrides the first, which in turn overrides default values.

Here's how to use:

.. code-block:: bash

    $ lightlab config

    usage: lightlab config [-h] [--system] [command] ...

    positional arguments:
      command     write-default: write default configuration
                  get [a.b [a2.b2]]: get configuration values
                  set a.b c: set configuration value
                  reset a[.b]: unset configuration value
      params

    optional arguments:
      -h, --help  show this help message and exit
      --system    manipulate lightlab configuration for all users. run as root.
    $ lightlab config get # reads all variables
    labstate.filepath: ~/.lightlab/labstate.json

    $ lightlab config set labstate.filepath ~/.lightlab/newpath.json
    ----saving /Users/tlima/.lightlab/config.conf----
    [labstate]
    filepath = /Users/tlima/.lightlab/newpath.json

    -------------------------------------------------
    $ lightlab config set labstate.filepath '~/.lightlab/newpath.json'
    ----saving /Users/tlima/.lightlab/config.conf----
    [labstate]
    filepath = ~/.lightlab/newpath.json

    -------------------------------------------------
    $ lightlab config get
    labstate.filepath: ~/.lightlab/newpath.json

    $ lightlab config --system get
    labstate.filepath: ~/.lightlab/labstate.json

    $ lightlab config reset labstate # could be labstate.filepath
    labstate.* reset.
    ----saving /Users/tlima/.lightlab/config.conf----
    -------------------------------------------------

    $ lightlab config get
    labstate.filepath: ~/.lightlab/labstate.json

    #### Interesting for server configurations

    $ lightlab config --system set labstate.filepath '/usr/local/etc/lightlab/labstate-system.json'
    Write permission to /usr/local/etc/lightlab.conf denied. You cannot save. Try again with sudo.

    $ sudo lightlab config --system set labstate.filepath '/usr/local/etc/lightlab/labstate-system.json'
    Password:
    ----saving /usr/local/etc/lightlab.conf----
    [labstate]
    filepath = /usr/local/etc/lightlab/labstate-system.json

    -------------------------------------------

    $ lightlab config get
    labstate.filepath: /usr/local/etc/lightlab/labstate-system.json
