''' Makes complex inheritance easier to read if there is an argument error.


    NOT RECOMMENDED FOR USE
        It ends up making it more complicated after all
'''

import inspect
from functools import wraps, update_wrapper
import re


def signatureRepr(aMethod, verbose=False):
    ''' Returns a pretty string showing required and optional arguments of a method or function
    '''
    paramDict = inspect.signature(aMethod).parameters
    selfStr = []
    require = []
    option = []
    for param in paramDict.values():
        if param.name == 'self':
            selfStr.append('self')
        elif param.kind == param.POSITIONAL_OR_KEYWORD:
            if param.default is param.empty:
                require.append(param.name)
            else:
                option.append((param.name, param.default))
    if verbose:
        lines = ['>>> ' + aMethod.__qualname__ + ' >>>']
        for req in require:
            lines.append('- Required: ' + req)
        for opt in option:
            lines.append('-- Optional: ' + opt[0] + '=' + str(opt[1]))
        sss = '\n'.join(lines)
    else:
        allArgs = selfStr + require + [op[0] + '=' + str(op[1]) for op in option]
        sss = aMethod.__qualname__
        sss += '(' + ', '.join(allArgs) + ')'
    return sss

typeErrREs = [re.compile(errSt) for errSt in {'positional argument', 'unexpected keyword argument'}]

def safeInherit(func):
    ''' Handles argument errors coming from a function call. Adds signature to error if so
    '''
    @wraps(func)
    def inheritanceWrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except TypeError as err:
            # Is this the kind of TypeError we are looking for? If so, convert it to a friendly
            if any(errREX.search(str(err)) for errREX in typeErrREs):
                newm = err.args[0] + '\n' + signatureRepr(func, verbose=True)
                err.args = (newm,) + err.args[1:]
                raise err
            else: # No it is not. It is something else
                raise
        return result
    return inheritanceWrapper


class MetaInheritanceBase(type):
    ''' Decorates every callable method of the class with an exception handler
    '''
    def __new__(metacls, name, bases, namespace, **kwds):
        for attr, val in namespace.items():
            if callable(val) and not attr[:2] == '__':
                namespace[attr] = safeInherit(val)
        return type.__new__(metacls, name, bases, dict(namespace))


class InheritanceBase(metaclass=MetaInheritanceBase):
    ''' Subclasses of InheritanceBase will get the metaclass with decorators

        It should be inherited instead of ``object`` for base classes

        All direct children should init super::

            def __init__(self, myA, **kwargs):
                self.something = myA
                super().__init__(**kwargs)

        The child subclass might have a method ``foo(self, alice)`` -- no **kwargs
        The grandchild version of foo must have **kwargs and, at some point, call super().foo(**kwargs)
    '''
    def __init__(self, **kwargs):
        if kwargs:
            raise TypeError('unexpected keyword argument')




