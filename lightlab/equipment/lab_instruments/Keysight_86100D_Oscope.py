from lightlab.equipment.abstract_drivers import kf
from lightlab.util.data import Waveform

import numpy as np
import matplotlib.pyplot as plt

class Keysight_86100D_Oscope (kf.VisaManager):

    def __init__(self, name='Keysight Oscilloscope', address=None, **kwargs):
        self.FlexDCA = kf.VisaManager(address=address, scpi_echo=False)

    def __del__(self):
        self.FlexDCA.write(':SYSTem:GTLocal')
        self.FlexDCA.close()

    def configure_FlexDCA_eye(self, channel):
        """ Installs a simulated module and prepares self.FlexDCA for
        measurements.
        """
        print('Configuring self.FlexDCA.', flush=True)
        self.FlexDCA.query(':SYSTem:DEFault;*OPC?')
        kf.all_channels_off(self.FlexDCA)
        kf.install_simulated_module(self.FlexDCA, channel, 'DEM')
        self.FlexDCA.write(':CHAN' + channel + ':DISPlay ON')
        self.FlexDCA.write(':ACQuire:RUN')
        self.FlexDCA.write(':SYSTem:MODE EYE')
        self.FlexDCA.query(':SYSTem:AUToscale;*OPC?')

    def configure_FlexDCA_pattern(self, channel):
        """ Installs a simulated module and prepares FlexDCA for
        measurements.
        """
        self.FlexDCA.query(':SYSTem:DEFault;*OPC?')
        kf.install_simulated_module(self.FlexDCA, channel, 'DEM')
        self.FlexDCA.write(':SOURce'+channel+':DRATe 9.95328E+9')
        self.FlexDCA.write(':SOURce'+channel+':WTYPe DATA')
        self.FlexDCA.write(':SOURce'+channel+':PLENgth 127')
        self.FlexDCA.write(':SOURce'+channel+':AMPLitude 90E-3')
        self.FlexDCA.write(':SOURce'+channel+':NOISe:RN 3.0E-6')
        self.FlexDCA.write(':SOURce'+channel+':JITTer:RJ 4.0E-12')
        self.FlexDCA.write(':CHAN' + channel + ':DISPlay ON')
        self.FlexDCA.write(':ACQuire:RUN')
        self.FlexDCA.query(':SYSTem:MODE OSCilloscope;*OPC?')
        self.FlexDCA.write(':TRIGger:PLOCk ON')
        self.FlexDCA.write(':ACQuire:EPATtern ON')
        while True:
            if self.FlexDCA.query(':WAVeform:PATTern:COMPlete?'):
                break
        self.FlexDCA.query(':SYSTem:AUToscale;*OPC?')
        self.FlexDCA.write(':TIMebase:UNIT UINTerval')
        pattern_length = self.FlexDCA.query(':TRIGger:PLENgth?')
        self.FlexDCA.write(':TIMebase:UIRange ' + pattern_length)
        self.FlexDCA.write(':ACQuire:STOP')

    def get_eye_info(self, channel):
        """ Returns information about eye diagram.
        """
        print('Returning waveform data.', flush=True)
        self.FlexDCA.write(':WAVeform:SOURce CHANnel' + channel)
        xorg = self.FlexDCA.query(':WAVeform:EYE:XORigin?')
        yorg = self.FlexDCA.query(':WAVeform:EYE:YORigin?')
        xinc = self.FlexDCA.query(':WAVeform:EYE:XINCrement?')
        yinc = self.FlexDCA.query(':WAVeform:EYE:YINCrement?')
        xstart = kf.eng_notation(xorg, '0.2') + 's'
        xend = str(float(xorg) + (float(xinc) * 750))
        xend = kf.eng_notation(xend, '0.2') + 's'
        ymin = kf.eng_notation(yorg, '0.2') + 'V'
        ymax = str(float(yorg) + (float(yinc) * 520))
        ymax = kf.eng_notation(ymax, '0.2') + 'V'
        return (xstart, xend, ymin, ymax)

    def get_pattern_info(self, channel):
        print('Get pattern scaling information.', flush=True)
        values = {'p_length': '',
                  'p_points': '',
                  'xmin': '',
                  'xmax': '',
                  'ymin': '',
                  'ymax': '',
                  'xscale': '',
                  'yscale': ''}
        self.FlexDCA.write(':WAVeform:SOURce CHANnel' + channel)
        values['p_length'] = self.FlexDCA.query(':WAVeform:PATTern:BITS?')
        values['p_points'] = int(self.FlexDCA.query(':WAVeform:XYFORmat:POINts?'))
        values['xmin'] = self.FlexDCA.query(':TIMebase:XLEFt?')
        values['xmax'] = self.FlexDCA.query(':TIMebase:XRIGht?')
        values['ymin'] = self.FlexDCA.query(':CHANnel' + channel + ':YBOTTom?')
        values['ymax'] = self.FlexDCA.query(':CHANnel' + channel + ':YTOP?')
        values['xscale'] = self.FlexDCA.query(':TIMebase:SCALe?')
        values['yscale'] = self.FlexDCA.query(':CHANnel' + channel + ':YSCale?')
        print('-' * 30)
        print('X-scale maximum: ' + kf.eng_notation(values['xmax'], '1.00') + 's')
        print('X-scale minimum: ' + kf.eng_notation(values['xmin'], '1.00') + 's')
        print('Y-scale maximum: ' + kf.eng_notation(values['ymax'], '1.00') + 'V')
        print('Y-scale minimum: ' + kf.eng_notation(values['ymin'], '1.00') + 'V')
        print('Pattern length: ' + values['p_length'] + ' bits')
        print('Data points: ' + str(values['p_points']))
        print('-' * 30)
        return values

    def get_binary_eye_data(self, channel):
        """ Returns the data points for an eye diagram by
        transferring binary data to computer.
        """
        print('Returning eye waveform data.', flush=True)
        eyedata = []
        endiansetting = self.FlexDCA.query(':SYSTem:BORDER?')
        self.FlexDCA.write(':SYSTem:BORDER LENDian')
        message = ':WAVeform:EYE:INTeger:DATa?'
        eyedata = self.FlexDCA.query_binary_values(message,
                                          datatype='L',
                                          container=list,
                                          is_big_endian=False,
                                          header_fmt='ieee')
        self.FlexDCA.write(':SYSTem:BORDER ' + endiansetting)
        return eyedata

    def get_waveform_x_data(self):
        """ Reads x data as floats. Using pyvisa's read_raw() method requires
        that :WAVeform:XYFORmat:FLOat:XDATa? query be sent using the write()
        method followed by separate read_raw().
        """
        print('Get pattern waveform X data.', flush=True)
        x_data = []  # Python 3 raw byte string
        endiansetting = self.FlexDCA.query(':SYSTem:BORDER?')  # get current byte order
        self.FlexDCA.write(':SYSTem:BORDER LENDian')  # set little endian byte order
        message = ':WAVeform:XYFORmat:FLOat:XDATa?'
        x_data = self.FlexDCA.query_binary_values(message,
                                                  datatype='f',
                                                  container=list,
                                                  is_big_endian=False,
                                                  header_fmt='ieee')
        self.FlexDCA.write(':SYSTem:BORDER ' + endiansetting)
        # scale data
        n = 0
        while n < len(x_data):
            x_data[n] *= 1E9  # data in mV
            n += 1
        return x_data
        
    def get_waveform_y_data(self):
        """ Reads y data as floats. Using pyvisa's read_raw() method requires
        that :WAVeform:XYFORmat:FLOat:XDATa? query be sent using the write()
        method followed by separate read_raw().
        """
        print('Get pattern waveform Y data.', flush=True)
        y_data = []
        endiansetting = self.FlexDCA.query(':SYSTem:BORDER?')  # get current byte order
        self.FlexDCA.write(':SYSTem:BORDER LENDian')  # set little endian byte order
        message = ':WAVeform:XYFORmat:FLOat:YDATa?'
        y_data = self.FlexDCA.query_binary_values(message,
                                                  datatype='f',
                                                  container=list,
                                                  is_big_endian=False,
                                                  header_fmt='ieee')
        self.FlexDCA.write(':SYSTem:BORDER ' + endiansetting)
        # scale data
        n = 0
        while n < len(y_data):
            y_data[n] *= 1E3  # data in ns
            n += 1
        return y_data

    def draw_graph_eye(self, eyedata, Labels, channel):
        """
        Plots binary data and saved graphics file to prove
        that we received the data from self.FlexDCA.
        Labels is a string tupple of plot labels: (xstart, xend, ymin, ymax)
        """
        print('Drawing eye diagram.', flush=True)
        fig = plt.figure(figsize=(10, 8), dpi=80, edgecolor='black')
        ax = fig.add_subplot(111)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.set_aspect('0.8')
        ax.xaxis.set_major_locator(plt.MultipleLocator(1.0))
        ax.yaxis.set_major_locator(plt.MultipleLocator(1.0))
        ax.grid(which='major', axis='both', linewidth=0.75,
                linestyle='-', color='0.75')
        ax.set_xticklabels(['', Labels[0], '', '', '', '', '', '', '',
                            '', '', Labels[1], ''])
        ax.set_yticklabels(['', Labels[2], '', '', '', '0', '', '',
                            '', Labels[3]])
        ax.set_ylabel('Voltage', fontsize=12)
        ax.set_xlabel('Time', fontsize=12)
        plt.plot((5, 5), (0, 8), 'k-', linewidth=2)  # draw center line
        plt.plot((0, 10), (4, 4), 'k-', linewidth=2)  # draw center line
        fig.suptitle('Channel ' + channel + ' Eye Diagram',
                     y=0.85, fontsize=12)
        x = []  # scaled point x position
        y = []  # scaled point y position
        n = 0  # list index
        col = 0
        while col < 751:
            row = 0
            while row < 521:
                point = eyedata[n]
                if point:  # point has hits
                    x.append(round((col / 751.0 * 10), 3))  # scaled x location
                    y.append(round((row / 521.0), 3) * 8)  # scaled y location
                row += 1
                n += 1
            col += 1
        plt.scatter(x, y, s=2, color='green', alpha=1, marker='.')
        # s = 'eye_diagram_' + channel + '.png'
        # plt.savefig(s, dpi=300)
        plt.show()
        # print('File saved in script folder: ', s, flush=True)
        
    def draw_graph_pattern(self, ydata, xdata, values, channel):
        """
        Draw graph.
        """
        print('Draw the pattern graph.', flush=True)
        xmin = round(float(values['xmin']) * 1E9, 1)
        xmax = round(float(values['xmax']) * 1E9, 2)
        ymin = round(float(values['ymin']) * 1E3, 1)
        ymax = round(float(values['ymax']) * 1E3, 1)
        title = 'Channel ' + channel + ': ' +\
                values['p_length'] + ' Bit Pattern Waveform'
        plt.figure(figsize=(8, 6), dpi=80)
        plt.plot(xdata, ydata, 'g-')  # data points hidden. line only
        plt.title(title)
        plt.xlabel('Time (ns)')
        plt.ylabel('Voltage (mV)')
        y_ticks = np.linspace(ymin, ymax, num=9, endpoint=True)
        y_axis_midpoint = round(ymax - (ymax-ymin)/2.0, 1)
        s = str(y_axis_midpoint)
        y_text = (str(ymin), '', '', '', s, '', '', '', str(ymax))
        plt.yticks(y_ticks, y_text)
        x_ticks = np.linspace(xmin, xmax, num=11, endpoint=True)
        x_text = (str(xmin), '', '', '', '', '', '', '', '', '', str(xmax))
        plt.xticks(x_ticks, x_text)
        plt.grid(b=True, which='major', axis='both')
        plt.ylim(ymin, ymax)
        plt.xlim(xmin, xmax)
        # plt.savefig(PLOTFILE, dpi=150)
        plt.show()
        # print('File saved in script folder: ', PLOTFILE, flush=True)

    def acquire_eye(self, channel):
        self.configure_FlexDCA_eye(channel)
        kf.waveform_acquisition(self.FlexDCA, 100)
        plot_labels = self.get_eye_info(channel)
        eyedata = self.get_binary_eye_data(channel)
        self.draw_graph_eye(eyedata, plot_labels, channel)
        
    def acquire_pattern(self, channel):
        self.configure_FlexDCA_pattern(channel)
        values = self.get_pattern_info(channel)
        x_data = self.get_waveform_x_data()
        y_data = self.get_waveform_y_data()
        self.draw_graph_pattern(y_data, x_data, values, channel)