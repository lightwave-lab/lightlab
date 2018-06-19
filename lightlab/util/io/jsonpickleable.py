''' Objects that can be serialized in a (sort of) human readable json format

    Tested in :mod:`tests.test_JSONpickleable`.
'''
import dill
import jsonpickle
import jsonpickle.ext.numpy as jsonpickle_numpy
jsonpickle_numpy.register_handlers()

from lightlab import logger
from lightlab.laboratory import Hashable
from .saveload import _endingWith, _makeFileExist
from . import _getFileDir


class HardwareReference(object):
    ''' Spoofs an instrument
    '''

    def __init__(self, klassname):
        self.klassname = klassname

    def open(self):
        raise TypeError(f'This object is placeholder for a real '
                        f'{self.klassname}. '
                        'You probably loaded this via JSON.')


class JSONpickleable(Hashable):
    ''' Produces human readable json files. Inherits _toJSON from Hashable
        Automatically strips attributes beginning with __.

        Attributes:
            notPickled (set): names of attributes that will be guaranteed to exist in instances.
                They will not go into the pickled string.
                Good for references to things like hardware instruments that you should re-init when reloading.

        See the test_JSONpickleable for much more detail

        What is not pickled?
            #. attributes with names in ``notPickled``
            #. attributes starting with __
            #. VISAObjects: they are replaced with a placeholder HardwareReference
            #. bound methods (not checked, will error if you try)

        What functions can be pickled
            #. module-level, such as np.linspace
            #. lambdas

        Todo:
            This should support unbound methods

            Args:
                filepath (str/Path): path string to file to save to
    '''
    notPickled = set()

    def __getstate__(self):
        '''
        This method removes all variables in ``notPickled`` during
        serialization.
        '''
        state = super().__getstate__()
        allNotPickled = self.notPickled
        for base in type(self).mro():
            try:
                theirNotPickled = base.notPickled
                allNotPickled = allNotPickled.union(theirNotPickled)
            except AttributeError:
                pass

        keys_to_delete = set()
        for key, val in state.copy().items():
            if isinstance(key, str):

                # 1. explicit removals
                if key in allNotPickled:
                    keys_to_delete.add(key)

                # 2. hardware placeholders
                elif (val.__class__.__name__ == 'VISAObject' or
                      any(base.__name__ == 'VISAObject' for base in val.__class__.mro())):
                    klassname = val.__class__.__name__
                    logger.warning('Not pickling %s = %s.', key, klassname)
                    state[key] = HardwareReference('Reference to a ' + klassname)

                # 3. functions that are not available in modules - saves the code text
                elif jsonpickle.util.is_function(val) and not jsonpickle.util.is_module_function(val):
                    state[key + '_dilled'] = dill.dumps(val)
                    keys_to_delete.add(key)

                # 4. double underscore attributes have already been removed
        for key in keys_to_delete:
            del state[key]
        return state

    def __setstate__(self, state):
        for key, val in state.copy().items():
            if isinstance(val, HardwareReference):
                state[key] = None
            elif key[-7:] == '_dilled':
                state[key[:-7]] = dill.loads(val)
                del state[key]

        for a in self.notPickled:
            state[a] = None

        super().__setstate__(state)

    @classmethod
    def _fromJSONcheck(cls, json_string):
        ''' Converts to object which is returned

            Also checks if the class is the right type and its attributes are correct
        '''
        json_state = jsonpickle.json.decode(json_string)
        context = jsonpickle.unpickler.Unpickler(backend=jsonpickle.json, safe=True, keys=True)
        try:
            restored_object = context.restore(json_state, reset=True)
        except (TypeError, AttributeError) as err:
            newm = err.args[
                0] + '\n' + 'This is that strange jsonpickle error trying to get aDict.__name__. You might be trying to pickle a function.'
            err.args = (newm,) + err.args[1:]
            raise

        if not isinstance(restored_object, cls):  # This is likely to happen if lightlab has been reloaded
            if type(restored_object).__name__ != cls.__name__:  # This is not ok
                raise TypeError('Loaded class is different than intended.\n' +
                                'Got {}, needed {}.'.format(type(restored_object).__name__, cls.__name__))

        for a in cls.notPickled:
            setattr(restored_object, a, None)

        for key, val in restored_object.__dict__.copy().items():
            if isinstance(val, HardwareReference):
                setattr(restored_object, key, None)
            elif key[-7:] == '_dilled':
                setattr(restored_object, key[:-7], dill.loads(val))
                delattr(restored_object, key)

        return restored_object

    def copy(self):
        ''' This will throw out hardware references and anything starting with __

            Good test for what will be saved
        '''
        return self._fromJSONcheck(self._toJSON())

    def save(self, filename):
        rp = _makeFileExist(_endingWith(filename, '.json'))
        with open(rp, 'w') as f:
            f.write(self._toJSON())

    @classmethod
    def load(cls, filename):
        rp = _getFileDir(_endingWith(filename, '.json'))
        with open(rp, 'r') as f:
            frozen = f.read()
        return cls._fromJSONcheck(frozen)

    def __str__(self):
        return self._toJSON()
