"""
Client-side pseudo-driver that sends commands to the ZeroMQ server for execution
on a remote ITLA laser. Adapted to the new itla_app / itla_server design.
"""

import zmq

class ITLAClient:
    """
    A simple client proxy that communicates with an ITLA laser via the ZeroMQ server.
    
    Usage Example:
        client = ITLAClient(serial_number="SERIAL123", address="192.168.1.100")
        response = client.enable_laser()
        print("Server response:", response)
    """

    def __init__(self, serial_number: str, address='localhost'):
        """
        :param serial_number: The laser's unique serial number as recognized by the server.
        :param address: The hostname or IP of the machine running the itla_server.
        """
        self.serial_number = serial_number
        self.address = address

    def _request(self, command: str) -> str:
        """
        Internal helper to send a command to the server in the format:
            "SERIAL___COMMAND"
        or for arguments:
            "SERIAL___COMMAND___arg1___arg2"
        
        Returns the server's reply as a string.
        """
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.connect(f"tcp://{self.address}:5555")

        try:
            socket.send_string(command)
            reply = socket.recv_string()
        except Exception as e:
            reply = f"Communication failed: {e}"
        finally:
            socket.close()
            context.destroy()

        return reply

    # -------------------------------------------------------------------------
    # Laser Power & On/Off
    # -------------------------------------------------------------------------
    def enable_laser(self):
        """
        Sends a request to enable the laser.
        Server command: "enable_laser"
        """
        cmd_str = f"{self.serial_number}___enable_laser"
        return self._request(cmd_str)

    def disable_laser(self):
        """
        Sends a request to disable the laser.
        Server command: "disable_laser"
        """
        cmd_str = f"{self.serial_number}___disable_laser"
        return self._request(cmd_str)

    def set_power_dbm(self, power_dbm: float):
        """
        Sets the laser power in dBm.
        Server command: "set_power_dbm___<float>"
        """
        cmd_str = f"{self.serial_number}___set_power_dbm___{power_dbm}"
        return self._request(cmd_str)

    def read_power_dbm(self):
        """
        Reads the current laser power in dBm.
        Server command: "read_power_dbm"
        """
        cmd_str = f"{self.serial_number}___read_power_dbm"
        return self._request(cmd_str)

    # -------------------------------------------------------------------------
    # Frequency
    # -------------------------------------------------------------------------
    def set_frequency_tera_hz(self, freq_thz: float):
        """
        Sets the laser frequency in THz.
        Server command: "set_frequency_tera_hz___<float>"
        """
        cmd_str = f"{self.serial_number}___set_frequency_tera_hz___{freq_thz}"
        return self._request(cmd_str)

    def get_frequency_tera_hz(self):
        """
        Reads the current laser frequency in THz.
        Server command: "get_frequency_tera_hz"
        """
        cmd_str = f"{self.serial_number}___get_frequency_tera_hz"
        return self._request(cmd_str)
    
    # -------------------------------------------------------------------------
    # Frequency
    # -------------------------------------------------------------------------
    def get_ftf_capability(self):
        """
        Get FTF capability
        Server command: "set_frequency_tera_hz___<float>"
        """
        cmd_str = f"{self.serial_number}___get_ftf_capability"
        return self._request(cmd_str)

    def ftf(self, offset_mhz: int):
        """
        Finetune the laser frequency in MHz.
        Server command: "ftf___<float>"
        """
        cmd_str = f"{self.serial_number}___ftf___{offset_mhz}"
        return self._request(cmd_str)

    # -------------------------------------------------------------------------
    # Clean Sweep
    # -------------------------------------------------------------------------
    def set_clean_sweep_range(self, range_ghz: float):
        """
        Sets the clean sweep range in GHz.
        Server command: "set_clean_sweep_range___<float>"
        """
        cmd_str = f"{self.serial_number}___set_clean_sweep_range___{range_ghz}"
        return self._request(cmd_str)

    def set_clean_sweep_rate(self, rate_ghz_s: float):
        """
        Sets the sweep rate in GHz
        """
        return self._request(f"{self.serial_number}___set_clean_sweep_rate___{rate_ghz_s}")
    
    def enable_clean_sweep(self):
        """
        Enables Clean Sweep.
        Server command: "enable_clean_sweep"
        """
        cmd_str = f"{self.serial_number}___enable_clean_sweep"
        return self._request(cmd_str)

    def disable_clean_sweep(self):
        """
        Disables Clean Sweep.
        Server command: "disable_clean_sweep"
        """
        cmd_str = f"{self.serial_number}___disable_clean_sweep"
        return self._request(cmd_str)

    def read_clean_sweep_offset(self):
        """
        Reads the Clean Sweep offset.
        Server command: "read_clean_sweep_offset"
        """
        cmd_str = f"{self.serial_number}___read_clean_sweep_offset"
        return self._request(cmd_str)

    def load_clean_sweep_calibration(self, cal_val: int):
        return self._request(f"{self.serial_number}___load_clean_sweep_calibration___{cal_val}")
    
    # -------------------------------------------------------------------------
    # Clean Jump
    # -------------------------------------------------------------------------
    def set_clean_jump_frequency(self, freq_thz: float):
        """
        Sets the Clean Jump target frequency in THz.
        Server command: "set_clean_jump_frequency___<float>"
        """
        cmd_str = f"{self.serial_number}___set_clean_jump_frequency___{freq_thz}"
        return self._request(cmd_str)

    def set_clean_jump_temperature(self, temperature_c: float):
        """
        Sets the Clean Jump target temperature in Celsius.
        Server command: "set_clean_jump_temperature___<float>"
        """
        cmd_str = f"{self.serial_number}___set_clean_jump_temperature___{temperature_c}"
        return self._request(cmd_str)

    def enable_clean_jump(self):
        """
        Enables the Clean Jump (executes it).
        Server command: "enable_clean_jump"
        """
        cmd_str = f"{self.serial_number}___enable_clean_jump"
        return self._request(cmd_str)

    def read_clean_jump_offset(self):
        return self._request(f"{self.serial_number}___read_clean_jump_offset")

    # -------------------------------------------------------------------------
    # Noise Mode
    # -------------------------------------------------------------------------
    def set_low_noise_mode(self, mode: int):
        """
        Sets the low-noise mode: 0=std, 1=no-dither, 2=whisper.
        Server command: "set_low_noise_mode___<int>"
        """
        cmd_str = f"{self.serial_number}___set_low_noise_mode___{mode}"
        return self._request(cmd_str)

    def get_low_noise_mode(self):
        """
        Reads the current low-noise mode.
        Server command: "get_low_noise_mode"
        """
        cmd_str = f"{self.serial_number}___get_low_noise_mode"
        return self._request(cmd_str)

    # -------------------------------------------------------------------------
    # Misc / Info
    # -------------------------------------------------------------------------
    def get_serial_number(self):
        """
        Returns the laser's serial number from the server perspective.
        Server command: "get_serial_number"
        """
        cmd_str = f"{self.serial_number}___get_serial_number"
        return self._request(cmd_str)
    
    def get_release(self):
        """
        Returns the laser's release info
        """
        cmd_str = f"{self.serial_number}___get_release"
        return self._request(cmd_str)

    def port_close(self):
        """
        Tells the server to close the underlying serial port for this device.
        Server command: "port_close"
        """
        cmd_str = f"{self.serial_number}___port_close"
        return self._request(cmd_str)
