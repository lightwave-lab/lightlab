Sysadmin: getting started
================================================
The basic setup is that there is one central lab computer that is the "instrumentation server." Other computers connect to the instruments through GPIB/USB/etc. These are "hosts." All of the hosts need National Instruments (NI) Measurement and Automation eXplorer (MAX).

*The below assumes that this system is Linux.*

There is a difference between cases where 1) all your lab members are ``lightlab`` users and 2) some of your lab members are ``lightlab`` developers and 3) all are developers and know what they are doing.


Installing NI-visa (32-bit) in Ubuntu (64-bit)
----------------------------------------------
Followed instructions in `here <http://forums.ni.com/t5/Linux-Users/Using-NI-VISA-with-Arch-Linux-or-Ubuntu-14-04/gpm-p/3462361#M2287>`_, but in computers with EFI secure boot, like all modern ones, we need to sign the kernel modules for and add the certificate to the EFI. For this, follow these `instructions <http://askubuntu.com/questions/762254/why-do-i-get-required-key-not-available-when-install-3rd-party-kernel-modules>`_.

Sign all modules in ``/lib/modules/newest_kernel/kernel/natinst/*/*/.ko``

Run the following after sudo updateNIdrivers (reboot required!)::

    kofiles=$(find /lib/modules/$(uname -r)/kernel/natinst | grep .ko)
    for kofile in $kofiles; do
        sudo /usr/src/linux-headers-$(uname -r)/scripts/sign-file sha256 /home/tlima/MOK.priv /home/tlima/MOK.der $kofile
    done

Then start nipalk::

    sudo modprobe nipalk
    sudo /etc/init.d/nipal start


Opening NI-visa servers on all hosts
------------------------------------
Open NI-MAX.

In the main menu bar: Tools > NI-VISA > VISA options. This will open a panel.

In My System > VISA Server, check "Run the VISA server on startup. " Click "Run Server Now."

In My System > VISA Server > Security, click the Add button, and put in a "*" under Remote Addresses.

Click Save at the top left.

Troubleshooting
***************
If you have been using Tektronix drivers, there might be a conflict with which VISA implementation will get used. These can be managed in the Conflict Manager tab.

General settings > Passports: Tulip sometimes gives trouble. The box should be checked, at least on 32-bit systems.


Initializing labstate on the instrumentation server
---------------------------------------------------
Make a jupyter "user"::

    sudo useradd -m jupyter
    sudo passwd jupyter
    <enter a new password twice>

Make a jupyter group specifying who is allowed to run jupyter servers and change the labstate::

    sudo groupadd jupyter
    sudo usermod -a -G jupyter alice
    sudo usermod -a -G jupyter bob
    ...

The jupyter user home directory can be accessed by any user and written only by the jupyter users::

    cd /home
    sudo chown root jupyter
    sudo chgrp jupyter jupyter
    sudo chmod a+r jupyter
    sudo chmod a+x jupyter
    sudo chmod g+w jupyter

The labstate will be automatically put and backed up in the directory ``/home/jupyter/labstate.json``. If anybody outside of group jupyter tries to change the labstate, it will not work.


@tlima please check


Running a jupyter server for users
----------------------------------
Create a directory for your lab's data gathering notebooks and data. Ours is called lightdata::

    cd /home/jupyter
    mkdir lightdata
    chgrp lightdata jupyter
    chmod a+r lightdata
    chmod a+x lightdata
    chmod g+w lightdata
    chmod +t lightdata

The last line sets the sticky bit. That means when a file is created within that directory, it can only be modified or deleted by its owner (i.e. the person that created it).

@tlima: how do you set the port and password? Where do you launch the notebook?


Set up CI for your own branches
------------------------------
@tlima I am shaky on this and the following sections


Handling virtual environments that install lightlab
---------------------------------------------------
@tlima I am shaky on this section

Install `virtualenvwrapper <http://virtualenvwrapper.readthedocs.io/en/latest/index.html>`_ with pip.

Put this in all users' ``.bashrc``::

    # Working with multiple virtualenv's
    export WORKON_HOME=/home/jupyter/Envs
    source /usr/local/bin/virtualenvwrapper.sh

They can then call ``workon development`` and ``workon master``.


Developers will have a clone of ``lightlab``
-----------------------------------------------
They will also likely be using some directory with other notebooks

_ Documents
| lightlab
| _myStuff
| | _data
| | | someData.pkl
| | gatherData.ipynb


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
