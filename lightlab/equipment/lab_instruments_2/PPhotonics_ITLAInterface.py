import re
import time
import numpy as np
from scipy.constants import c as C0

from lightlab.equipment.lab_instruments_2.PPhotonics_ITLAClient import ITLAClient

# Helpers
def wait2(time_sec):
    time.sleep(time_sec)
    return

def freq_to_wavl(frequency, speed_of_light=C0):
    return speed_of_light / np.array(frequency)

def wavl_to_freq(wavl, speed_of_light=C0):
    return speed_of_light / np.array(wavl)

def safe_float_regex(value):
    try:
        return float(re.sub(r'[^\d\.]', '', value))
    except ValueError:
        return None


# Laser state representation
LASER_OFF = 0
LASER_ON  = 1

class LaserState:
    def __init__(self):
        self.on = LASER_OFF
        self.power = None       # last requested power in dBm
        self.wavelength = None  # last requested wavelength (nm) or None

class Laser:
    """
    High-level Laser wrapper, no software triggers for clean sweep or jump.
    """
    def __init__(self, serial: str, address: str):
        self.verbose = False
        self.laser_state = LaserState()
        # Null padding necessary if length of serial no. != 10
        self.serial = serial if len(serial) == 10 else serial + "\x00\x00\x00\x00\x00\x00"
        self.client = ITLAClient(serial_number=self.serial, address=address)

        # Initialize from device
        freq_str = self.client.get_frequency_tera_hz()
        freq_thz = safe_float_regex(freq_str) or 193.1
        freq_ghz = freq_thz * 1000
        self.laser_state.wavelength = freq_to_wavl(freq_ghz)

        power_str = self.client.read_power_dbm()
        p_val = safe_float_regex(power_str) or 7.0
        self.laser_state.power = p_val
        
        print(f"Connected to ITLA Laser S/N: {self.serial.strip()} at {address}. Initial freq: {freq_ghz:.3f} GHz, power: {p_val:.3f} dBm")

    # -------------------------------------------------------------------------
    # Laser On/Off
    # -------------------------------------------------------------------------
    def ensure_on(self, wait=True):
        if self.laser_state.on == LASER_OFF:
            self.client.enable_laser()
            self.laser_state.on = LASER_ON
        if wait:
            self.wait_for_power_up()
            
        if 'PP7' in self.serial:
            wait2(4)
            self.set_low_noise_mode(1)  # No-dither mode for PP7 lasers
            wait2(4)
            self.set_low_noise_mode(1)  # Switch back to standard mode after stabilization
            

    def ensure_off(self):
        self.client.disable_laser()
        self.laser_state.on = LASER_OFF

    # -------------------------------------------------------------------------
    # Power
    # -------------------------------------------------------------------------
    def set_power(self, 
                  power_dbm: float, 
                  turn_on=False):
        """
        Turn laser off, set power, turn on again, wait for stable power if needed."""
        
        self.ensure_off()
        self.client.set_power_dbm(power_dbm)
        self.laser_state.power = power_dbm
        if turn_on:
            self.ensure_on()

    def get_power(self) -> float:
        """
        Returns the actual measured power from the device.
        """
        p_str = self.client.read_power_dbm()
        p_val = safe_float_regex(p_str)
        if p_val is not None:
            self.laser_state.power = p_val
            
        return p_val if p_val is not None else float('nan')

    def wait_for_power_up(self, tolerance_ratio=0.004, consecutive=32, timeout=60):
        """
        Checks laser power stability with safeguards for edge cases and timeouts.
        """
        if self.laser_state.power is None:
            return

        req = self.laser_state.power
        count = 0
        start_time = time.time()
        max_retries = 100
        retries = 0

        while (time.time() - start_time) < timeout and retries < max_retries:
            p_str = self.client.read_power_dbm()
            p_val = safe_float_regex(p_str)

            if p_val is None:
                retries += 1
                # time.sleep(0.05)
                continue

            # Calculate error (absolute for near-zero targets)
            err = abs(p_val - req) / abs(req)
            tolerance = tolerance_ratio

            # Update progress
            print(
                f"Laser power: {p_val:.3f} dBm \t Error: {err:5.3f} \t Count: {count}",
                end="\r",
                flush=True,
            )

            if err < tolerance:
                count += 1
                if count >= consecutive:
                    print(f"\nLaser power stable at {p_val:.3f} dBm")
                    return
            else:
                count = 0

            # time.sleep(0.05)

        # raise TimeoutError("Laser power stabilization failed to stablilize in 30 s")
        print(f"\nFinal Laser power at {p_val:.3f} dBm")

    # -------------------------------------------------------------------------
    # Frequency
    # -------------------------------------------------------------------------
    def set_wavelength(self, wavelength_nm: float, turn_on=False):
        """
        Turn laser off, set freq, turn on again.
        """
        freq_ghz = wavl_to_freq(wavelength_nm)
        freq_thz = freq_ghz / 1000.0
        self.ensure_off()
            
        self.client.set_frequency_tera_hz(freq_thz)
        self.laser_state.wavelength = wavelength_nm
        
        if turn_on:
            self.ensure_on()

    def set_frequency_ghz(self, freq_ghz: float, turn_on=False):
        """
        Utility method: sets frequency in GHz. The server expects THz.
        """
        self.set_wavelength(freq_to_wavl(freq_ghz), turn_on)

    def get_frequency_ghz(self) -> float:
        """
        Return frequency in GHz by reading THz from server and multiplying by 1000.
        """
        freq_str = self.client.get_frequency_tera_hz()
        freq_thz = safe_float_regex(freq_str) or 193.0
        return freq_thz * 1000

    # -------------------------------------------------------------------------
    # Frequency
    # -------------------------------------------------------------------------
    def get_ftf_capability(self):
        """
        Get FTF capability
        """
        return self.client.get_ftf_capability()

    def ftf(self, offset_mhz: int):
        """
        Utility method: sets frequency in GHz. The server expects THz.
        """
        return self.client.ftf(offset_mhz)
    

    # -------------------------------------------------------------------------
    # Clean Sweep (no triggers)
    # -------------------------------------------------------------------------
    def set_clean_sweep(self, range_ghz: float, rate_ghz_s: float):
        """
        Configure range & rate. Doesn't enable yet.
        For extended range >150GHz, load calibrations if needed.
        """
        if range_ghz > 150:
            # Example calibration approach if needed
            self.client.load_clean_sweep_calibration(1234)

        self.client.set_clean_sweep_range(range_ghz)
        self.client.set_clean_sweep_rate(rate_ghz_s)

    def start_clean_sweep(self):
        """
        Just enable the sweep. Laser will ramp continuously until stopped.
        """
        self.client.enable_clean_sweep()

    def stop_clean_sweep(self):
        """
        Disables the sweep.
        """
        self.client.disable_clean_sweep()

    def read_sweep_offset(self) -> float:
        """
        Returns the current offset in GHz from -range/2 to +range/2.
        """
        off_str = self.client.read_clean_sweep_offset()
        off_val = safe_float_regex(off_str)
        return off_val if off_val is not None else float('nan')

    # -------------------------------------------------------------------------
    # Clean Jump
    # -------------------------------------------------------------------------
    def clean_jump(self, target_freq_thz: float, target_temp_c: float = 0.0):
        """
        1) set frequency registers
        2) set temperature
        3) enable jump
        """
        self.client.set_clean_jump_frequency(target_freq_thz)
        # self.client.set_clean_jump_temperature(target_temp_c)
        self.client.enable_clean_jump()

    def read_clean_jump_offset(self) -> float:
        """
        offset (MHz) = (raw - 10000).
        """
        val_str = self.client.read_clean_jump_offset()
        return safe_float_regex(val_str) or float('nan')
    
    # -------------------------------------------------------------------------
    # Noise mode
    # -------------------------------------------------------------------------
    def set_low_noise_mode(self, mode):
        """
        Sets the low-noise mode: 
            0=std, 
            1=no-dither, 
            2=whisper.
        """
        assert mode in [0, 1, 2], print('Unknown mode specified. Allowed modes are low-noise mode: 0=std, 1=no-dither, 2=whisper.')
        
        self.client.set_low_noise_mode(mode)
    
    def get_low_noise_mode(self):
        """
        Sets the low-noise mode: 
            0=std, 
            1=no-dither, 
            2=whisper.
        """
        return self.client.get_low_noise_mode()
        
    # -------------------------------------------------------------------------
    # Close / Cleanup
    # -------------------------------------------------------------------------
    def close_port(self):
        self.client.port_close()
