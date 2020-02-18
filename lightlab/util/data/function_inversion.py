''' Finding the x-value that provides a targeted y-value for measured functions
'''

import numpy as np
from lightlab import logger


def descend(yArr, invalidIndeces, startIndex, direction, threshVal):
    ''' From the start index, descend until reaching a threshold level and return that index
    If it runs into the invalidIndeces or an edge, returns i at the edge of validity and False for validPeak
    '''
    iterUntilFail = len(yArr)  # number of tries before giving up to avoid hang
    if direction in [0, -1, 'left']:
        sideSgn = -1
    elif direction in [1, 'right']:
        sideSgn = 1
    i = startIndex
    validPeak = True
    tooCloseToEdge = False
    tooCloseToOtherPeak = False
    for _ in range(iterUntilFail):
        if not validPeak:
            break

        if i + sideSgn <= -1 or i + sideSgn > len(yArr):
            tooCloseToEdge = True
            logger.debug('Descend: too close to edge of available range')
        if invalidIndeces[i]:
            tooCloseToOtherPeak = True
            logger.debug('Descend: too close to another peak')
        validPeak = not tooCloseToEdge and not tooCloseToOtherPeak

        if yArr[i] <= threshVal:
            break

        # logger.debug('Index %s: blanked=%s, yArr=%s', i, invalidIndeces[i], yArr[i])
        i += sideSgn
    else:
        validPeak = False
    return i, validPeak


def interpInverse(xArrIn, yArrIn, startIndex, direction, threshVal):
    ''' Gives a float representing the interpolated x value that gives y=threshVal '''
    xArr = xArrIn.copy()
    yArr = yArrIn.copy()
    if direction == 'left':
        xArr = xArr[::-1]
        yArr = yArr[::-1]
        startIndex = len(xArr) - 1 - startIndex
    xArr = xArr[startIndex:]
    yArr = yArr[startIndex:]
    yArr = yArr - threshVal

    possibleRange = (np.min(yArrIn), np.max(yArrIn))
    # warnStr = 'Inversion requested y = {}, but {} of range is {}'
    if threshVal < possibleRange[0]:
        logger.warning('Inversion requested y = %s, but %s of range is %s',
                       threshVal, 'minimum', np.min(yArrIn))
        return xArr[-1]
    elif threshVal > possibleRange[1]:
        logger.warning('Inversion requested y = %s, but %s of range is %s',
                       threshVal, 'maximum', np.max(yArrIn))
        return xArr[0]

    fakeInvalidIndeces = np.zeros(len(yArr), dtype=bool)
    iHit, isValid = descend(yArr, fakeInvalidIndeces, startIndex=0, direction='right', threshVal=0)
    if not isValid:
        logger.warning('Did not descend across threshold. Returning minimum')
        return xArr[np.argmin(yArr)]
    elif iHit in [0]:
        return xArr[iHit]
    else:  # interpolate
        q = yArr[iHit - 1:iHit + 1][::-1]
        v = xArr[iHit - 1:iHit + 1][::-1]
        return np.interp(0, q, v)
