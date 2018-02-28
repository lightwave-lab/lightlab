import pkgutil
import lightlab

package = lightlab
modules = list()
for _, modname, _ in pkgutil.walk_packages(path=package.__path__,
                                           prefix=package.__name__ + '.',
                                           onerror=lambda x: None):
    modules.append(modname)
