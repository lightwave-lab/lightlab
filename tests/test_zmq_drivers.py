''' Creates local zmq client and servers and tests functionality'''

import pytest
from mock import patch
from lightlab.equipment import lab_instruments
from lightlab.equipment.lab_instruments import VISAInstrumentDriver
import inspect

# TODO