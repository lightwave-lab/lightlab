'''
    Resolves several directories as follows.
    These can be overridden after import if desired.

        1. projectDir
            The git repo of the current project

        2. dataHome = projectDir/data
            Where all your data is saved.

        3. fileDir = dataHome
            Where all the save/load functions will look.
            Usually this is set differently from notebook to notebook.

        4. monitorDir = projectDir/progress-monitor
            Where html for sweep progress monitoring will be written
            by ``ProgressWriter``.

        5. lightlabDevelopmentDir
            The path to a source directory of ``lightlab`` for development.
            It is found through the ".pathtolightlab" file.
            This is currently unused.
'''
import os
from pathlib import Path
import lightlab.util.gitpath as gitpath
from lightlab import logger

try:
    projectDir = Path(gitpath.root())
except IOError as e:
    # git repo not found, logging that.
    logger.warning(e)
    projectDir = Path(os.getcwd())
    logger.warning("Default projectDir='{}'".format(projectDir))
if not os.access(projectDir, 7):
    logger.warning("Cannot write to this projectDir({}).".format(projectDir))

# Data files
dataHome = projectDir / 'data'
fileDir = dataHome  # Set this in your experiment

# Monitor files
monitorDir = projectDir / 'progress-monitor'

# Maybe you are using the lightlab package from elsewhere
try:
    with open(projectDir / '.pathtolightlab') as fx:
        lightlabDevelopmentDir = Path(fx.readline())
except IOError:
    lightlabDevelopmentDir = projectDir
