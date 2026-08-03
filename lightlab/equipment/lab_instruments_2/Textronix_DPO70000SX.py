from time import sleep

import pyvisa  # Should be pyvisa-py
import numpy as np
import matplotlib.pyplot as plt

VERBOSE = 0

class Oscilloscope:

    def __init__(self, visa_address):
        """ Creates an Oscilloscope object from the provided visa address.

        This has been tested on TCPIP Visa addresses
        """

        # Store visa address
        self.visa_address = visa_address
        self.immediate_measurement = ''
        self.immediate_source = ''


        # Open associated instrument using pyvisa
        rm = pyvisa.ResourceManager()
        self.resource = rm.open_resource(self.visa_address)


        # Set fixed configuration details of scope
        # TODO: Allow override as arguments to __init__()
        self.resource.timeout = 10000  # ms
        self.resource.encoding = 'latin_1'
        self.resource.read_termination = '\n'
        self.resource.write_termination = None
        # self.resource.write('*cls')  # clear ESR
        self.resource.write('header OFF')  # disable attribute echo in replies

        # Enable acquisition
        self.resource.write('acquire:state ON')
        self.resource.write('acquire:stopafter RUNSTOP;state ON')

        # Ensure complete
        self.resource.query('*opc?')

        if VERBOSE:
            print('DPO73304SX')

    def raw_query(self, query):
        return self.resource.query(query)
    
    def raw_write(self, command):
        return self.resource.write(command)
    
    def reset_stats(self):
        self.raw_write('MEASUREMENT:STATISTICS:COUNT RESET')
        return
    
    def set_acquisition_mode(self, mode):
        '''
            modes: Sample (SAM), Average (AVE), Envelope (ENV) etc
            
            {SAMple|PEAKdetect|HIRes|AVErage|WFMDB|ENVelope}
        '''
        self.raw_write(f'ACQuire:MODe {mode}')
        
        return
    
    def set_avg_no(self, avg_no):
        self.raw_write(f'ACQuire:NUMAVg {avg_no}')
        return
    
    def restart_acquisition_avg_mode(self, avg_no=64):
        self.set_avg_no(avg_no+1) # hack to reset the averaging
        sleep(0.1)
        self.set_avg_no(avg_no)
        return
    
    def reset_averaging(self):
        self.raw_query('COUnter CLEAR')
        return
    
    def set_scale(self, channel, scale_mV):
        self.raw_write(f':CH{channel}:SCA {scale_mV}E-3')
        return
    
    def amplitude(self, channel, meas_id=1, meas_type='MEAN'):
        ''' 
            Return signal amplitude

            Args:
                channel         : scope channel
                measurement_id  : measurement channel (1-8)
                type            : (MEAN, INSTANTANEOUS, MAX, MINI)
        '''

        amp = 0
        meas_type_curr = self.raw_query(f'Measurement:meas{meas_id}?')
        if f'CH{channel}' in meas_type_curr and 'AMPLITUDE' in meas_type_curr:
           amp = self.raw_query(f'Measurement:Meas{meas_id}:{meas_type}?')
        else:
            raise Exception('Amplitude measurement not yet set on scope')
        
        return float(amp)
    
    def get_measurement(self, channel, meas_id, meas_type='MEAN'):
        ''' 
            Return signal amplitude

            Args:
                channel         : scope channel
                measurement_id  : measurement channel (1-8)
                type            : (MEAN, INSTANTANEOUS, MAX, MINI)
        '''
        meas = 0
        meas_type_curr = self.raw_query(f'Measurement:meas{meas_id}?')
        if f'CH{channel}' in meas_type_curr:
            meas = self.raw_query(f'Measurement:Meas{meas_id}:{meas_type}?')
        else:
            raise Exception('Specified measurement not yet set on scope')
        
        return float(meas)
    
    
    def peak2peak(self, channel, meas_id=1, meas_type='MEAN'):
        ''' 
            Return signal amplitude

            Args:
                channel         : scope channel
                measurement_id  : measurement channel (1-8)
                type            : (MEAN, INSTANTANEOUS, MAX, MINI)
        '''

        pk2pk = 0
        meas_type_curr = self.raw_query(f'Measurement:meas{meas_id}?')
        if f'CH{channel}' in meas_type_curr and 'PK2PK' in meas_type_curr:
           pk2pk = self.raw_query(f'Measurement:Meas{meas_id}:{meas_type}?')
        else:
            raise Exception('Peak-2-Peak measurement not yet set on scope')
        
        return float(pk2pk)
    
    
    def read(self, channel=1):
        """ Reads a snapshot of the current oscilloscope data for the given channel """

        # Configure curve
        self.resource.write('data:encdg RIBINARY')  # signed integer
        self.resource.write(f'data:source CH{channel}')
        self.resource.write('data:start 1')
        acq_record = int(self.resource.query('horizontal:recordlength?'))
        self.resource.write('data:stop {}'.format(acq_record))
        self.resource.write('wfmoutpre:byt_n 2')  # 2 byte per sample

        # Read data
        bin_wave = self.resource.query_binary_values('curve?', datatype='h', container=np.array, is_big_endian=True)

        # Read associated configuration
        wfm_record = int(self.resource.query('wfmoutpre:nr_pt?'))
        pre_trig_record = int(self.resource.query('wfmoutpre:pt_off?'))
        t_scale = float(self.resource.query('wfmoutpre:xincr?'))
        t_sub = float(self.resource.query('wfmoutpre:xzero?'))  # sub-sample trigger correction
        v_scale = float(self.resource.query('wfmoutpre:ymult?'))  # volts / level
        v_off = float(self.resource.query('wfmoutpre:yzero?'))  # reference voltage
        v_pos = float(self.resource.query('wfmoutpre:yoff?'))  # reference position (level)

        # Creates nice output vectors

        # Time:
        total_time = t_scale * wfm_record
        t_start = (-pre_trig_record * t_scale) + t_sub
        t_stop = t_start + total_time
        scaled_time = np.linspace(t_start, t_stop, num=wfm_record, endpoint=False)

        # Amplitude:
        unscaled_wave = np.array(bin_wave, dtype='double')  # data type conversion
        scaled_wave = (unscaled_wave - v_pos) * v_scale + v_off

        # Returns time/amplitude vectors
        return scaled_time, scaled_wave

    def trig(self):
        self.resource.write("trig force")

    def close(self):
        self.resource.close()



class ScopeRead:

    def __init__(self, times, voltages):
        """Initialize from given data"""
        self.times, self.voltages = times, voltages
        self.frequencies = None
        self.amplitudes = None
        self.phases = None
        self.peak2peak = np.max(voltages) - np.min(voltages)

    def get_fft(self):
        length = len(self.voltages)
        timestep = self.times[1] - self.times[0]
        freqstep = 1/timestep/length
        freqs = np.array(list(range(length)))*freqstep
        
        fft = np.fft.fft(self.voltages)
        
        fft = fft[:len(fft)>>1]
        freqs = freqs[:len(fft)]

        self.frequencies = freqs
        self.amplitudes = np.absolute(fft)
        self.phases = np.angle(fft)

        return self.amplitudes, self.phases
    
    def get_params(self, guess_freq=None):
        if self.frequencies is None:
            self.get_fft()

        if guess_freq is None:
            index = np.argmax(self.amplitudes[1:]) + 1 # Ignore DC offset
        else:
            guess_index = np.argmin(np.abs(self.frequencies-guess_freq))
            min_index = int(guess_index * 0.9)
            max_index = int(guess_index * 1.1)
            index = np.argmax(self.amplitudes[min_index:max_index]) + min_index
        return self.amplitudes[index]/len(self.times), self.frequencies[index], self.phases[index]

    # def plot(self, with_fit=False):
    #     plt.plot(self.times*1e6, self.voltages*1000, label="Data")
    #     plt.xlabel("Time (us)")
    #     plt.ylabel("Voltage (mV)")
    #     if with_fit:
    #         popt = self.get_fit()
    #         plt.plot(self.times*1e6, model(self.times, *popt)*1000, label="Fit")
    #         plt.legend()
    #         plt.title(f"$v(t)={popt[0]*1000:.4f}sin(2\pi({popt[1]/1e6:.4f})t + {popt[2]:.2f})$")

    def plot_fft(self, normalize=False, guess_freq = None):
        if self.frequencies is None:
            self.get_fft()

        # Normalize
        if normalize:
            norm_amplitudes = self.amplitudes/np.max(self.amplitudes)
        else:
            norm_amplitudes = self.amplitudes

        plt.plot(self.frequencies/1e6, 10*np.log10(norm_amplitudes))
        # plt.yscale("log")
        plt.xlabel("Frequency (MHz)")
        plt.ylabel("Intensity (dB)")
        plt.title(f"Frequency: {self.get_params(guess_freq)[1]/1e6:.4f} MHz")