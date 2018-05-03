
class ChannelError(Exception):
    pass


class RangeError(Exception):
    ''' It is useful to put the type of error 'high' or 'low' in the second
        argument of this class' initializer
    '''
    pass


class DeprecatedError(Exception):
    ''' Make sure to describe the new alternative
    '''
    pass
