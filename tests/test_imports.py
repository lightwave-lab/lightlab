'''Import all instrument module by name'''
import pkgutil
import lightlab
import pytest
import importlib

package = lightlab
modules = list()
for _, modname, _ in pkgutil.walk_packages(path=package.__path__,
                                           prefix=package.__name__ + '.',
                                           onerror=lambda x: None):
    modules.append(modname)


@pytest.mark.parametrize("modname", modules)
def test_import(modname):
    """Simply imports the module"""
    importlib.import_module(modname)


def test_visa_driver_package():
    from lightlab.equipment.lab_instruments import Tektronix_DSA8300_Oscope
    try:
        from lightlab.equipment.lab_instruments.visa_drivers.Tektronix_DSA8300_Oscope import Tektronix_DSA8300_Oscope
        from lightlab.equipment.lab_instruments.visa_drivers import Tektronix_DSA8300_Oscope
    except ModuleNotFoundError:
        print('\n\nIt looks like the reorganization of visa_drivers is happening.')
        print('Please modify test_imports.py')

