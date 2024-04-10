""" Driver class for Keithley 2606B.

The following programming example illustrates the setup and command
sequence of a basic source-measure procedure with the following parameters:
• Source function and range: voltage, autorange
• Source output level: 5 V
• Current compliance limit: 10 mA
• Measure function and range: current, 10 mA

-- Restore 2606B defaults.
smua.reset()
-- Select voltage source function.
smua.source.func = smua.OUTPUT_DCVOLTS
-- Set source range to auto.
smua.source.autorangev = smua.AUTORANGE_ON
-- Set voltage source to 5 V.
smua.source.levelv = 5
-- Set current limit to 10 mA.
smua.source.limiti = 10e-3
-- Set current range to 10 mA.
smua.measure.rangei = 10e-3
-- Turn on output.
smua.source.output = smua.OUTPUT_ON
-- Print and place the current reading in the reading buffer.
print(smua.measure.i(smua.nvbuffer1))
-- Turn off output.
smua.source.output = smua.OUTPUT_OFF

"""
from . import VISAInstrumentDriver
from lightlab.equipment.visa_bases.driver_base import TCPSocketConnection
from lightlab.laboratory.instruments import Keithley

import socket
import numpy as np
import time
from lightlab import logger


class Keithley_2606B_SMU(VISAInstrumentDriver):
    """ Keithley 2606B 4x SMU instrument driver

        `Manual: <https://download.tek.com/manual/2606B-901-01B_May_2018_Ref_Man.pdf>`__

        Usage: Unavailable

        Capable of sourcing current and measuring voltage, as a Source Measurement Unit.
    """

    instrument_category = Keithley

    tsp_node = None
    channel = None

    MAGIC_TIMEOUT = 10
    _latestCurrentVal = 0
    _latestVoltageVal = 0
    currStep = 0.1e-3
    voltStep = 0.3
    rampStepTime = 0.05  # in seconds.

    def __init__(
        self,
        name=None,
        address=None,
        tsp_node: int = None,
        channel: str = None,
        **visa_kwargs
    ):
        """
        Args:
            tsp_node: Number from 1 to 64 corresponding to the
                pre-configured TSP node number assigned to each module.
            channel: 'A' or 'B'
        """

        if channel is None:
            logger.warning("Forgot to select a channel: either 'A', or 'B'")
        elif channel not in ("A", "B", "a", "b"):
            raise RuntimeError("Select a channel: either 'A', or 'B'")
        else:
            self.channel = channel.upper()

        if tsp_node is None:
            logger.warning("Forgot to specify a tsp_node integer number between 1 and 64.")
        elif not isinstance(tsp_node, int):
            raise RuntimeError(
                "Please specify a tsp_node integer number between 1 and 64."
            )
        elif not 1 <= tsp_node <= 64:
            raise RuntimeError("Invalid tsp_node. Valid numbers between 1 and 64.")

        self.tsp_node = tsp_node

        visa_kwargs["tempSess"] = visa_kwargs.pop("tempSess", True)
        VISAInstrumentDriver.__init__(self, name=name, address=address, **visa_kwargs)
        self.reinstantiate_session(address, visa_kwargs["tempSess"])

    # BEGIN TCPSOCKET METHODS
    def reinstantiate_session(self, address, tempSess):
        if address is not None:
            # should be something like ['TCPIP0', 'xxx.xxx.xxx.xxx', '6501', 'SOCKET']
            address_array = address.split("::")
            self._tcpsocket = TCPSocketConnection(
                ip_address=address_array[1],
                port=int(address_array[2]),
                timeout=self.MAGIC_TIMEOUT,
            )

    def open(self):
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        try:
            self._tcpsocket.connect()
            super().open()
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

    def write(self, writeStr):
        with self._tcpsocket.connected() as s:
            logger.debug("Sending '%s'", writeStr)
            s.send(writeStr)
        time.sleep(0.05)

    # END TCPSOCKET METHODS

    @property
    def smu_string(self):
        if self.channel.upper() == "A":
            return "smua"
        elif self.channel.upper() == "B":
            return "smub"
        else:
            raise RuntimeError(
                "Unexpected channel: {}, should be 'A' or 'B'".format(self.channel)
            )

    @property
    def smu_full_string(self):
        return "node[{N}].{smuX}".format(N=self.tsp_node, smuX=self.smu_string)

    def query_print(self, query_string, expected_talker=None):
        time.sleep(0.01)
        query_string = "print(" + query_string + ")"
        return self.query(query_string, expected_talker=expected_talker)

    def smu_reset(self):
        self.write(
            "node[{tsp_node}].{smu_ch}.reset()".format(
                tsp_node=self.tsp_node, smu_ch=self.smu_string
            )
        )

    def instrID(self):
        query_str = (
            "print([[Keithley Instruments Inc., Model ]].."
            "node[{tsp_node}].model..[[, ]]..node[{tsp_node}].serialno..[[, ]]..node[{tsp_node}].revision)".format(
                tsp_node=self.tsp_node
            )
        )
        return self.query(query_str)

    def is_master(self):
        """ Returns true if this TSP node is the localnode.

        The localnode is the one being interfaced with the Ethernet cable,
        whereas the other nodes are connected to it via the TSP-Link ports.
        """
        return self.query_print("localnode.serialno") == self.query_print(
            "node[{tsp_node}].serialno".format(tsp_node=self.tsp_node)
        )

    def tsp_startup(self, restart=False):
        """ Ensures that the TSP network is available.

        - Checks if tsplink.state is online.
        - If offline, send a reset().
        """
        state = self.query_print("tsplink.state")
        if state == "online" and not restart:
            return True
        elif state == "offline":
            nodes = int(float(self.query_print("tsplink.reset()")))
            logger.debug("%s TSP nodes found.", nodes)
            return True

    def smu_defaults(self):
        self.write("{smuX}.source.offfunc = 0".format(smuX=self.smu_full_string))  # 0 or smuX.OUTPUT_DCAMPS: Source 0 A
        self.write("{smuX}.source.offmode = 0".format(smuX=self.smu_full_string))  # 0 or smuX.OUTPUT_NORMAL: Configures the source function according to smuX.source.offfunc attribute
        self.write("{smuX}.source.highc = 1".format(smuX=self.smu_full_string))  # 1 or smuX.ENABLE: Enables high-capacitance mode
        # self.write("{smuX}.sense = 0".format(smuX=self.smu_full_string))  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)
        self.set_sense_mode(sense_mode="local")

    def startup(self):
        self.tsp_startup()
        self.smu_reset()
        self.smu_defaults()
        self.write("waitcomplete()")
        time.sleep(0.01)
        self.query_print('"startup complete."', expected_talker="startup complete.")

    def set_sense_mode(self, sense_mode="local"):
        ''' Set sense mode. Defaults to local sensing. '''
        if sense_mode == "remote":
            sense_mode = 1  # 1 or smuX.SENSE_REMOTE: Selects remote sense (4-wire)
        elif sense_mode == "local":
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)
        else:
            sense_mode = 0  # 0 or smuX.SENSE_LOCAL: Selects local sense (2-wire)

        self.write("{smuX}.sense = {sense_mode}".format(smuX=self.smu_full_string, sense_mode=sense_mode))

    # SourceMeter Essential methods

    def _configCurrent(self, currAmps):
        currAmps = float(currAmps)
        if currAmps >= 0:
            currAmps = np.clip(currAmps, a_min=1e-9, a_max=1.0)
        else:
            currAmps = np.clip(currAmps, a_min=-1, a_max=-1e-9)
        self.write(
            "{smuX}.source.leveli = {c}".format(smuX=self.smu_full_string, c=currAmps)
        )
        self._latestCurrentVal = currAmps

    def _configVoltage(self, voltVolts):
        voltVolts = float(voltVolts)
        self.write(
            "{smuX}.source.levelv = {v}".format(smuX=self.smu_full_string, v=voltVolts)
        )
        self._latestVoltageVal = voltVolts

    def setCurrent(self, currAmps):
        """ This leaves the output on indefinitely """
        currTemp = self._latestCurrentVal
        if not self.enable() or self.currStep is None:
            self._configCurrent(currAmps)
        else:
            nSteps = int(np.floor(abs(currTemp - currAmps) / self.currStep))
            for curr in np.linspace(currTemp, currAmps, 2 + nSteps)[1:]:
                self._configCurrent(curr)
                time.sleep(self.rampStepTime)

    def setVoltage(self, voltVolts):
        voltTemp = self._latestVoltageVal
        if not self.enable() or self.voltStep is None:
            self._configVoltage(voltVolts)
        else:
            nSteps = int(np.floor(abs(voltTemp - voltVolts) / self.voltStep))
            for volt in np.linspace(voltTemp, voltVolts, 2 + nSteps)[1:]:
                self._configVoltage(volt)
                time.sleep(self.rampStepTime)

    def getCurrent(self):
        curr = self.query_print("{smuX}.source.leveli".format(smuX=self.smu_full_string))
        return float(curr)

    def getVoltage(self):
        volt = self.query_print("{smuX}.source.levelv".format(smuX=self.smu_full_string))
        return float(volt)

    def setProtectionVoltage(self, protectionVoltage):
        protectionVoltage = float(protectionVoltage)
        self.write(
            "{smuX}.source.limitv = {v}".format(smuX=self.smu_full_string, v=protectionVoltage)
        )

    def setProtectionCurrent(self, protectionCurrent):
        protectionCurrent = float(protectionCurrent)
        self.write(
            "{smuX}.source.limiti = {c}".format(smuX=self.smu_full_string, c=protectionCurrent)
        )

    @property
    def compliance(self):
        return (self.query_print("{smuX}.source.compliance".format(smuX=self.smu_full_string)) == "true")

    def measVoltage(self):
        retStr = self.query_print("{smuX}.measure.v()".format(smuX=self.smu_full_string))
        v = float(retStr)
        if self.compliance:
            logger.warning('Keithley compliance voltage of %s reached', self.protectionVoltage)
            logger.warning('You are sourcing %smW into the load.', v * self._latestCurrentVal * 1e-3)
        return v

    def measCurrent(self):
        retStr = self.query_print("{smuX}.measure.i()".format(smuX=self.smu_full_string))
        i = float(retStr)  # second number is current always
        if self.compliance:
            logger.warning('Keithley compliance current of %s reached', self.protectionCurrent)
            logger.warning('You are sourcing %smW into the load.', i * self._latestVoltageVal * 1e-3)
        return i

    @property
    def protectionVoltage(self):
        volt = self.query_print("{smuX}.source.limitv".format(smuX=self.smu_full_string))
        return float(volt)

    @property
    def protectionCurrent(self):
        curr = self.query_print("{smuX}.source.limiti".format(smuX=self.smu_full_string))
        return float(curr)

    def enable(self, newState=None):
        ''' get/set enable state
        '''
        if newState is not None:
            while True:
                self.write("{smuX}.source.output = {on_off}".format(smuX=self.smu_full_string, on_off=1 if newState else 0))
                time.sleep(0.1)
                self.query_print("\"output configured\"", expected_talker="output configured")
                retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_full_string))
                is_on = float(retVal) == 1
                if bool(newState) == is_on:
                    break
        else:
            retVal = self.query_print("{smuX}.source.output".format(smuX=self.smu_full_string))
            is_on = float(retVal) == 1
        return is_on

    def __setSourceMode(self, isCurrentSource):
        if isCurrentSource:
            source_mode_code = 0
            source_mode_letter = 'i'
            measure_mode_letter = 'v'
        else:
            source_mode_code = 1
            source_mode_letter = 'v'
            measure_mode_letter = 'i'

        self.write("{smuX}.source.func = {code}".format(smuX=self.smu_full_string, code=source_mode_code))
        self.write("{smuX}.source.autorange{Y} = 1".format(smuX=self.smu_full_string, Y=source_mode_letter))
        self.write("{smuX}.measure.autorange{Y} = 1".format(smuX=self.smu_full_string, Y=measure_mode_letter))

    def setVoltageMode(self, protectionCurrent=0.05):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=False)
        self.setProtectionCurrent(protectionCurrent)
        self._configVoltage(0)

    def setCurrentMode(self, protectionVoltage=1):
        self.enable(False)
        self.__setSourceMode(isCurrentSource=True)
        self.setProtectionVoltage(protectionVoltage)
        self._configCurrent(0)
        
    # Yusuf's code
    def print_filter_state(self):
        filters = ['', 'Repeat Average', 'Moving Average', 'Median']
        # type
        filter_type = self.query_print(f"{self.smu_full_string}.measure.filter.type")
        try:
            ftype = int(float(filter_type))
            print(f"type:\t\t {filters[ftype]}")
        except:
            print("Could not convert return value of filter type to int")
            print(f'Filter type returned: {filter_type}')
        # avg count
        current_count = self.query_print(f"{self.smu_full_string}.measure.filter.count")
        try:
            c_count = int(float(current_count))
            print(f"avg. count:\t {c_count}")
        except:
            print("Could not convert return value of average count to int")
            print(f'Filter average count returned: {current_count}')
        # filter enable
        is_filter_on = self.query_print(f"{self.smu_full_string}.measure.filter.enable")
        try:
            fon = int(float(is_filter_on))
            print(f"enabled:\t {'True' if fon else 'False'}")
        except:
            print("Could not convert return value of filter enable to int")
            print(f'Filter enable returned: {is_filter_on}')
            
    # Filter
    def set_filter(self, count, set_avg_count):
        print("\nCurrent Filter State: ")
        self.print_filter_state()
        # Set filter
        if set_avg_count:
            self.write(f"{self.smu_full_string}.measure.filter.count = {str(count)}")
            self.write(f"{self.smu_full_string}.measure.filter.type = {self.smu_full_string}.FILTER_REPEAT_AVG")
            self.write(f"{self.smu_full_string}.measure.filter.enable = {self.smu_full_string}.FILTER_ON")
            print("\nFilter State After Setting: ")
            self.print_filter_state()
        return
