"""
The laboratory module facilitates the organization and documentation
of instruments, experiments and devices. The objects defined here are
designed to be "hashable", i.e., easy to store and share.
"""

import jsonpickle
from collections import MutableSequence, Mapping

__all__ = ["Node"]


class FrozenDict(Mapping):
    """Don't forget the docstrings!!"""

    def __init__(self, data):
        self._d = data

    def __iter__(self):
        return iter(self._d)

    def __len__(self):
        return len(self._d)

    def __getitem__(self, key):
        return self._d[key]

    def __setitem__(self, key, value):
        raise RuntimeError("attempting to change read-only list")

    def __delitem__(self, key):
        raise RuntimeError("attempting to delete item from read-only list")


class Hashable(object):
    """
    Hashable class to be used with jsonpickle's module.
    Rationale: This is a fancy way to do ``self.__dict__ == other.__dict__``.
    That line fails when there are circular references within the __dict__.
    ``Hashable`` solves that.


    By default, every key-value in the initializer will become instance
    variables. E.g. ``Hashable(a=1).a == 1``

    No instance variables starting with "__" will be serialized.
    """
    context = jsonpickle.pickler.Pickler(
        unpicklable=True, warn=True, keys=True)

    def __eq__(self, other):
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

        - a :class:`~lightlab.laboratory.devices.Device`
        - a :class:`~lightlab.laboratory.instruments.bases.Host`
        - a :class:`~lightlab.laboratory.instruments.bases.Bench`
        - an :class:`~lightlab.laboratory.instruments.bases.Instrument`

    """

    bench = None

    def placeBench(self, new_bench):  # TODO Deprecate
        self.bench = new_bench


def typed_property(type_obj, name):
    """ Property that only accepts instances of a class and
    stores the contents in self.name
    """

    def fget(self):
        return getattr(self, name)

    def fset(self, value):
        if value is None or isinstance(value, type_obj):
            return setattr(self, name, value)
        else:
            raise TypeError(f"{value} is not instance of {type_obj}")

    def fdel(self):
        return setattr(self, name, None)

    doc = f"Property that only accepts {type_obj} values"

    return property(fget, fset, fdel, doc)


# https://stackoverflow.com/questions/3487434/overriding-append-method-after-inheriting-from-a-python-list
class NamedList(MutableSequence, Hashable):
    """
    Object list that enforces that there are only one object.name in the list.

    """

    read_only = False

    def __init__(self, *args, read_only=False):  # pylint: disable=super-init-not-called
        self.list = list()
        self.extend(list(args))
        self.read_only = read_only

    @property
    def dict(self):
        return FrozenDict({i.name: i for i in self})

    @property
    def values(self):
        return lambda: iter(self.list)

    @property
    def keys(self):
        return lambda: iter([i.name for i in self])

    def items(self):
        return self.dict.items()

    def check(self, value):
        if not hasattr(value, 'name'):
            raise TypeError(f"{type(value)} does not have name.")

    def check_presence(self, name):
        matching_idxs = [idx for idx, elem in enumerate(
            self) if elem.name == name]
        return matching_idxs

    def __len__(self):
        return len(self.list)

    def __getitem__(self, i):
        if isinstance(i, str):
            return self.dict[i]
        return self.list[i]

    def __delitem__(self, i):
        if self.read_only:
            raise RuntimeError("attempting to delete item from read-only list")
        if isinstance(i, str):
            matching_idxs = [idx for idx,
                             elem in enumerate(self) if elem.name == i]
            for idx in matching_idxs:
                del self.list[idx]
        else:
            del self.list[i]

    def __setitem__(self, i, v):
        if self.read_only:
            raise RuntimeError("attempting to change read-only list")
        self.check(v)
        if isinstance(i, str):
            if i in self.dict.keys():
                matching_idxs = [idx for idx,
                                 elem in enumerate(self) if elem.name == i]
                assert len(matching_idxs) == 1
                idx = matching_idxs[0]
                self.list[idx] = v  # update current entry
            else:
                if i != v.name:
                    # Renaming instrument to conform to the dict's key
                    # named_list['name1'] = Instrument('name2')
                    # Instrument will be renamed to name1 prior to insertion
                    v.name = i

                # special case when v is already in the list, in
                # which case one must do nothing.
                if v not in self.list:
                    self.list.append(v)
        else:
            self.list[i] = v

    def insert(self, index, value):
        # This inserts a new element after index.
        # Note: not the same as __setitem__, which replaces the value
        # in an index.
        # Append will call this method with self.insert(len(self), value)
        if self.read_only:
            raise RuntimeError("attempting to insert item to read-only list")
        else:
            self.check(value)
            conflicts = self.check_presence(value.name)
            if len(conflicts) > 0:
                raise RuntimeError(f"{value.name} already exists in list[{conflicts[0]}].")
            if isinstance(index, str):
                # this code should normally never be run. but just in case,
                # it should add value right before index's position
                index_list = self.check_presence(index)
                assert len(index_list) <= 1
                if len(index_list) == 1:
                    index = index_list[0]
                    self.list.insert(index, value)
                else:
                    self[value.name] = value
            else:
                self.list.insert(index, value)

    def __str__(self):
        return str(self.list)


class TypedList(NamedList):
    """
    Object list that enforces that there are only one object.name in
    the list and that they belong to a certain class (obj_type).
    """

    def __init__(self, obj_type, *args, read_only=False, **kwargs):
        self.obj_type = obj_type
        super().__init__(*args, read_only=read_only, **kwargs)

    def check(self, value):
        if not isinstance(value, self.obj_type):
            raise TypeError(f"{value} is not an instance of {self.obj_type}")
        return super().check(value)
