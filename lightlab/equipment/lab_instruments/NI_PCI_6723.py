from . import VISAInstrumentDriver
from lightlab.equipment.abstract_drivers import MultiModalSource, MultiChannelSource
from lightlab.equipment.visa_bases.driver_base import TCPSocketConnection
from lightlab.laboratory.instruments import CurrentSource

import numpy as np
import time
import socket
from lightlab.util.io import RangeError
from lightlab import visalogger as logger


class NI_PCI_6723(VISAInstrumentDriver, MultiModalSource, MultiChannelSource):
    """ Primarily employs abstract classes. Follow the bases for more information

        :class:`~lightlab.equipment.lab_instruments.VISAInstrumentDriver`
        provides communication to the board

        :class:`~lightlab.equipment.abstract_drivers.MultiModalSource`
        provides unit support and range checking

        :py:class:`~lightlab.equipment.abstract_drivers.MultiChannelSource`
        provides **notion of state** (stateDict) and channel support

        Usage: :ref:`/ipynbs/Hardware/CurrentSources-NI.ipynb`

    """

    instrument_category = CurrentSource

    # The natural unit is volts so don't confuse
    supportedModes = MultiModalSource.supportedModes - {"baseunit"}
    baseUnitBounds = [0, 10]
    baseToVoltCoef = 1
    v2maCoef = 4  # current (milliamps) = v2maCoef * voltage (volts)

    exceptOnRangeError = True  # If False, it will constrain it and print a warning
    maxChannel = 32  # number of dimensions that the current sources are expecting
    targetPort = 16022  # TCPIP server port; charge of an electron (Coulombs)
    waitMsOnWrite = 500  # Time to settle after tuning

    _tcpsocket = None
    MAGIC_TIMEOUT = 30

    def __init__(
        self, name="The current source", address=None, useChans=None, **kwargs
    ):
        kwargs["tempSess"] = kwargs.get("tempSess", True)
        if "elChans" in kwargs.keys():
            useChans = kwargs.pop("elChans")
        self.reinstantiate_session(address, kwargs["tempSess"])
        MultiChannelSource.__init__(self, useChans=useChans)

    def reinstantiate_session(self, address, tempSess):
        if address is not None:
            # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
            address_array = address.split("::")
            self._tcpsocket = TCPSocketConnection(
                ip_address=address_array[1],
                port=int(address_array[2]),
                timeout=self.MAGIC_TIMEOUT,
                termination="\r\n",
            )

    def startup(self):
        self.off()

    def open(self):
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        try:
            self._tcpsocket.connect()
        except socket.error:
            self._tcpsocket.disconnect()
            raise

    def close(self):
        self._tcpsocket.disconnect()

    def _query(self, queryStr):
        with self._tcpsocket.connected() as s:
            s.send(queryStr)

            i = 0
            old_timeout = s.timeout
            s.timeout = self.MAGIC_TIMEOUT
            received_msg = ""
            while i < 1024:  # avoid infinite loop
                recv_str = s.recv(1024)
                received_msg += recv_str
                if recv_str.endswith("\n"):
                    break
                s.timeout = 1
                i += 1
            s.timeout = old_timeout
            return received_msg.rstrip()

    def query(self, queryStr, expected_talker=None):
        ret = self._query(queryStr)
        if expected_talker is not None:
            if ret != expected_talker:
                log_function = logger.warning
            else:
                log_function = logger.debug
            log_function(
                "'%s' returned '%s', expected '%s'", queryStr, ret, str(expected_talker)
            )
        else:
            logger.debug("'%s' returned '%s'", queryStr, ret)
        return ret

    def write(self, writeStr, expected_talker=None):
        """ The APEX does not deal with write; you have to query to clear the buffer """
        self.query(writeStr, expected_talker)
        time.sleep(0.2)

    def instrID(self):
        r""" There is no "\*IDN?" command. Instead, test if it is alive,
            and then return a reasonable string
        """
        self.tcpTest()
        return "Current Source"

    def tcpTest(self, num=2):
        print("x = " + str(num))
        # self.open()
        ret = self.query("Test: " + str(num) + " " + str(num + 0.5))
        # self.close()
        retNum = [0] * len(ret.split())
        for i, s in enumerate(ret.split(" ")):
            retNum[i] = float(s) + 0.01
        print("[x+1, x+1.5] = " + str(retNum))

    def setChannelTuning(
        self, chanValDict, mode, waitTime=None
    ):  # pylint: disable=arguments-differ
        oldState = self.getChannelTuning(mode)
        # Check range and convert to base units
        chanBaseDict = dict()
        for ch, val in chanValDict.items():
            try:
                enforced = self.enforceRange(val, mode)
            except RangeError as err:
                self.off()
                raise err
            chanBaseDict[ch] = self.val2baseUnit(enforced, mode)

        # Change the state
        super().setChannelTuning(chanBaseDict)

        # Was there a change
        if not oldState == self.getChannelTuning(mode):
            self.sendToHardware(waitTime)
        else:
            self.wake()

    def getChannelTuning(self, mode):  # pylint: disable=arguments-differ
        baseDict = super().getChannelTuning()
        return self.baseUnit2val(baseDict, mode)

    def off(self):  # pylint: disable=arguments-differ
        self.setChannelTuning(dict([ch, 0] for ch in self.stateDict.keys()), "volt")

    def wake(self):
        """ Don't change the value but make sure it doesn't go to sleep after inactivity.

            Good for long sweeps
        """
        self.sendToHardware(waitTime=0)

    def sendToHardware(self, waitTime=None):
        """Updates current drivers with the present value of tuneState
        Converts it to a raw voltage, depending on the mode of the driver

            Args:

        """
        # First get a complete array in terms of voltage needed by the NI-PCI card
        fullVoltageState = np.zeros(self.maxChannel)
        for ch, baseVal in self.stateDict.items():
            fullVoltageState[ch] = self.baseUnit2val(baseVal, "volt")
        # Then write a TCPIP packet
        writeStr = "Set:"
        for v in fullVoltageState:
            writeStr += " " + str(v)
        # self.open()
        retStr = self.query(writeStr)
        # self.close()
        if retStr != "ACK":
            raise RuntimeError('Current driver is angry. Message: "' + retStr + '"')

        if waitTime is None:
            waitTime = self.waitMsOnWrite
        logger.debug("Current settling for %s ms", waitTime)
        time.sleep(waitTime / 1000)
