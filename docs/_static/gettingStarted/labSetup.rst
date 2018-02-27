Setting up your lab
================================================

At its heart, this package and code is all about the real world. It's not the world of smart phones and "UX" and mouse clicks -- it's the physics of volts and photons, or whatever else you have there. Here are some steps to hook up that special instrumentation to this code base.

Todo for documenting this
-------------------------
* basics on GPIB
* how to write drivers
* registering your drivers with the main packages (depending on virtual lab implementation)

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


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
