# Git with ipython notebooks
Interactive tutorials are in notebooks. A full "experiment" in the lab is contained in a notebook. Notebooks are supposed to change a lot and meant to be played with. They are graphical. They are essential to track.

- Diff-ing your work against someone else's is impossible
- Changes to binary outputs take up a huge amount of space, even if nothing significant actually changed

Jupyter notebooks have two sections: inputs (code, markdown) and outputs (stdout, plots, images). Interactive python notebook files embed compiled outputs. This is good if you want to restart a kernel but still see the output, or if you close the file, etc.

### Solution/Problem 1: The nbstripout filter
This is a cool thing that is integrated within the git commands. It basically ignores all of the outputs and metadata of `.ipynb` files. When you commit and push, it only pushes the inputs. It is installed via the requirements.txt, but there is also some interesting [discussion](https://stackoverflow.com/questions/18734739/using-ipython-notebooks-under-version-control/20844506) and [documentation](https://github.com/toobaz/ipynb_output_filter)

#### There are three downsides:
1. What if you liked keeping those outputs without rerunning every commit?
2. It has to strip evvverything, including all those high-quality graphics, every single time you `git status`.
3. It crashes your essential commands. Very easy to get into a chicken-and-egg hole where you can't `diff` anything because __some__thing isn't JSON -- causing a crash -- but you can't figure out what isn't JSON because you can't see which files just changed.
4. It corrupts your files. That's why we made cleannbline.

### Solution 2. Deactivate the nbstripout filter

    source venv/bin/activate
    nbstripout --uninstall

Never think about it again... until you have to merge.

## The merge scenario
You have branches `development` and `BSS-feature`, and you want to merge `BSS-feature` into `development`. Both have lots of notebooks with outputs, possibly with corrupted first lines.

### Preliminaries
`nbstripout` is in your venv, so activate the venv. Later, when we install the filter, it expects a clean attributes file.

    source venv/bin/activate
    rm .git/info/attributes <<don't have to do this every time>>

You should have a good file editor (Sublime) ready for lots of conflicts happening within unreadable (in multiple senses) `.ipynb` files. You will need some kind of "Find All Within Project." Have it going on your local machine with an SSHFS.

Be aware of the `cleannbline` script. Sometimes non-JSON and _non-unicode_ characters get into the first line, making them unreadable for everything. This script cleans them.

### Process
#### Create a test branch for merge
    git checkout -b test_merge_BSS-feature-into-development

#### Activate your filter
    nbstripout --install
    cat .git/info/attributes

should produce an output that looks like this

    *.ipynb filter=nbstripout
    *.ipynb diff=ipynb

#### Strip the notebooks on test branch
Run
    
    git status

It takes some time. What the hell is that error? It means that some of the notebooks are not sufficiently JSON for the nbstripout filter. 

In the crash log, it should point to a certain file, let's say `notebooks/Test.ipynb` First, clean it with

    ./cleannbline notebooks/Test.ipynb

Then, open that file in Sublime and search for `<<<<`. Sometimes conflicts in your stash can get hidden in a way that does not show up in Jupyter. nbstripout will crash. You can find it in Sublime.

Return to running `git status` until it completes without error. It should show a ton of modifications: those are the effects of stripping. Add those and commit

    git add .
    git commit -m "stripped notebooks for merge"

#### Strip the notebooks on BSS-feature branch
Your filter is currently active, so when you try

    git checkout BSS-feature

it will automatically crash. As above though, it will point to a file. Keep going until `git status` completes. Add those and commit.

Side note: even though `git status` shows a ton of modifications, you should get a clean `git diff` (Although sometimes it will just crash, NBD). Both commands are applying the ipynb filter... in some way.

#### Do the merge
    git checkout test_merge_BSS-feature-into-development
    git merge BSS-feature

You will get conflicts in two categories: notebooks and other. Since there are `<<<<` things everywhere, your `git diff` will crash while you're in the merge. It also doesn't point you to an offending file. Here is where you'll really appreciate Sublime. 

Make sure Sublime opens the entire `notebooks` _directory_. That way Find All will search all the files. 

1. Pick one file, let's say `notebooks/Test2.ipynb`
2. You might have to `./cleannbline notebooks/Test2.ipynb`
3. In sublime, fix all instances of `<<<<`, which are usually
    - Minor version changes or metadata stuff
    - Legitimate conflicts
4. When you are satisfied, go back and `git add notebooks/Test2.ipynb`

Repeat for all the notebooks. Then do the same for all the regular code files. When you run `git status` and everything is green, you are done. End the merge with
    
    git commit

If for some reason, you want to escape the merge while keeping the test_merge branch stripped, you can run `git reset --hard`

#### Finalize
Double check that everything went well (i.e. open some notebooks in Jupyter). If something screwed up in your merging _or_ stripping, you can just delete the test_merge branch and start over.

Now we're going to make changes to the real `development` branch.

    git checkout development

This will take a while. If it causes crashes, do the thing above to make sure all notebooks are valid JSON until you get a successful `git status`. Make a commit on the _real_ branch

    git add .
    git commit -m "stripped notebooks from target branch"
    git merge test_merge_BSS-feature-into-development

This should succeed without conflict. 

#### Cleanup
Remove the test branch

    git branch -d test_merge_BSS-feature-into-development

Then you __must__ deactivate the filter

    nbstripout --uninstall

Now you can move around the unclean branches without triggering crashes left and right.

While you're at it, leave the venv

    deactivate

## Some additional notes on the filter:
When you have the filter active and checkout a normal branch, it will checkout AND strip the outputs in git’s mind (not the HEAD version though… confusing)

When you have the filter active and leave a branch that has outputs, it will generate changes, thereby not allowing you to checkout without committing changes

You can turn it on and off with the `nbstripout --install`, `nbstripout --uninstall` commands, as long as the attributes file has nothing else in it
This is the easiest way to check: `cat .git/info/attributes`
You can also check: `nbstripout --is-installed && echo $?`
If it returns 0, then it IS installed
