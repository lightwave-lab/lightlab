"""
The laboratory module facilitates the organization and documentation
of instruments, experiments and devices. The objects defined here are
designed to be "hashable", i.e., easy to store and share.
"""

import jsonpickle

__all__ = ["Node"]


class Hashable(object):
    """
    Hashable class to be used with jsonpickle's module.
    No instance variables starting with "__" will be serialized.

    By default, every key-value in the initializer will become instance
    variables. E.g. ``Hashable(a=1).a == 1``

    """
    context = jsonpickle.pickler.Pickler(unpicklable=True, warn=True, keys=True)

    def __eq__(self, other):

        # Original idea:
        #
        # if self.__class__ != other.__class__:
        #     return False
        # else:
        #     return self.__dict__ == other.__dict__
        # It doesn't work because of cyclical references inside __dict__

        jsonpickle.set_encoder_options('json', sort_keys=True)
        json_self = self.context.flatten(self, reset=True)
        json_other = self.context.flatten(other, reset=True)
        return json_self == json_other

    def __hash__(self):
        jsonpickle.set_encoder_options('json', sort_keys=True)
        json_self = self.context.flatten(self, reset=True)
        return hash(jsonpickle.json.encode(json_self))

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        super().__init__()

    def __getstate__(self):
        '''
        This method removes all variables starting with "__" during
        serialization. Variables named as such are actually stored
        different in self.__dict__. Check PEP 8.
        '''
        klassnames = []
        klassnames.append(self.__class__.__name__.lstrip('_'))

        for base in self.__class__.mro():
            klassnames.append(base.__name__.lstrip('_'))

        state = self.__dict__.copy()
        keys_to_delete = set()
        for key in state.keys():
            if isinstance(key, str):
                for klassname in klassnames:
                    if key.startswith("_{}__".format(klassname)):
                        keys_to_delete.add(key)
                    if key.startswith("__"):
                        keys_to_delete.add(key)
        for key in keys_to_delete:
            del state[key]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _toJSON(self):
        context = jsonpickle.pickler.Pickler(unpicklable=True, warn=True)
        json_state = context.flatten(self, reset=True)
        jsonpickle.set_encoder_options('json', sort_keys=True, indent=4)
        return jsonpickle.json.encode(json_state)


class Node(Hashable):
    """
    Node is a token of an object that exists in a laboratory.
    For example, subclasses are:

        - a :py:class:`~lightlab.laboratory.devices.Device`
        - a :py:class:`~lightlab.laboratory.instruments.bases.Host`
        - a :py:class:`~lightlab.laboratory.instruments.bases.Bench`
        - an :py:class:`~lightlab.laboratory.instruments.bases.Instrument`

    """
    pass
