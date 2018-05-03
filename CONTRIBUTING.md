## Making pull requests
We manage contributions with pull requests. If you have not done so yet, then start by forking the lightlab repository.

You should never edit code on the master or development branches! To make changes, create a new branch *based off of development*. Give it a meaningful name. If you are writing a new driver, start those branch names with "driver-".
```bash
git checkout development
git checkout -b driver-arduino-LEDDisplay
```
Make the changes. Be sure to test and document as described in __section__.
Push them to Github, still on your fork (a.k.a. origin).
```bash
git push origin driver-arduino-LEDDisplay
```
Finally, create a pull request to have that branch incorporated into the central repository (a.k.a. upstream).
