# -*- coding: utf-8 -*-
"""
kf.py
This module imports the pyvisa module, includes unicode constants for
strings, and a class for making connecting to and communication
with FlexDCA.
_________________________________________________________________________
Copyright 2016 Keysight Technologies Inc. All rights reserved.
You have a royalty-free right to use, modify, reproduce and distribute this
example files (and/or any modified version) in any way you find useful,
provided that you agree that Keysight has no warranty, obligations or
liability for any Sample Application Files.
_________________________________________________________________________

"""
import time
import visa  # import VISA library

FlexDCA = None
VISA_LIBRARY = r'C:\WINDOWS\system32\visa64.dll'

#  Channel color constants.
RED = 'TCOL4'
SALMON = 'TCOL10'
PINK = 'TCOL6'
PURPLE = 'TCOL8'
ORANGE = 'TCOL12'
SUNSET = 'TCOL15'
GOLD = 'TCOL7'
YELLOW = 'TCOL1'
GREEN = 'TCOL2'
MOSS = 'TCOL16'
SEAGREEN = 'TCOL13'
BLUE = 'TCOL3'
DARKBLUE = 'TCOL9'
LIGHTBLUE = 'TCOL5'
SKYBLUE = 'TCOL14'
VIOLET = 'TCOL11'

#  Python 3 Unicode Greek alphabet constants.
ALPHAU = '\u0391'  # Î‘
BETAU = '\u0392'  # Î’
GAMMAU = '\u0393'  # Î“
DELTAU = '\u0394'  # Î”
EPSILONU = '\u0395'  # Î•
ZETAU = '\u0396'  # Î–
ETAU = '\u0397'  # Î—
THETAU = '\u0398'  # Î˜
IOTAU = '\u0399'  # Î™
KAPPAU = '\u039A'  # Îš
LAMDAU = '\u039B'  # Î›
MUU = '\u039C'  # Îœ
NUU = '\u039D'  # Î
XIU = '\u039E'  # Îž
OMICRONU = '\u039F'  # ÎŸ
PIU = '\u03A0'  # Î 
RHOU = '\u03A1'  # Î¡
SIGMAU = '\u03A3'  # Î£
TAUU = '\u03A4'  # Î¤
UPSILONU = '\u03A5'  # Î¥
PHIU = '\u03A6'  # Î¦
CHIU = '\u03A7'  # Î§
PSIU = '\u03A8'  # Î¨
OMEGAU = '\u03A9'  # Î©

ALPHA = '\u03B1'  # Î±
BETA = '\u03B2'  # Î²
GAMMA = '\u03B3'  # Î³
DELTA = '\u03B4'  # Î´
EPSILON = '\u03B5'  # Îµ
ZETA = '\u03B6'  # Î¶
ETA = '\u03B7'  # Î·
THETA = '\u03B8'  # Î¸
IOTA = '\u03B9'  # Î¹
KAPPA = '\u03BA'  # Îº
LAMDA = '\u03BB'  # Î»
MU = '\u03BC'  # Î¼
NU = '\u03BD'  # Î½
XI = '\u03BE'  # Î¾
OMICRON = '\u03BF'  # Î¿
PI = '\u03C0'  # Ï€
RHO = '\u03C1'  # Ï
SIGMA = '\u03C3'  # Ïƒ
TAU = '\u03C4'  # Ï„
UPSILON = '\u03C5'  # Ï…
PHI = '\u03C6'  # Ï†
CHI = '\u03C7'  # Ï‡
PSI = '\u03C8'  # Ïˆ
OMEGA = '\u03C9'  # Ï‰

# Additional Python 3 Unicode characters
DEGREE = '\u00B0'  # Â°
PLUSSMINUS = '\u00B1'  # Â±
LTEQ = '\u2264'  # â‰¤
GTEQ = '\u2265'  # â‰¥


class VisaManager(object):
    """ This class abstracts an instance of pyVisa's GPIBInstrument class.
    This allows for features such as scpi command logging that can be
    turned on or off. """

    def __init__(self, address, visa_library='', scpi_echo=False):
        """ Creates a VisaManager object for communicating with FlexDCA.

        Args
        ====
        address
            FlexDCA's VISA hislip address.
        visa_library
            Optional path to PC's visa dll. Default value is given in
            kf.VISA_LIBRARY constant.
        scpi_echo
            True turns on scpi logging to console as an aid to
            troubleshooting.
        Returns
        =======
        A VisaManager object.

        Private Properties
        ==================
        self._rm
            py.visa's ResourceManager object.
        self._instrument
            Instance of pyVisa's TCPIPInstrument class.
        """
        self._instID = ''  # Identification string of N1010A,...
        self._scpi_echo = scpi_echo
        try:
            # Create an instance of PyVISA's ResourceManager
            self._rm = visa.ResourceManager(visa_library)
            self._instrument = self._rm.open_resource(address)
            self._instrument.timeout = 20000  # Set connection timeout to 20s
            self._instrument.read_termination = '\n'
            self._instrument.write_termination = '\n'
            self._instID = self._instrument.query('*IDN?')
            print('\nFlexDCA connection established to:\n' + self._instID,
                  flush=True)
        except (visa.VisaIOError, visa.InvalidSession):
            print('\nVISA ERROR: Cannot open instrument address.\n',
                  flush=True)
        except Exception as other:
            print('\nVISA ERROR: Cannot connect to instrument:', other,
                  flush=True)

    def write(self, scpi_command):
        """ Sends a scpi command to FlexDCA. SCPI command logged depending on
        _scpi_echo var.

        Args
        ====
        scpi_command
            For example, ':ACQuire:RUN'
        """
        self._instrument.write(scpi_command)
        if self._scpi_echo:
            self.scpi_logger(scpi_command)

    def query(self, scpi_command):
        """ Sends a scpi query to FlexDCA and returns response.
        SCPI query logged depending on _scpi_echo var.

        Args
        ====
        scpi_command
            For example, ':MEASure:OSCilloscope:FALLtime?'
        """
        try:
            response = self._instrument.query(scpi_command)
        except visa.VisaIOError:
            print('\nVISA I/O timeout: ' + scpi_command + '\n', flush=True)
        if self._scpi_echo:
            self.scpi_logger(scpi_command)
        return response

    def query_binary_values(self, message, datatype='B', is_big_endian=False,
                            container=bytes, delay=None, header_fmt='ieee'):
        """ Sends a scpi query to FlexDCA that returns SCPI binary data
        instead of an ASCII string. For example, ':WAVeform:XML:READ? CHAN2A'
        returns binary data.
        var.

        Args
        ====
        message
            SCPI query string.
        datatype
            Set to unsigned bytes for internal format PyVisa's default is
            float. You can change datatype to whatever you need that is
            supported by PyVisa.
        is_big_endian
            FlexDCA's byte order is little-endian by default.
        ieee
            IEEE definite-length block header is automatically stripped
            from returned data.

        Returns
        =======
        Binary data.
        """
        return self._instrument.query_binary_values(message, datatype,
                                                    is_big_endian, container,
                                                    delay, header_fmt)

    def read_raw(self):
        """ Any IEEE definite-length block header is not striped
        from response. """
        return self._instrument.read_raw()

    def write_binary_values(self, message, values, datatype='B',
                            is_big_endian=False, termination=None,
                            encoding=None):
        self._instrument.write_binary_values(message, values, datatype,
                                             termination, encoding)
        # to satisfy ':WAVeform:XML:WRITe? WMEMory2,' as a query
        return self.read_raw()

    def scpi_logger(self, scpi_command):
        """ Prints the command or query to the console and
        query/prints any errors found in FlexDCA's error buffer.
        The do_not_log list is used to prevent sending a
        ':SYSTem:ERROR:COUNt?' or ':NEXT?' query for error logging
        after a specific scpi_command that immediately
        reads a query. For example, this would put FlexDCA back into
        remote mode after a ':SYSTem:GTLocal' which defeats the
        purpose. """

        if '?' in scpi_command:
            print('Query: ', scpi_command, flush=True)
        else:
            print('Write: ', scpi_command, flush=True)
        do_not_log = [':SYSTem:GTLocal',
                      ':DISK:FILE:READ?',
                      ':WAVeform:EYE:INTeger:DATa?',
                      ':WAVeform:XYFORmat:FLOat:XDATa',
                      ':WAVeform:XYFORmat:FLOat:YDATa',
                      ':WAVeform:XML:READ?',
                      ':WAVeform:XML:WRITe?',
                      ':WAVeform:EYE:XML:READ?',
                      ':WAVeform:EYE:XML:WRITe?']
        for item in do_not_log:
            if item in scpi_command:
                # print('Write: ', scpi_command, flush=True)
                return
        error_count = int(self._instrument.query(':SYSTEM:ERRor:COUNt?'))
        if error_count:
            s = ''
            print('SCPI COMMAND ERROR!', flush=True)
            for error in range(0, error_count):
                s += self._instrument.query(':SYSTem:ERRor:NEXT?') + '\n'
            print(s, flush=True)

    def close(self):
        """ Close the Visa connection with the instrument."""
        self._instrument.close()

    @property
    def instID(self):
        """ Returns FlexDCA's identification string. """
        return self._instID

    @property
    def instrument(self):
        """ """
        return self._instrument

    @property
    def timeout(self):
        """ Returns the I/O timeout setting in ms. """
        return self._instrument.timeout

    @timeout.setter
    def timeout(self, timeout):
        """ Sets the I/O timeout setting in ms. """
        self._instrument.timeout = timeout

    @property
    def scpi_echo(self):
        """ Returns the boolean flag for logging SCPI commands. """
        return self._scpi_echo

    @scpi_echo.setter
    def scpi_echo(self, scpi_echo):
        """ Sets the boolean flag for logging SCPI commands. """
        self._scpi_echo = scpi_echo


def install_simulated_module(FlexDCA, channel, model, signal='NRZ'):
    """ Simplified installation of a simulated FlexDCA module.

    Args
    ====
    FlexDCA
        A VisaManager object.
    channel
        Simulated module's channel to use. Installation slot is
        derived from channel.
    model
        Type of simulated module. "DEM" is a dual-electrical module.
        "QEM" is a quad-electrical module. "DOM" is a dual-optical
        module. "QEM" is a electrical-optical module.
    signal
        Format of signal. NRZ or PAM4.

    Returns
    =======
    None
    """
    slot = channel[0]
    FlexDCA.write(':EMODules:SLOT' + slot + ':SELection ' + model)
    if signal in 'NRZ':
        FlexDCA.write(':SOURce' + channel + ':FORMat NRZ')
    else:
        FlexDCA.write(':SOURce' + channel + ':FORMat PAM4')
    FlexDCA.write(':SOURce' + channel + ':DRATe 9.95328E+9')
    FlexDCA.write(':SOURce' + channel + ':WTYPe DATA')
    FlexDCA.write(':SOURce' + channel + ':PLENgth 127')
    FlexDCA.write(':SOURce' + channel + ':AMPLitude 90E-3')
    FlexDCA.write(':SOURce' + channel + ':NOISe:RN 3.0E-6')
    FlexDCA.write(':SOURce' + channel + ':JITTer:RJ 4.0E-12')
    FlexDCA.write(':CHANnel' + channel + ':DISPlay ON')


def all_channels_off(FlexDCA):
    """ Turns all available channels off. """
    for slot in '12345678':
        for letter in 'ABCD':
            channel = slot + letter
            FlexDCA.write(':CHANnel' + channel + ':DISPlay OFF')


def return_scalar(FlexDCA, query):
    """ Returns a FlexDCA scalar measurement result. Uses a loop that checks
    the status of the measurement every 200 ms until the measurement
    result is ready. If the status is invalid 'INV', the loop
    continues waiting for the measurement to be ready.
    If status is questionable 'QUES', an exception is thrown.
    If a valid measurement cannot be returned within the Visa
    timeout setting an exception is thrown.

    Args
    ====
    FlexDCA
        A VisaManager object.
    query
        SCPI query for scalar measurement. For example, ':MEASure:EYE:EWIDth?'

    Returns
    =======
    Measurement result.
    """
    class ScalarMeasQuestionableException(Exception):
        """ A scalar measurement result is questionable. """
        pass

    class ScalarMeasTimeOutException(Exception):
        """ A scalar measurement has timed out. """
        pass

    timeout = FlexDCA.timeout / 1000  # convert ms to s
    query = query.strip('?')
    start_time = time.time()  # time in seconds
    while(True):
        time.sleep(0.2)
        status = FlexDCA.query(query + ':STATus?')
        if 'CORR' in status:  # valid measurement result
            return FlexDCA.query(query + '?')  # get measurement
        elif 'QUES' in status:  # questionable results
            s = query + '\nReason: ' + FlexDCA.query(query + ':STATus:REASon?')
            raise ScalarMeasQuestionableException(s)
        elif (int(time.time() - start_time)) > timeout:  # IO timout
            s = query + '\nReason: ' + FlexDCA.query(query + ':STATus:REASon?')
            raise ScalarMeasTimeOutException(s)


def waveform_acquisition(FlexDCA, count):
    """ Perform an acquisition limit test to capture
    waveform data.

    Args
    ====
    FlexDCA
        A VisaManager object.
    count
        The number of waveforms or patterns to acquire.

    Returns
    =======
    None
    """
    FlexDCA.write(':ACQuire:STOP')  # single acquisition mode
    FlexDCA.write(':ACQuire:CDISplay')  # Clear display
    if '1' in FlexDCA.query(':TRIGger:PLOCk?'):  # pattern lock is on
        FlexDCA.write(':LTESt:ACQuire:CTYPe:PATTerns ' + str(count))
    else:
        FlexDCA.write(':LTESt:ACQuire:CTYPe:WAVeforms ' + str(count))
    FlexDCA.write(':LTESt:ACQuire:STATe ON')
    FlexDCA.query(':ACQuire:RUN;*OPC?')  # OPC required when limit testing
    FlexDCA.write(':LTESt:ACQuire:STATe OFF')


def eng_notation(numstring, resolution):
    """  Converts a string in scientific notation to engineering notation.
     Unit multiplier character is appended to in final return string.

    Args
    ====
    numstring
        Number string for conversion. For example, '12.3e-4'.
    resolution
        An real that indicates number of decimal places in
        the result. For example, '0.01' would give '1.23 m'

    Returns
    =======
    Str representing number with multiplier character.
    """
    import decimal as dc
    if numstring in '9.91E+37':
        return ''
    dc.getcontext().prec = 10  # prevent limiting of decimal places
    multiplier = {12: 'T', 9: 'G', 6: 'M', 3: 'k', 0: '', -3: 'm',
                  -6: MU, -9: 'n', -12: 'p', -15: 'f'}
    numberReal = dc.Decimal(numstring)
    # absolute value is not between 0 and 1 (fraction)
    if abs(numberReal) >= 1:
        exponentMult = 0
        while int(numberReal) != 0:
            numberReal = numberReal / 1000
            exponentMult += 1
        numberReal *= 1000
        exponentMult -= 1
    elif (abs(numberReal) > 0) and (abs(numberReal) < 1):  # fraction
        exponentMult = 0
        while int(numberReal) == 0:
            numberReal = numberReal * 1000
            exponentMult += 1
        exponentMult *= -1
    elif numberReal == 0:  # number must be zero
        exponentMult = 0
    exponentMult *= 3
    if exponentMult == -15:
        n = numberReal.quantize(dc.Decimal('1'))
    else:
        n = numberReal.quantize(dc.Decimal(str(resolution)))
    return str(n) + ' ' + multiplier[exponentMult]


def show_all_constants():
    """ Displays all of the constants with values in this module. To
    be displayed, the font used must include the character. """

    print('All kf module constants:')
    d = [('RED:', 'TCOL4'), ('SALMON:', 'TCOL10'), ('PINK:', 'TCOL6'),
         ('PURPLE:', 'TCOL8'), ('ORANGE:', 'TCOL12'), ('SUNSET:', 'TCOL15'),
         ('GOLD:', 'TCOL7'), ('YELLOW:', 'TCOL1'), ('GREEN:', 'TCOL2'),
         ('MOSS:', 'TCOL16'), ('SEAGREEN:', 'TCOL13'), ('BLUE:', 'TCOL3'),
         ('DARKBLUE:', 'TCOL9'), ('LIGHTBLUE:', 'TCOL5'),
         ('SKYBLUE:', 'TCOL14'), ('VIOLET:', 'TCOL11'),
         ('ALPHAU:', ALPHAU), ('NUU:', NUU), ('BETAU:', BETAU), ('XIU:', XIU),
         ('GAMMAU:', GAMMAU), ('OMICRONU:', OMICRONU), ('DELTAU:', DELTAU),
         ('PIU:', PIU), ('EPSILONU:', EPSILONU), ('RHOU:', RHOU),
         ('ZETAU:', ZETAU), ('SIGMAU:', SIGMAU), ('ETAU:', ETAU),
         ('TAUU:', TAUU), ('THETAU:', THETAU), ('UPSILONU:', UPSILONU),
         ('IOTAU:', IOTAU), ('PHIU:', PHIU), ('KAPPAU:', KAPPAU),
         ('CHIU:', CHIU), ('LAMDAU:', LAMDAU), ('PSIU:', PSIU), ('MUU:', MUU),
         ('OMEGAU:', OMEGAU), ('ALPHA:', ALPHA), ('NU:', NU), ('BETA:', BETA),
         ('XI:', XI), ('GAMMA:', GAMMA), ('OMICRON:', OMICRON),
         ('DELTA:', DELTA), ('PI:', PI), ('EPSILON:', EPSILON), ('RHO:', RHO),
         ('ZETA:', ZETA), ('SIGMA:', SIGMA), ('ETA:', ETA), ('TAU:', TAU),
         ('THETA:', THETA), ('UPSILON:', UPSILON), ('IOTA:', IOTA),
         ('PHI:', PHI), ('KAPPA:', KAPPA), ('CHI:', CHI), ('LAMDA:', LAMDA),
         ('PSI:', PSI), ('MU:', MU), ('OMEGA:', OMEGA),
         ('DEGREE:', DEGREE), ('PLUSSMINUS:', '\u00B1'), ('LTEQ:', '\u2264'),
         ('GTEQ:', '\u2265')
         ]
    i = 0
    while i < len(d):
        if i % 2:
            print('    {0:>10s}  {1:<s}'.format(d[i][0], d[i][1]), end='\n')
        else:
            print('{0:>10s}  {1:<s}'.format(d[i][0], d[i][1]), end='')
        i += 1