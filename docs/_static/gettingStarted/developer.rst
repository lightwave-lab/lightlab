Developer workflow setup
================================================

.. contents:: In this section
    :local:


TODO: transfer some sections to ReST. Fill in Git. Write intro

<< Introduction >> Computer things particular to remote experiments

* Develop the code on the machine that it will run. This is presumably remote since it has to be in a lab close to your equipment.
* You cannot access our hardware. You can access our own. Or you can work with virtual aspects.


Make an rsa key
-----------------------
**ToDO: make this RST**
`Generate an SSH key pair <https://docs.gitlab.com/ce/ssh/README.html#generating-a-new-ssh-key-pair>`_ on the server via:
```
ssh-keygen -t rsa -C "your.email@example.com" -b 4096
```
Whether or not you generate a password is up to you. You can now print it using
```
cat ~/.ssh/id_rsa.pub
```
and copy-paste it into your git lab profile by going to the top right and navigating to `Settings` --> `SSH keys`.
Once SSH key pairs are generated, you can download the latest calibration tools via `git clone <ssh-address>` with the address specified above.

Remote machine
--------------
Logging on
**********
First, make sure that your have a user account set up on the your server.
This should include your SSH public key ``localhost:~/.ssh/id_rsa.pub`` copied into the file ``<server>:~/.ssh/authorized_keys``.

Add the following lines to the file ``localhost:~/.ssh/config``::

    Host <server>
         HostName lightwave-lab-<server>.princeton.edu
         User <username>
         Port 22
         IdentityFile ~/.ssh/id_rsa

You can now ``ssh <server>``, but it is recommended that you use `MOSH <https://mosh.org/>`_ to connect to the server::

    $ mosh <server>

File system sync
****************
It is recommended that you use SSHFS to mirror your work to your local computer. There is no need to clone to your local computer.

1. Clone the project into your server home directory, and install the virtual environment there.

2. Install SSHFS on your local system.

    - Linux: ``sudo apt-get install sshfs``
    - OSX: `Download binaries <https://osxfuse.github.io>`_ and then
        - Install FUSE for macOS
        - Install SSHFS for macOS

3. Make shortcuts in your ``.bashrc``.

Linux::

    alias mntlight='sshfs <server>:/path/to/calibration-instrumentation /path/to/local/dir -C -o allow_other'
    alias umntlight='fusermount -u /path/to/local/dir'

MacOS::

    alias mntlight='sshfs <server>:/path/to/calibration-instrumentation /path/to/local/dir -C -o allow_other,auto_cache,reconnect,defer_permissions,noappledouble'
    alias umntlight='umount /path/to/local/dir'

4. Now you can mount and unmount your remote calibration-instrumentation folder with::

    $ mntlight
    $ unmtlight

Git
---
At the time of writing, we have this hosted on a GitLab server, so you need to be a member of Lightwave Lab to get the clone link. Presumably you have cloned if you are here. To get further updates, use ``git pull``. When you make changes that you wish to be permanent::

    $ git add .
    $ git commit -m "some descriptive message"

You can commit many times before re-syncing with the centralized repository. When you wish to do so, always pull first, resolve conflicts, and then you can push.


Developer tools
---------------
Use a virtual environment. This environment can be git-tracked. You will need to enter this environment to execute compiled code, install and freeze dependencies, and launch IPython servers. The first time, install virtualenv on your system environment::

    $ pip install virtualenv

To create and enter virtual environment any time::

    $ make venv
    $ source venv/bin/activate

To exit virtual environment::

    $ deactivate

For developers, the following command builds and install into the virtual environment::

    $ make devbuild

To build in venv and run tests::

    $ make test

Adding a new package
********************

When you add a Python Package in the venv, install with pip. Make sure you add the new package to the requirements file::

    $ pip freeze --local | grep -v '^\-e' > requirements.txt

and then commit. Anyone else pulling from git will have their pip tell them that a new package was added, and automatically install it. **If you do not grep** above, it will tell everyone else to install your specific commit state, and that would be very bad.

**Don't break the documentation**

    If you import an external package, sphinx will try to load it and fail. The solution is to mock it. Lets say your source file wants to import::

        import scipy.optimize as opt

    For this to pass and build the docs, you have to go into the ``docs/sphinx/conf.py`` file. Then add that package to the list of mocks like so::

        MOCK_MODULES = [<other stuff>, 'scipy.optimize']

Jupyter
-------
Password protect
****************
Jupyter lets you run commands on your machine from a web browser. That is dangerous because anybody with an iphone can obliviate your computer with ``rm -rf /``, and they can obliviate your research with ``currentSource(applyAmps=1e6)``. Let's be safe on this one.

On the lab computer, first get in the project virtual environment::

    $ make venv
    $ source venv/bin/activate

Copy and modify the provided template::

    $ mkdir ~/.jupyter
    $ cp /home/jupyter/.jupyter/jupyter_notebook_config.py ~/.jupyter

then generate a password with::

    $ make getjpass
    Enter password: <Enters password>
    Verify password: <Enters password>

This will produce one line containing a hash of that password of the form::

    sha1:b61b...frq

Choose an unused port. Port allocations on your lab computer should be discussed with your group. Let's say you got :8885.

When you have a port and a password hash, update the config file::

    $ nano ~/.jupyter/jupyter_notebook_config.py

.. code-block:: python

    ...
    ## Hashed password to use for web authentication.
    c.NotebookApp.password = 'sha1:b61b...frq' # hash from above
    ...
    ## The port the notebook server will listen on.
    c.NotebookApp.port = 8885 # port from above

Launch the server
*****************
To launch the server in the right place, just run::

    $ make jupyter

Except that will lock up your shell session. Instead, you can spin off a process to serve jupyter in a tmux::

    $ tmux new -s myNotebookServer
    $ make jupyter
    <Ctrl-b, d>  # to detach

You can now acces your notebooks anywhere with your password at: `https://lightwave-lab-<server>.princeton.edu:<port>`.

If for some reason you want to reconnect to this process, you can use ``tmux attach-process -t myNotebookServer`` or ``tmux ls`` followed by picking the right name. If you really want to kill it, you can::

    $ ps aux | grep <username> | grep myNotebookServer

Find the PID, and send a ``kill -9`` at it.

.. note:: file system structure in the lightwave lab: all Jupyter files are kept in the ``notebooks`` directory, which is a sister directory of the ``lightlab`` directory containing all the code. Within ``notebooks``, the directory ``sketchpad`` is ignored by git, so you can play around here.


Monitor server
--------------
To monitor your processes from a standard unsecure webpage, you can set up another server. So far, this is just for long sweeps that simply tell you how far along they are, and when they will complete.

First, you must get another port allocated to you, different from the one you used for Jupyter. Put that in a file called ``.monitorserverport`` in your git project root directory (where the Makefile is). Let's say that port is 8000::

    $ echo 8000 > .monitorserverport

To then launch the server from a tmux::

    $ tmux new -s monitorServer
    $ source venv/bin/activate
    $ make monitorhost
    <Ctrl-b, d>  # to detach

You can test if it's working in the notebook below.

.. toctree::
    :maxdepth: 1

    /ipynbs/TestPrintProgressServer.ipynb

.. note::

    I have tried making this launch a daemon automatically. You can see some fork functions in util.io. I have not yet verified that it is safe, so it is currently disabled.


Specific to Lightwave Lab
-------------------------

GitLab repository
******************
The GitLab project page is https://lightwave.princeton.edu:444/atait/calibration-instrumentation, and the project can be cloned like this::

    $ git clone git@lightwave.princeton.edu:atait/calibration-instrumentation.git


Current port allocations
************************

**Olympias**:

==== ======== ===========
Port User     Activity
==== ======== ===========
8888 (master) Jupyter
8889 egordon  Jupyter
8890 atait    Jupyter
8050 atait    monitoring
==== ======== ===========

Allowed Jupyter ports are 8888-8893. Allowed monitor ports are anything. Olympias is in the ``.princeton.edu`` domain (no ``.ee``).

**Cassander**:

==== ======== =============
Port User     Activity
==== ======== =============
8890 atait    Jupyter
8891 yechim   Jupyter
8050 atait    monitoring
8049 atait    documentation
==== ======== =============

Allowed Jupyter ports are 8888-8893. Allowed monitor ports are 8050-8060.

Jupyter uses HTTPS, while the others use HTTP. Cassander is in the ``.ee.princeton.edu`` domain.

**Hermes**:

==== ======== =============
Port User     Activity
==== ======== =============
8889 mnahmias Jupyter
==== ======== =============


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
