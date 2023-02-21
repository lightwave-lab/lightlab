''' Argument sanitizing and very basic array operations '''
import numpy as np

# Argument sanitizing


def verifyListOfType(arg, checkType):
    ''' Checks to see if the argument is a list or a single object of the checkType
    Returns a list, even if it is length one
    If arg is None, it returns None
    '''
    if arg is None:
        return None
    if isinstance(arg, checkType):
        arg = [arg]
    if isinstance(arg, (list, tuple)):
        for a in arg:
            if not isinstance(a, checkType):
                raise Exception('Incorrect type, expecting ' + str(checkType) +
                                '. Got ' + str(type(a)))
    return arg


def argFlatten(*argLists, typs=(list, tuple, set)):
    ''' Takes a combination of multiple arguments and flattens the ones of type typs.
        None arguments are ignored, no error.

        Args:
            *argLists: multiple arguments that could be lists or tuples
            typs (tuple): types of things to flatten

        Returns:
            (tuple)

        It goes like this::

            dUtil.argFlatten()                                        # == ()
            dUtil.argFlatten(1)                                       # == (1,)
            dUtil.argFlatten((3, 4))                                  # == (3, 4)
            dUtil.argFlatten(1, (3, 4), np.zeros(2))                  # == (1, 3, 4, ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2))                  # == (1, 3, 4, ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2), typs=tuple)      # == (1, [3, 4], ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2), typs=np.ndarray) # == (1, [3, 4], 0., 0.)
    '''
    flatList = []
    for arg in argLists:
        if arg is None:
            continue
        if not isinstance(arg, typs):
            arg = [arg]
        flatList.extend(list(arg))
    return tuple(flatList)


MANGLE_LEN = 256  # magic constant from compile.c


def mangle(name, klass):
    ''' Sanitizes attribute names that might be "hidden,"
        denoted by leading '__'. In :py:class:`~lightlab.laboratory.Hashable` objects,
        attributes with this kind of name can only be class attributes.

        See :py:mod:`~tests.test_instrument_overloading` for user-side implications.

        Behavior::

            mangle('a', 'B') == 'a'
            mangle('_a', 'B') == '_a'
            mangle('__a__', 'B') == '__a__'
            mangle('__a', 'B') == '_B__a'
            mangle('__a', '_B') == '_B__a'
    '''
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        klass = klass[:MANGLE_LEN - tlen]

    return "_%s%s" % (klass, name)


# Simple common array operations

def rms(diffArr, axis=0):
    return np.sqrt(np.mean(diffArr ** 2, axis=axis))


def minmax(arr):
    ''' Returns a list of [min and max] of the array '''
    return np.array([np.min(arr), np.max(arr)])
