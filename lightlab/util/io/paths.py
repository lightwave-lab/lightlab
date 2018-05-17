'''
    Resolves several directories as follows.
    These can be overridden after import if desired.

        1. ``projectDir``
            The git repo of the file that first imported ``io``

        2. ``dataHome`` = (default) ``projectDir / "data"``
            Where all your data is saved.

        3. ``fileDir`` = (default) ``dataHome``
            Where all the save/load functions will look.
            Usually this is set differently from notebook to notebook.

        4. ``monitorDir`` = (default) ``projectDir / "progress-monitor"``
            Where html for sweep progress monitoring will be written
            by ``ProgressWriter``.

        5. ``lightlabDevelopmentDir``
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
    logger.warning("io.projectDir is typically set to the root of the"
                   " git repository containing this file. Because none"
                   " was found, projectDir was set to "
                   f"'{projectDir}'. To remove this"
                   f" warning, please create a git repository in '{projectDir}'"
                   " or any of its parent directories.\n"
                   "------------------------------\n"
                   "To create a git repository in a folder, run the following commands:\n\n"
                   "$ cd folder/\n"
                   "$ git init .")
if not os.access(projectDir, 7):
    logger.warning("You do not have permission to save or overwrite "
                   f"files in '{projectDir}'. If you need to save files, contact "
                   f"'{projectDir.owner()}' or an administrator.")


# Data files
dataHome = projectDir / 'data'
# fileDir = dataHome  # Set this in your experiment

# class FileDirHelper(object):
#     def __init__(self):
#         self.__fileDir = dataHome

#     def __get__(self, instance, owner):
#         return self.__fileDir

#     def __set__(self, instance, newDir):
#         self.__fileDir = newDir

#     def __delete__(self, instance):
#         del self.__fileDir

# fileDir = FileDirHelper()

# Monitor files
monitorDir = projectDir / 'progress-monitor'

# Maybe you are using the lightlab package from elsewhere
try:
    with open(projectDir / '.pathtolightlab') as fx:
        lightlabDevelopmentDir = Path(fx.readline())
except IOError:
    lightlabDevelopmentDir = projectDir
