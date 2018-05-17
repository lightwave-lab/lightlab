## Making pull requests
We manage contributions with pull requests. If you have not done so yet, then start by forking the lightlab repository.

We follow a [branching model](http://nvie.com/posts/a-successful-git-branching-model/) in which no one should commit directly to the master or development branches. To make changes, create a new branch *based off of development*. Give it a meaningful name. If you are writing a new driver, start those branch names with "driver-".
```bash
git checkout development
git checkout -b driver-arduino-LEDDisplay
```
Make the changes. Tell others how it's used: Documenation can happen in the docstrings because documentation makes AutoAPI. Show others how it's used: If it's a code feature, write a test in `tests` or in `notebooks/Tests`. If it's a driver, write a notebook in `notebooks/BasicHardwareTests`. 

Push changes to Github, still on your fork (a.k.a. origin).
```bash
git push origin driver-arduino-LEDDisplay
```
Finally, create a pull request to have that branch incorporated into the central repository (a.k.a. upstream). 

