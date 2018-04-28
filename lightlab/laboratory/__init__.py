import jsonpickle
from collections import MutableSequence

__all__ = ["Node"]


class Hashable(object):
    """
    Hashable class to be used with jsonpickle's module. No instance
    variables starting with "__" will be serialized.
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

    def placeBench(self, new_bench):
        self.bench = new_bench


def typed_property(type_obj, name):
    """ Property that only accepts instances of a class and
    stores the contents in self.name"""
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

    def __init__(self, *args):
        self.list = list()
        self.extend(list(args))

    @property
    def dict(self):
        return {i.name: i for i in self}

    @property
    def values(self):
        return lambda: iter(self.list)

    @property
    def keys(self):
        return lambda: iter([i.name for i in self])

    def check(self, v):
        if not hasattr(v, 'name'):
            raise TypeError(f"{type(v)} does not have name.")

    def __len__(self):
        return len(self.list)

    def __getitem__(self, i):
        if isinstance(i, str):
            return self.dict[i]
        return self.list[i]

    def __delitem__(self, i):
        if isinstance(i, str):
            matching_idxs = [idx for idx, elem in enumerate(self) if elem.name == i]
            for idx in matching_idxs:
                del self.list[idx]
        else:
            del self.list[i]

    def __setitem__(self, i, v):
        self.check(v)
        if isinstance(i, str):
            if i in self.dict.keys():
                matching_idxs = [idx for idx, elem in enumerate(self) if elem.name == i]
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

    def insert(self, i, v):
        self.check(v)
        name_list = [i.name for i in self]
        if v.name in name_list:
            raise RuntimeError(f"{v.name} already exists in list {name_list}.")
        if isinstance(i, str):
            del self[i]
            self[i] = v
        self.list.insert(i, v)

    def __str__(self):
        return str(self.list)


class TypedList(NamedList):
    """
    Object list that enforces that there are only one object.name in
    the list and that they belong to a certain class (obj_type).
    """

    def __init__(self, obj_type, *args):
        self.obj_type = obj_type
        super().__init__(*args)

    def check(self, v):
        if not isinstance(v, self.obj_type):
            raise TypeError(f"{v} is not an instance of {self.obj_type}")
        return super().check(v)
