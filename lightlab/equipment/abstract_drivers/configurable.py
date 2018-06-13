from lightlab import visalogger as logger
from pyvisa import VisaIOError
from contextlib import contextmanager
import dpath
import json
from numpy import floor
from pathlib import Path

from lightlab.util.io import lightlabDevelopmentDir
defaultFileDir = lightlabDevelopmentDir / 'savedConfigDefaults/'

from . import AbstractDriver


class AccessException(Exception):
    pass


class TekConfig(object):
    ''' Wraps a dictionary attribute. Uses dpath for operations.

        Commands are defined as tuples (cStr, val). For example (':PATH:TO:CMD', 4).
            Use these by doing scope.write(' '.join(TekConfig.get('PATH:TO:CMD')))
            The val is always a string.

        Todo:
            :transferring subgroup from one instance to another.
            :returning a dictionary representing a subgroup (actually this might currently be happening in error)
            :transferring subgroup values to a different subgroup in the same instance (for example, CH1 to CH2)
    '''
    separator = ':'

    def __init__(self, initDict=None):
        if initDict is None:
            initDict = dict()
        self.dico = initDict.copy()

    def __str__(self):
        return json.dumps(self.dico, indent=2, sort_keys=True)

    def print(self, subgroup=''):
        sub = type(self)()
        sub.transfer(self, subgroup=subgroup)
        print(sub)

    def copy(self, subgroup=''):
        ret = type(self)()
        ret.transfer(self, subgroup=subgroup)
        return ret

    def get(self, cStr, asCmd=True):
        ''' Returns the value only, not a dictionary

            Args:
                asCmd (bool): if true, returns a tuple representing a command. Otherwise returns just the value
        '''
        try:
            val = dpath.util.get(self.dico, cStr, separator=self.separator)
        except KeyError:
            raise KeyError(cStr + ' is not present in this TekConfig instance')
        if type(val) is dict and '&' in val.keys():
            val = val['&']
        if not asCmd:
            return val
        else:
            return (cStr, str(val))

    def set(self, cStr, val):
        ''' Takes the value only, not a dictionary '''
        # First check that it does not exist as a subdir
        try:
            ex = dpath.util.get(self.dico, cStr, separator=self.separator)
        except KeyError:
            # doesn't exist, we are good to go
            pass
        else:
            if type(ex) is dict:
                # we don't want to overwrite this subdirectory, so put a tag on cmd
                cStr = cStr + self.separator + '&'

        cmd = (cStr, val)
        success = dpath.util.set(self.dico, *cmd, separator=self.separator)
        if success != 1:  # it doesn't exist yet
            try:
                dpath.util.new(self.dico, *cmd, separator=self.separator)
            except ValueError as e:
                # We probably have an integer leaf where we would also like to have a directory
                parent = self.separator.join(cmd[0].split(self.separator)[:-1])
                try:
                    oldV = self.get(parent, asCmd=False)
                except KeyError as e:
                    print('dpath did not take ' + str(cmd))
                    raise e
                dpath.util.set(self.dico, parent, {'&': oldV}, separator=self.separator)
                dpath.util.new(self.dico, *cmd, separator=self.separator)

    def getList(self, subgroup='', asCmd=True):
        ''' Deep crawler that goes in and generates a command for every leaf.

            Args:
                subgroup (str): subgroup must be a subdirectory. If '', it is root directory. It can also be a command string, in which case, the returned list has length 1
                asCmd (bool): if false, returns a list of strings that can be sent to scopes

            Returns:
                list: list of valid commands (cstr, val) on the subgroup subdirectory
        '''
        cList = []
        children = dpath.util.search(self.dico, subgroup + '*',
                                     yielded=True, separator=self.separator)
        for cmd in children:
            s, v = cmd
            if type(v) is not dict:
                if s[0] != self.separator:
                    s = self.separator + s
                cList += [(s, v)]
            else:
                cList += self.getList(subgroup=cmd[0] + self.separator)
        if asCmd:
            return cList
        else:
            writeList = [None] * len(cList)
            for i, cmd in enumerate(cList):
                cStr, val = cmd
                if cStr[-1] == '&':  # check for tokens
                    cStr = cStr[:-2]
                writeList[i] = cStr + ' ' + str(val)
            return writeList

    def setList(self, cmdList):
        ''' The inverse of getList '''
        for c in cmdList:
            self.set(*c)

    def transfer(self, source, subgroup=''):
        ''' Pulls config from the source TekConfig object. This is useful for subgrouping.

            For example, you might want to load from default only the trigger configuration.

            Args:
                source (TekConfig or dict): the object from which config values are pulled into self
                subgroup (str): subgroup must be a subdirectory. If '', it is root directory.
                    It can also be a command string, in which case, only that parameter is affected
        '''
        if type(source) is dict:
            sCon = type(self)(source)
        elif type(source) is type(self):
            sCon = source
        else:
            raise Exception('Invalid source for transfer. Got ' + str(type(source)))
        commands = sCon.getList(subgroup=subgroup)
        self.setList(commands)

    @classmethod
    def fromFile(cls, fname, subgroup=''):
        fpath = Path(fname)
        with fpath.open('r') as fx:
            d = json.load(fx)
        full = cls(d)
        ret = cls()
        ret.transfer(full, subgroup=subgroup)
        return ret

    @classmethod
    def __parseShorthand(cls, setResponse):
        ''' Turns shorthand multi-command strings into list of proper command tuples
        '''
        pairs = setResponse.split(';')

        commands = [None] * len(pairs)
        cmdGrp = None
        for i in range(len(pairs)):
            words = pairs[i].split(' ')
            cmdLeaf, val = words[0:2]
            if len(words) > 2:
                print('Warning 2-value returns not handled by TekConfig class. Ignoring...')
                print(*words)
            if cmdLeaf[0] == cls.separator:
                pat = cmdLeaf[1:]
                cmdGrp = cls.separator.join(pat.split(cls.separator)[:-1])
            else:
                pat = cmdGrp + cls.separator + cmdLeaf
            commands[i] = (pat, val)
        return commands

    @classmethod
    def fromSETresponse(cls, setResponse, subgroup=''):
        ''' setResponse (str): what is returned by the scope in response to query('SET?')

            It will require some parsing for subgroup shorthand
        '''
        commandList = cls.__parseShorthand(setResponse)
        full = cls()
        full.setList(commandList)
        if subgroup == '':
            return full
        else:
            ret = cls()
            ret.transfer(full, subgroup=subgroup)
            return ret

    def save(self, fname, subgroup='', overwrite=False):
        ''' Saves dictionary parameters in json format. Merges if there's something already there, unless overwrite is True.

            Args:
                fname (str): file name
                subgroup (str): groups of commands to write. If '', it is everything.
                overwrite (bool): will make a new file exactly corresponding to this instance, otherwise merges with existing
        '''
        try:
            existingConfig = TekConfig.fromFile(fname)
        except FileNotFoundError:
            # file probably doesn't exist
            existingConfig = None
            overwrite = True

        if overwrite:
            configToSave = type(self)()
            configToSave.transfer(self, subgroup=subgroup)
        else:
            configToSave = existingConfig.transfer(self, subgroup=subgroup)

        fpath = Path(fname)
        with fpath.open('w+') as fx:
            fx.write(str(configToSave))  # __str__ gives nice json format


# pylint: disable=no-member
class Configurable(AbstractDriver):
    ''' Instruments can be configurable to keep track of settings within the instrument

        This class is setup so that the hardware state is reflected exactly in the 'live' config
        **unless somebody changes something in lab**.
        Watch out for that and use ``forceHardware`` if that is a risk

        This clas uses query/write methods that are not directly inherited,
        so the subclass or its parents must implement those functions
    '''

    config = None  #: Dictionary of :class:`TekConfig` objects.

    def __init__(self, headerIsOptional=True, verboseIsOptional=False, precedingColon=True, interveningSpace=True, **kwargs):

        self._hardwareinit = False

        self.verboseIsOptional = verboseIsOptional
        self.headerIsOptional = headerIsOptional

        self.header = not headerIsOptional
        self.colon = precedingColon
        self.space = interveningSpace

        self.config = dict()
        self.config['default'] = None
        self.config['init'] = TekConfig()
        self.config['live'] = TekConfig()
        self.separator = self.config['live'].separator

        super().__init__(**kwargs)

    def initHardware(self):
        ''' Runs upon first hardware access.
            Tells the instrument how to format its commands
        '''
        if not self._hardwareinit:
            if self.verboseIsOptional:
                self.write('VERBOSE ON')
            if self.headerIsOptional:
                self.write('HEADER OFF')
            self._hardwareinit = True
        return self._hardwareinit

    # Simple, individual getter and setter
    def setConfigParam(self, cStr, val=None, forceHardware=False):
        ''' Sets an individual configuration parameter.
            If the value has been read before, and there is no change,
            then it will **not** write to the hardware.

            Args:
                cStr (str): name of the command
                val (any): value to send. Detects type, so if it's an int, it will be stored as int
                forceHardware (bool): will always send to hardware,
                    in case it is critical or if it tends to be changed by pesky lab users

            Returns:
                (bool): Did it requre a write to hardware?
        '''
        if val is None:
            val = ''
        try:
            prevVal = self.config['live'].get(cStr, asCmd=False)
        except KeyError:
            prevVal = None
            refresh = True
        else:
            refresh = (str(val) != str(prevVal))
        if refresh or forceHardware:
            self.config['live'].set(cStr, val)
            if prevVal is None:
                self.config['init'].transfer(self.config['live'], cStr)
            self._setHardwareConfig(cStr)  # send only the one that changed
            return True
        else:
            return False

    def getConfigParam(self, cStr, forceHardware=False):
        ''' Gets a single parameter.
            If the value has been read before, and there is no change,
            then it will **not** query the hardware.

            This is much faster than getting from hardware; however,
            it assumes that nobody in lab touched anything.

            Args:
                cStr (str): name of the command
                forceHardware (bool): will always query from hardware,
                    in case it is critical or if it tends to be changed by pesky lab users

            Returns:
                (any): command value. Detects type, so that ``'2.5'`` will return as ``float``

            If the command is not recognized, attempts to get it from hardware
        '''
        try:
            prevVal = self.config['live'].get(cStr, asCmd=False)
        except KeyError:
            prevVal = None
        if prevVal is None or forceHardware:  # Try getting from hardware
            self._getHardwareConfig(cStr)
        if prevVal is None:  # This is the first time getting, so it goes in 'init'
            self.config['init'].transfer(self.config['live'], cStr)
        return self.config['live'].get(cStr, asCmd=False)

    @contextmanager
    def tempConfig(self, cStr, tempVal, forceHardware=False):
        ''' Changes a parameter within the context of a "with" block.
            Args are same as in :meth:`getConfigParam`.
        '''
        oldVal = self.getConfigParam(cStr, forceHardware)
        try:
            self.setConfigParam(cStr, tempVal)
            yield self
        finally:
            self.setConfigParam(cStr, oldVal)

    def getDefaultFilename(self):
        r''' Combines the :data:`lightlab.util.io.paths.defaultFileDir`
            with the \*IDN? string of this instrument.

            Returns:
                (str): the default filename
        '''
        info = self.instrID().split(',')
        deffile = defaultFileDir / '-'.join(info[:3]) + '.json'
        return deffile

    def saveConfig(self, dest='+user', subgroup='', overwrite=False):
        '''

            If you would like to setup a temporary state (i.e. taking some measurements and going back), use a file and `subgroup=`

            Args:
                subgroup (str): a group of commands or a single command. If '', it means everything.

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

        for liveInit in ['live', 'init']:
            self.config[liveInit].transfer(srcObj, subgroup=subgroup)
        # This writes everything without checking how it is set currently
        self._setHardwareConfig(subgroup)

    def __getFullHardwareConfig(self, subgroup=''):
        ''' Get everything that is returned by the SET? query

            Args:
                subgroup (str): default '' means everything

            Returns:
                TekConfig: structured configuration object
        '''
        self.initHardware()
        logger.info('Querying SET? response of %s', self.instrID())
        try:
            resp = self.query('SET?')
            return TekConfig.fromSETresponse(resp, subgroup=subgroup)
        except VisaIOError as err:  # SET timed out. You are done.
            logger.error('%s timed out on \'SET?\'. \
                         Try resetting with \'*RST\'.', self.instrID())
            raise err

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

            try:
                ret = self.query(cStr + '?')
            except VisaIOError:
                logger.error('Problematic parameter was %s.\n'
                             'Likely it does not exist in this instrument command structure.', cStr)
                raise
            logger.debug('Queried %s, got %s', cStr, ret)

            if self.header:
                val = ret.split(' ')[-1]
            else:
                val = ret
            # Type detection
            try:
                val = float(val)
            except ValueError:
                pass
            else:
                if val == floor(val):
                    val = int(val)
            self.config['live'].set(cStr, val)

    def _setHardwareConfig(self, subgroup=''):
        ''' Writes all or a subgroup of commands using the state of the 'live' config.

            Args:
                subgroup (str): a subgroup of commands. If '', we write everything
        '''
        self.initHardware()
        live = self.config['live'].getList(subgroup, asCmd=False)
        for cmd in live:
            if not self.colon and cmd[0] == self.separator:
                cmd = cmd[1:]
            if not self.space:
                ''.join(cmd.split(' '))
            logger.debug('Sending %s to configurable hardware', cmd)
            self.write(cmd)

    def generateDefaults(self, filename=None, overwrite=False):
        ''' Attempts to read every configuration parameter.
            Handles several cases where certain parameters do not make sense and must be skipped

            Generates a new default file which is saved
            in configurable.defaultFileDir

            *This takes a while.*

            Args:
                filename (str): simple name. You can't control the directory.
                overwrite (bool): If False, stops if the file already exists.
        '''
        if filename is None:
            filename = self.getDefaultFilename()
        if Path(filename).exists() and not overwrite:
            logger.warning('%s already exists.'
                           'Use `overwrite` if you really want.', filename)
            return

        allConfig = self.__getFullHardwareConfig()
        allSetCmds = allConfig.getList('', asCmd=True)

        cfgBuild = TekConfig()

        for cmd in allSetCmds:
            if cmd[0][-1] != '&':  # handle the sibling subdir token
                cStr = cmd[0]
            else:
                cStr = cmd[0][:-2]
            try:
                val = self.query(cStr + '?', withTimeout=1000)
                cfgBuild.set(cStr, val)
                logger.info(cStr, '<--', val)
            except VisaIOError:
                logger.info(cStr, 'X -- skipping')

        cfgBuild.save(filename)
        logger.info('New default saved to %s', filename)
# pylint: enable=no-member
