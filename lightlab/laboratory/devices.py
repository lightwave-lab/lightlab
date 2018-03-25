'''
This module contains virtual tokens for optical and electronic devices.
'''
from lightlab.laboratory import Node
import lightlab.laboratory.state as labstate


#fixme: add device equality function
class Device(Node):
    name = None
    ports = None
    __bench = None

    def __init__(self, name, **kwargs):
        self.name = name
        self.ports = kwargs.pop("ports", dict())
        self.__bench = kwargs.pop("bench", None)
        super().__init__(**kwargs)

    @property
    def bench(self):
        if self.__bench is None:
            self.__bench = labstate.lab.findBenchFromDevice(self)
        return self.__bench

    @bench.setter
    def bench(self, new_bench):
        if self.bench is not None:
            self.bench.removeDevice(self)
        if new_bench is not None:
            new_bench.addDevice(self)
        self.__bench = new_bench

    def __str__(self):
        return "Device {}".format(self.name)

    def display(self):
        # Print benches table
        lines = ["{}".format(self)]
        lines.append("Bench: {}".format(self.bench))
        lines.append("=====")
        lines.append("Ports")
        lines.append("=====")
        if len(self.ports) > 0:
            lines.extend(["   {}".format(str(port)) for port in self.ports])
        else:
            lines.append("   No ports.")
        lines.append("***")
        print("\n".join(lines))
