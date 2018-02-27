## Remote Hardware Control

Calibration work that involves real hardware should take place on a dedicated Lightwave Laboratory Server: for example, Olympias or Hermes. 
Once installation is complete, you can use the following commands to safely log in, create a persistent SSH session, and instantiate a new jupyter notebook:
```
$ mosh <server>
$ tmux new -s notebook OR screen -S notebook
$ cd calibration-instrumentation
$ make jupyter
```
You can now navigate to your jupyter session in your browser via `https://lightwave-lab-<server>.princeton.edu:<port>` as specified in the window.
* To end the jupyter session, use `^C`.
* You can use the `exit` command to exit both your virtual SSH or mosh session.
* To disconnect but keep jupyter running, simply close your Terminal session. Once you log back in with MOSH, use `screen -r` or `tmux attach` to re-attach your previous session.

# Installation
### SSH Setup

First, make sure that your have a user account set up on the your server.
This should include your SSH public key `localhost:~/.ssh/id_rsa.pub` copied into the file `<server>:~/.ssh/authorized_keys`.

Add the following lines to the file `localhost:~/.ssh/config`
```
Host <server>
     HostName lightwave-lab-<server>.ee.princeton.edu
     User <username>
     Port 22
     IdentityFile ~/.ssh/id_rsa
```

It is recommended that you use [MOSH](https://mosh.org/) to connect to the server:
```
$ mosh <server>
```

### SSHFS (Optional)
It is recommended that you use SSHFS to mirror your work to your local computer.
* Clone the project into your server home directory, and install the virtual environment there.
* Install SSHFS on your local system.
 * Linux: `sudo apt-get install sshfs`
 * OSX: [Download binaries here](https://osxfuse.github.io)
     1. Install FUSE for maxOS, and then
     2. Install SSHFS
 * OSX (Outdated): [Instructions Here](https://gist.github.com/henriquea/4556954)
     - Problem is that `fuse4x` is no longer supported by Homebrew
* Mirror directory on your local system, add the following to your .bashrc:
```
alias mntlight='sshfs <server>:/path/to/calibration-instrumentation /path/to/local/dir -C -o allow_other'
alias umntlight='[OSX: umount] [Linux: fusermount -u] /path/to/local/dir'
```
* Execute `mntlight` and `umntlight` to mount and unmount your server calibration-instrumentation folder.

### Git
Now, you can clone this git repository into the default user directory located on the server.
It is recommended that you [generate an SSH key pair](https://docs.gitlab.com/ce/ssh/README.html#generating-a-new-ssh-key-pair) on the server via:
```
ssh-keygen -t rsa -C "your.email@example.com" -b 4096
```
Whether or not you generate a password is up to you. You can now print it using
```
cat ~/.ssh/id_rsa.pub
```
and copy-paste it into your git lab profile by going to the top right and navigating to `Settings` --> `SSH keys`.
Once SSH key pairs are generated, you can download the latest calibration tools via `git clone <ssh-address>`.
This address can be found at the top of this page.
### SSH Virtualization
Before you run jupyter, you should instantiate a virtual SSH environment. 
This is a safety precaution that will prevent the terminal session from disappearing if you are suddenly disconnected.
Virtual SSH environments also come with additional features, such as window management.
You can use either `screen` or `tmux`, depending on personal preference.
To initialize a new virtual session with the name 'notebook:'
```
$ screen -S notebook
$ tmux new -s notebook
```
You can use the `exit` command to terminate. If you are disconnected and log back into the machine, use
```
$ screen -r
$ tmux attach
```
to reconnect to your virtual session. You can check what virtual sessions exist via
```
$ screen -ls
$ tmux list-sessions
```

### Jupyter
*Access the Master Branch Jupyter Server At: `https://lightwave-lab-<server>.princeton.edu:<port>`*

Make sure you are inside the calibration-instrumentation directory before continuing.
To set up a secure jupyter environment:
* Make a copy of the template config file.
```
$ mkdir ~/.jupyter
$ cp /home/jupyter/.jupyter/jupyter_notebook_config.py ~/.jupyter
```
* Generate a new password for your jupyter notebook server (also instantiates a virtual environment with proper Python packages):
```
$ make jupyter-password
```
* Choose an unused port. 

Current port allocations on Olympias:

| User | Port |
|---|---|
| *master* | 8888 |
| egordon  | 8889 |
| atait    | 8890 |

Note that an unused port will be automatically assigned to you during `make jupyter` if one is not specified.

* Update your config file (and this README) with your selections.
```
$ nano ~/.jupyter/jupyter_notebook_config.py
...
## The port the notebook server will listen on.
c.NotebookApp.port = <port from above>
```

Once you have initialized your virtual SSH session and specified a password, you can start a local jupyter server in the `notebooks` directory at any time using:
```
$ make jupyter
```
This will first build a development version of `lightlab` in the virtual (`venv`) environment, and execute the jupyter server in that virtual environment.
The virtual environment is instantiated to keep package dependencies separate from one another in different projects (i.e. calibration instrumentation vs. SIMPEL).
If this is your first time, it will download all the packages currently specified in `requirements.txt`. Otherwise, it will update your packages to the current versions.
Feel free to create a directory `notebooks/sketchpad` to make notebooks that are not git-tracked.

* Access your jupyter notebook server anywhere with your password at: `https://lightwave-lab-<server>.ee.princeton.edu:<port>`

# Developer Tools

If you want to install in Root System (discouraged):
```
$ python3 setup.py install
```

To create and enter virtual environment:
```
$ make venv
$ source venv/bin/activate
```

To Exit Virtual Environment:
```
deactivate
```

For developers, the following command builds and install into the virtual environment:
```
$ make devbuild
```

Finally, to build in venv and run tests:
```
make test
```

When you add a Python Package in the venv, install with pip. Make sure you add the new package to the requirements file:
```
pip freeze --local | grep -v '^\-e' > requirements.txt
```

In order to update external packages, please run the command:
```
pip freeze --local | grep -v '^\-e' | cut -d = -f 1  | xargs -n1 pip install -U
```

Remember that, after re-running `make devbuild`, you only need to restart jupyter's kernel to update.
Also, remember that anything in `sketchpad` is not git-tracked.

* How to kill your existing notebook
```
$ ps aux | grep <your user name> | grep jupyter
```
Look through that for something that looks like a jupyter notebook kernel and kill it. For example,
```
egordon  30322  0.0  0.1 295612 18456 pts/9    Sl+  Mar02   6:12 /home/egordon/calibration-instrumentation/venv/bin/python3 venv/bin/jupyter-notebook
$ kill -9 30322
```

# Building documentation
Documentation is built automatically using the same makefile using this command
```
$ make docs
```
This compiles an html hierarchy. You can open the root page like this
```
$ open docs/sphinx/_build/html/index.html
```

## Version control for Jupyter Notebooks
Jupyter notebooks have basically two sections: inputs (code, markdown) and outputs (stdout, plots, images). `.ipynb` files store all of the compiled outputs. This is good if you want to restart a kernel but still see the output, or if you close the file, etc. The problem is that the outputs are large binary images. This messes with git in two ways:
    * Changes to binary outputs take up a huge amount of space, even if nothing significant actually changed, and
    * Diff-ing your work against someone else's is impossible

To avoid having git track compiled outputs, follow these instructions (from [here](https://github.com/toobaz/ipynb_output_filter))
1. Get the script that does the filtering
```
(mkdir ~/bin)
curl https://raw.githubusercontent.com/toobaz/ipynb_output_filter/master/ipynb_output_filter.py -o ~/bin/ipynb_output_filter.py
chmod +x ~/bin/ipynb_output_filter.py
```

2. Tell your git installation how to find it
```
echo "*.ipynb filter=dropoutput_ipynb" >> ~/.gitattributes
git config --global core.attributesfile ~/.gitattributes
git config --global filter.dropoutput_ipynb.clean ~/bin/ipynb_output_filter.py
git config --global filter.dropoutput_ipynb.smudge cat
```
This has changed your global configuration, so the filter works on your other git projects. If you don't want that, you can disable it on a project-by-project basis in the ``.git/info/attributes`` file. Or you can disable it on a global basis by changing the `~/.gitattributes` file line to `*.ipynb filter=`.

### If you are contributing to this project, please use the notebook filters!

### Sweep Progress Monitor Server

#### On Olympias
* Start the monitor in a screen session:
```
screen -S sweepProgressMonitor
make sweepprogress
```
`Ctrl-a, Ctrl-d`

* Access your monitoring server anywhere at: `http://lightwave-lab-olympias.princeton.edu:8850`

Remember that, after re-running `make devbuild`, you only need to restart jupyter's kernel to update.
Also, remember that anything in `sketchpad` is not git-tracked.

* How to kill the monitor for some reason
```
$ ps aux | grep atait | grep sweepProgressMonitor
```
It should be the only result.

For example
```
atait    19256  0.0  0.0  27204  2860 ?        Ss   22:55   0:00 SCREEN -S sweepProgressMonitor
$ kill -9 19265
```
