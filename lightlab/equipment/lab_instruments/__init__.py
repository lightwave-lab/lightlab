from ..visa_bases import VISAInstrumentDriver

# This imports all of the modules in this folder
# As well as all their member classes that are VISAInstrumentDriver
import importlib
import pkgutil


class BuggyHardware(Exception):
    ''' Not all instruments behave as they are supposed to.
        This might be lab specific. atait is not sure exactly how to deal with that.
    '''
    pass


for _, modname, _ in pkgutil.walk_packages(path=__path__,  # noqa
                                           prefix=__name__ + '.'):
    _temp = importlib.import_module(modname)
    for k, v in _temp.__dict__.items():
        if k[0] != '_' and type(v) is not type:
            try:
                mro = v.mro()
            except AttributeError:
                continue
            if VISAInstrumentDriver in mro:
                globals()[k] = v
