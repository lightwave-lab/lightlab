''' Implementation of core peak finding algorithm.
    It is wrapped to be more user-friendly by :meth:`~lightlab.util.data.one_dim.MeasuredFunction.findResonanceFeatures`.

    :class:`ResonanceFeature` is a data storage class
    returned by :meth:`~lightlab.util.data.one_dim.MeasuredFunction.findResonanceFeatures`
'''
import matplotlib.pyplot as plt
import numpy as np
from lightlab import logger

from .function_inversion import descend


class ResonanceFeature(object):
    ''' A data holder for resonance features (i.e. peaks or dips)

        Attributes:
            lam (float): center wavelength
            fwhm (float): full width half maximum -- can be less if the extinction depth is less than half
            amp (float): peak amplitude
            isPeak (float): is it a peak or a dip
    '''

    def __init__(self, lam, fwhm, amp, isPeak=True):
        self.lam = lam
        self.fwhm = fwhm
        self.amp = amp
        self.isPeak = isPeak

    def copy(self):
        ''' Simple copy so you can modify without side effect

            Returns:
                ResonanceFeature: new object
        '''
        return ResonanceFeature(self.lam.copy(), self.fwhm.copy(), self.amp.copy(), self.isPeak)

    def __plottingData(self):
        ''' Gives a polygon represented by 5 points

            Returns:
                list[tuple]: 5-element list of (x,y) tuples representing points of a polygon
        '''
        w = self.fwhm
        x = self.lam - w / 2
        if self.isPeak:
            h = 6
            y = self.amp - h / 2
        else:
            h = -self.amp
            y = self.amp - 3
        return type(self).__box2polygon(x, y, w, h)

    def simplePlot(self, *args, **kwargs):
        r''' Plots a box to visualize the resonance feature

            The box is centered on the peak ``lam`` and ``amp`` with a width of ``fwhm``.

            Args:
                \*args: args passed to ``pyplot.plot``
                \*\*kwargs: kwargs passed to ``pyplot.plot``

            Returns:
                whatever ``pyplot.plot`` returns
        '''
        return plt.plot(*(self.__plottingData() + args), **kwargs)

    @staticmethod
    def __box2polygon(x, y, w, h):
        w = abs(w)
        h = abs(h)
        xa = x * np.ones(5)
        ya = y * np.ones(5)
        xa[1:3] += w
        ya[2:4] += h
        return (xa, ya)


class PeakFinderError(RuntimeError):
    pass


def findPeaks(yArrIn, isPeak=True, isDb=False, expectedCnt=1, descendMin=1, descendMax=3, minSep=0):
    '''Takes an array and finds a specified number of peaks

        Looks for maxima/minima that are separated from others, and
        stops after finding ``expectedCnt``

        Args:
            isDb (bool): treats dips like DB dips, so their width is relative to outside the peak, not inside
            descendMin (float): minimum amount to descend to be classified as a peak
            descendMax (float): amount to descend down from the peaks to get the width (i.e. FWHM is default)
            minSep (int): the minimum spacing between two peaks, in array index units

        Returns:
            array (float): indeces of peaks, sorted from biggest peak to smallest peak
            array (float): width of peaks, in array index units

        Raises:
            Exception: if not enough peaks found. This plots on fail, so you can see what's going on
    '''
    xArr = np.arange(len(yArrIn))
    yArr = yArrIn.copy()
    sepInds = int(np.floor(minSep))

    pkInds = np.zeros(expectedCnt, dtype=int)
    pkWids = np.zeros(expectedCnt)
    blanked = np.zeros(xArr.shape, dtype=bool)

    if not isPeak:
        yArr = 0 - yArr

    descendBy = descendMax

    yArrOrig = yArr.copy()

    for iPk in range(expectedCnt):  # Loop over peaks
        logger.debug('--iPk = %s', iPk)
        isValidPeak = False
        for iAttempt in range(1000):  # Loop through falsities like edges and previously found peaks
            if isValidPeak:
                break
            logger.debug('Attempting to find actual')
            indOfMax = yArr.argmax()
            peakAmp = yArr[indOfMax]
            if isPeak or not isDb:
                absThresh = peakAmp - descendBy
            else:
                absThresh = min(descendBy, peakAmp - descendBy)
            logger.debug('absThresh = %s', absThresh)

            # Didn't find a peak anywhere
            if blanked.all() or absThresh <= np.amin(yArr) or iAttempt == 999:
                descendBy -= .5                             # Try reducing the selectivity
                if descendBy >= descendMin:
                    logger.debug('Reducing required descent to %s', descendBy)
                    continue
                else:
                    # plot a debug view of the spectrum that throws an error when exited
                    logger.warning('Found %s of %s peaks. Look at the plot.', iPk, expectedCnt)
                    plt.plot(yArr)
                    plt.plot(yArrOrig)
                    plt.show(block=True)
                    raise PeakFinderError('Did not find enough peaks exceeding threshold')

            # descend data down by a threshold amount
            logger.debug('-Left side')
            indL, validL = descend(yArr, blanked, indOfMax - sepInds, 'left', absThresh)
            logger.debug('-Right side')
            indR, validR = descend(yArr, blanked, indOfMax + sepInds, 'right', absThresh)
            hmInds = [indL, indR + 1]
            isValidPeak = validL and validR
            # throw out data around this peak by minimizing yArr and recording as blank
            yArr[hmInds[0]:hmInds[1]] = np.amin(yArr)
            blanked[hmInds[0]:hmInds[1]] = True
        logger.debug('Successfully found a peak')
        pkInds[iPk] = int(np.mean(hmInds))
        pkWids[iPk] = np.diff(hmInds)[0]
    return pkInds, pkWids
