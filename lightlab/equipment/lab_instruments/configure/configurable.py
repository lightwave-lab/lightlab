from .tek_config import TekConfig
from lightlab import logger
import pyvisa


class AccessException(Exception):
    pass


class Configurable(object):
    ''' Instruments can be configurable and use TekConfig.

        This clas uses query/write methods that are not directly inherited, so the subclass or its parents must implement those functions
    '''
    defaultFileDir = '../../lightlab/equipment/savedScopeConfigs/defaults/'

    def __init__(self, headerIsOptional=True, verboseIsOptional=False, precedingColon=True, interveningSpace=True, **kwargs):

        self._hardwareinit = False

        self.verboseIsOptional = verboseIsOptional
        self.headerIsOptional = headerIsOptional

        self.header = not headerIsOptional
        self.colon = precedingColon
        self.space = interveningSpace

        self.config = {}
        self.config['default'] = None
        self.config['live'] = TekConfig()

        super().__init__(**kwargs)

    def initHardware(self):
        if not self._hardwareinit:
            if self.verboseIsOptional:
                self.write('VERBOSE ON')
            if self.headerIsOptional:
                self.write('HEADER OFF')
            self._hardwareinit = True
        return self._hardwareinit

    # Configration methods
    def getDefaultFilename(self):
        # Typically: manufacturer, model#, serial#, <other stuff with strange
        # chars>
        info = self.instrID().split(',')
        deffile = Configurable.defaultFileDir + '-'.join(info[:3]) + '.json'
        return deffile

    # Simple, individual getter and setter
    def setConfigParam(self, cStr, val=None, forceHardware=False):
        ''' Sets an individual configuration parameter

            forceHardware means it will always send to hardware,
                in case it is critical and tends to be changed by pesky lab users
        '''
        if val is None:
            val = ''
        try:
            prevVal = self.config['live'].get(cStr, asCmd=False)
            refresh = (str(val) != str(prevVal))
        except KeyError:
            refresh = True
        if refresh or forceHardware:
            self.config['live'].set(cStr, val)
            self._setHardwareConfig(cStr)  # send only the one that changed

    def getConfigParam(self, cStr, forceHardware=False):
        ''' This assumes that nobody in lab touched anything and is much faster than getting from hardware.

            If the command is not recognized, attempts to get it from hardware
        '''
        if not forceHardware:
            try:
                return self.config['live'].get(cStr, asCmd=False)
            except KeyError:  # not in the current structure, try getting from hardware
                pass
        # get it from hardware
        self._getHardwareConfig(cStr)
        return self.config['live'].get(cStr, asCmd=False)

    # More specialized access methods that handle command subgroups, files,
    # and tokens
    def saveConfig(self, dest='+user', subgroup='', overwrite=False):
        ''' This only works with files. Reason being that I prefer not to have the user playing with TekConfig objects directly.

            If you would like to setup a temporary state (i.e. taking some measurements and going back), use a file and `subgroup=`

            Args:
                subgroup (str): a group of commands or a single command. If '', it means everything.

            Returns:
                nothing

            Side effects:
                if dest is object or dict, modifies it
                if dest is token, modifies the config library of self
                if dest is filename, writes that file
        '''
        if type(dest) in [TekConfig, dict]:
            dest.transfer(self.config['live'], subgroup=subgroup)
        elif type(dest) is str and dest[0] == '+':  # tokens
            if dest[1:] in ['default, init']:
                raise AccessException(
                    'You are not allowed to change defaults or initialization history')
            self.config[dest[1:]] = TekConfig()
            self.config[dest[1:]].transfer(
                self.config['live'], subgroup=subgroup)
        elif type(dest) is str:
            self.config['live'].save(dest, subgroup, overwrite)
        else:
            raise Exception(
                'Invalid save destination. It must be a file, token, or TekConfig object')

    def loadConfig(self, source='+user', subgroup=''):
        ''' Loads some configuration parameters from a source which is either:

                * a file name string, or
                * a special token ['+default' or '+init'], or
                * some TekConfig object or dict you have out there

            Args:
                source (str/TekConfig): load source
                subgroup (str): a group of commands or a single command. If '', it means everything.

            Returns:
                nothing
        '''
        if type(source) in [TekConfig, dict]:
            srcObj = source
        elif type(source) is str and source[0] == '+':  # tokens
            if source[1:] == 'default' and self.config['default'] is None:  # need to load default
                self.config['default'] = TekConfig.fromFile(
                    self.getDefaultFilename())
            srcObj = self.config[source[1:]]
        elif type(source) is str:
            srcObj = TekConfig.fromFile(source)
        else:
            raise Exception(
                'Invalid load source. It must be a file, token, or TekConfig object')

        self.config['live'].transfer(srcObj, subgroup=subgroup)
        # This writes everything without checking how it is set currently
        self._setHardwareConfig(subgroup)

    # Hardware interface. User is not allowed to access directly.
    # This class is setup so that the hardware state is reflected exactly in the 'live' config
    #   Unless somebody changes something in lab
    def __getFullHardwareConfig(self, subgroup=''):
        ''' Get everything that is returned by the SET? query

            Args:
                subgroup (str): default '' means everything

            Returns:
                TekConfig: structured configuration object
        '''
        self.initHardware()
        try:
            resp = self.query('SET?')
            return TekConfig.fromSETresponse(resp, subgroup=subgroup)
        except pyvisa.VisaIOError as e:  # SET timed out. You are done.
            print(self.instrID() +
                  ': timed out on \'SET?\'. Try resetting with \'*RST\'.')
            raise e

    def _getHardwareConfig(self, cStrList):
        ''' Queries all or a subgroup of commands using the state of the 'live' config.

            This does not return, but it puts it in the config['live'] attribute

            Args:
                cStrList (list or str): list of command strings. Can also be a scalar string
        '''
        self.initHardware()
        if type(cStrList) is not list and type(cStrList) is str:
            cStrList = [cStrList]
        for cStr in cStrList:
            if cStr[-1] == '&':  # handle the sibling subdir token
                cStr = cStr[:-2]
            logger.debug('Querying ' + str(cStr) +
                         ' from configurable hardware')
            ret = self.query(cStr + '?')
            if self.header:
                val = ret.split(' ')[-1]
            else:
                val = ret
            self.config['live'].set(cStr, val)

    def _setHardwareConfig(self, subgroup=''):
        ''' Writes all or a subgroup of commands using the state of the 'live' config.

            Args:
                subgroup (str): a subgroup of commands. If '', we write everything
        '''
        self.initHardware()
        live = self.config['live'].getList(subgroup, asCmd=False)
        for cmd in live:
            if not self.colon and cmd[0] == ':':
                cmd = cmd[1:]
            if not self.space:
                ''.join(cmd.split(' '))
            logger.debug('Sending ' + str(cmd) + ' to configurable hardware')
            self.write(cmd)
