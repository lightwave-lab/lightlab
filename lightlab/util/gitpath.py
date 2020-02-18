"""All credit goes to https://github.com/MaxNoe/python-gitpath"""

from subprocess import check_output, CalledProcessError
from functools import lru_cache
import os.path


@lru_cache(maxsize=1)
def root():
    ''' returns the absolute path of the repository root '''
    try:
        base = check_output(['git', 'rev-parse', '--show-toplevel'])
    except CalledProcessError:
        raise IOError(f"'{os.getcwd()}' is not a git repository")
    return base.decode('utf-8').strip()


def abspath(relpath):
    ''' returns the absolute path for a path given relative to the root of
    the git repository
    '''
    return os.path.join(root(), relpath)
