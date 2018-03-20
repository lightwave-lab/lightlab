from ..visa_bases import VISAInstrumentDriver

# This imports all of the modules in this folder
# As well as all their member classes that are VISAInstrumentDriver
import importlib
import pkgutil

for _, modname, _ in pkgutil.walk_packages(path=__path__,
                                           prefix=__name__ + '.'):
    _temp = importlib.import_module(modname)
    for k, v in _temp.__dict__.items():
        try:
            mro = v.mro()
        except AttributeError:
            continue
        if VISAInstrumentDriver in mro:
            globals()[k] = v
