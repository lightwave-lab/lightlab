User: getting started
=====================

Not really sure what this means. As of now, everyobdy is a developer.

:doc:`docYourCode`

Make sure you have python I guess.

#. one

#. two


Connecting to the instrumentation server
----------------------------------------
First, make sure that your have a user account set up on the your server. Let's say your domain is "school.edu" First, do a manual log on to change your password to a good password. From your local machine::

    $ ssh -p 22 <remote username>@<server hostname>.school.edu
    <Enter old password>
    $ passwd
    <Enter old, default password, then the new one>

Make an RSA key
***************
On your local machine::

    ssh-keygen -t rsa -C "your.email@school.edu" -b 4096

You do not have to make a password on your ssh key twice, so press enter twice. Then copy that key to the server with::

    $ ssh-copy-id <remote username>@<server hostname>.school.edu
    <Enter new password>

Faster logging on
*****************
In your local machine, add the following lines to the file ``~/.ssh/config``::

    Host <short name>
         HostName <server name>.school.edu
         User <remote username>
         Port 22
         IdentityFile ~/.ssh/id_rsa

You can now ``ssh <short name>``, but it is recommended that you use `MOSH <https://mosh.org/>`_ to connect to the server::

    $ mosh <short name>

MOSH is great for spotty connections, or if you want to close your computer and reopen the ssh session automatically.

.. Indices and tables
.. ==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
