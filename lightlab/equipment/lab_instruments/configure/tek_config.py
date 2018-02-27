import dpath
import json
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
    def __init__(self, initDict={}):
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
            val = dpath.util.get(self.dico, cStr, separator=':')
        except KeyError:
            raise KeyError(cStr + ' is not present in this TekConfig instance')
        if not asCmd:
            return val
        else:
            return (cStr, str(val))

    def set(self, cStr, val):
        ''' Takes the value only, not a dictionary '''
        # First check that it does not exist as a subdir
        try:
            ex = self.get(cStr, asCmd=False)
            if type(ex) is dict:
                # we don't want to overwrite this subdirectory, so put a tag on cmd
                cStr = cStr + ':&'
        except KeyError:
            # doesn't exist, we are good to go
            pass

        cmd = (cStr, val)
        success = dpath.util.set(self.dico, *cmd, separator=':')
        if success != 1: # it doesn't exist yet
            try:
                dpath.util.new(self.dico, *cmd, separator=':')
            except ValueError as e:
                # We probably have an integer leaf where we would also like to have a directory
                parent = ':'.join(cmd[0].split(':')[:-1])
                try:
                    oldV = self.get(parent, asCmd=False)
                except KeyError as e:
                    print('dpath did not take ' + str(cmd))
                    raise e
                dpath.util.set(self.dico, parent, {'&': oldV}, separator=':')
                dpath.util.new(self.dico, *cmd, separator=':')

    def getList(self, subgroup='', asCmd=True):
        ''' Deep crawler that goes in and generates a command for every leaf.

            Args:
                subgroup (str): subgroup must be a subdirectory. If '', it is root directory. It can also be a command string, in which case, the returned list has length 1
                asCmd (bool): if false, returns a list of strings that can be sent to scopes

            Returns:
                list: list of valid commands (cstr, val) on the subgroup subdirectory
        '''
        cList = []
        children = dpath.util.search(self.dico, subgroup + '*', yielded=True, separator=':')
        for cmd in children:
            s, v = cmd
            if type(v) is not dict:
                if s[0] != ':':
                    s = ':' + s
                cList += [(s, v)]
            else:
                cList += self.getList(subgroup=cmd[0] + ':')
        if asCmd:
            return cList
        else:
            writeList = [None] * len(cList)
            for i, cmd in enumerate(cList):
                cStr, val = cmd
                if cStr[-1] == '&': # check for tokens
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
                subgroup (str): subgroup must be a subdirectory. If '', it is root directory. It can also be a command string, in which case, only that parameter is affected
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
        from pathlib import Path
        fpath = Path(fname)
        with fpath.open('r') as fx:
            d = json.load(fx)
        full = cls(d)
        ret = cls()
        ret.transfer(full, subgroup=subgroup)
        return ret

    @staticmethod
    def __parseShorthand(setResponse):
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
            if cmdLeaf[0] == ':':
                pat = cmdLeaf[1:]
                cmdGrp = ':'.join(pat.split(':')[:-1])
            else:
                pat = cmdGrp + ':' + cmdLeaf
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
            overwrite=True

        if overwrite:
            configToSave = type(self)()
            configToSave.transfer(self, subgroup=subgroup)
        else:
            configToSave = existingConfig.transfer(self, subgroup=subgroup)

        from pathlib import Path
        fpath = Path(fname)
        with fpath.open('w+') as fx:
            fx.write(str(configToSave)) # __str__ gives nice json format
