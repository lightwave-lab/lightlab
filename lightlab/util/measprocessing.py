''' Useful stuff having to do with measurement processing.
For example, if you want to set up a spectrum transmission baseline, or a weight functional basis
Generally, these states are not device states, but could change from day to day
'''
import numpy as np

from lightlab import logger


class SpectrumMeasurementAssistant(object):
    ''' Class for preprocessing measured spectra
    Calculates background spectra by 1) smoothing, 2) tuning/splicing, and 3) peak nulling
    Also handles resonance finding (This could move to a separate manager or external function)
    Interfaces directly with OSA. It DOES NOT set tuning states.
    '''
    useBgs = ['tuned', 'smoothed', 'const']  # The order matters
    bgSmoothDefault = 2.0  # in nm

    def __init__(self, nChan=1, arePeaks=False, osaRef=None):
        self.nChan = nChan
        self.arePeaks = arePeaks
        if osaRef is None:
            print('Warning: osa is not initialized as of laboratory-state update. It will be phony')
        self.osa = osaRef
        self.__backgrounds = {}
        # self.__bgSmoothed = None # Constant background spectrum due to fading, EDFA profile, etc.
        # self.__bgTuned = None # Constant background taking into account resonance tuning
        # self.__bgNulled = None # Constant background using resonance shapes
        self.peakfinderOptions = {}
        self.filtShapesForConvolution = None

    def rawSpect(self, avgCnt=1):
        if self.osa is None:
            raise Exception('This is a phony instance with no spectrum analyzer present')
        return self.osa.spectrum(avgCnt)

    def fgSpect(self, avgCnt=1, raw=None, bgType=None):
        ''' Returns the current spectrum with background removed.

            Also plots so you can see what's going on, if visualize mode was specified

            If raw is specified, does not sweep, just removes background
        '''
        if raw is None:
            raw = self.rawSpect(avgCnt=avgCnt)
        bg = self.getBgSpect(bgType)
        if bgType is None and type(bg) is float and bg == 0:
            self.setBgSmoothed(raw)
        unbiased = raw - bg
        return unbiased

    def resonances(self, spect=None, avgCnt=1):
        ''' Returns the current wavelengths of detected peaks in order sorted by wavelength.
        Uses the simple findPeaks function, but it could later use a convolutive peak finder for more accuracy.
        :param spect: if this is specified, then a new spectrum will not be taken
        '''
        if spect is None:
            spect = self.fgSpect(avgCnt=avgCnt)
        # Standard peak finder
        res = spect.findResonanceFeatures(
            expectedCnt=self.nChan, isPeak=self.arePeaks, **self.peakfinderOptions)
        # Advanced correlation based peak finder
        if self.filtShapesForConvolution is not None:
            fineRes, confidence = spect.refineResonanceWavelengths(  # pylint: disable=unused-variable
                self.filtShapesForConvolution, seedRes=res)
            res = fineRes
        lamSort = np.argsort([r.lam for r in res])
        return res[lamSort]

    def killResonances(self, spect=None, avgCnt=1, fwhmsAround=3.):
        '''
        '''
        if spect is None:
            spect = self.fgSpect(avgCnt=avgCnt)
        processed = spect.copy()
        for r in self.resonances(spect):
            segmentAroundPeak = r.lam + r.fwhm * fwhmsAround / 2 * np.array([-1, 1])
            processed = processed.deleteSegment(segmentAroundPeak)
        return processed

    def fgResPlot(self, spect=None, axis=None, avgCnt=1):  # pylint: disable=unused-argument
        ''' Takes a foreground spectrum, plots it and its peaks.
        Currently the axis input is unused.
        '''
        if spect is None:
            spect = self.fgSpect(avgCnt)
        res = self.resonances(spect)
        spect.simplePlot()
        for r in res:
            r.simplePlot()

    def setBgConst(self, raw=None):
        ''' Makes a background the maximum transmission observed '''
        if raw is None:
            raw = self.rawSpect()
        self.__backgrounds['const'] = max(raw.ordi)
        self.__backgrounds['smoothed'] = max(raw.ordi)

    def setBgSmoothed(self, raw=None, smoothNm=None):
        ''' Attempts to find background using a low-pass filter.
        Does not return. Stores results in the assistant variables.
        '''
        if raw is None:
            raw = self.rawSpect()
        if smoothNm is None:
            smoothNm = self.bgSmoothDefault
        if self.arePeaks:
            logger.debug('Warning fake background spectrum is being used on the drop port')
            self.setBgConst(raw)
        else:
            self.__backgrounds['smoothed'] = raw.lowPass(windowWidth=smoothNm)

    def setBgTuned(self, base, displaced):
        ''' Insert the pieces of the displaced spectrum into where the peaks are
            It is assumed that these spectra were taken with this object's fgSpect method
        '''
        if self.arePeaks:
            logger.debug('Warning fake background spectrum is being used on the drop port')
            self.__backgrounds['tuned'] = self.getBgSpect()
            return
        res = self.resonances(base)
        baseRaw = base + self.getBgSpect()
        displacedRaw = displaced + self.getBgSpect()
        for r in res:
            spliceWind = r.lam + 6 * r.fwhm * np.array([-1, 1]) / 2
            baseRaw = baseRaw.splice(displacedRaw, segment=spliceWind)
        self.__backgrounds['tuned'] = baseRaw

    def setBgNulled(self, filtShapes, avgCnt=3):
        ''' Uses the peak shape information to null out resonances
        This gives the best estimate of background INDEPENDENT of the tuning state.
        It is assumed that the fine background taken by tuning is present, and the filter shapes were taken with that
        spect should be a foreground spect, but be careful when it is also derived from bgNulled
        '''
        if self.arePeaks:
            logger.debug('Warning, null-based background spectrum not used for drop port. Ignoring')
            self.__backgrounds['nulled'] = self.getBgSpect()
        else:
            spect = self.fgSpect(avgCnt, bgType='tuned')
            newBg = spect.copy()
            for i, r in enumerate(self.resonances(newBg)):
                nulledPiece = spect - filtShapes[i].db().shift(r.lam)
                newBg = newBg.splice(nulledPiece)
            self.__backgrounds['nulled'] = self.getBgSpect(bgType='tuned') - newBg

    def getBgSpect(self, bgType=None):
        preferredOrder = self.useBgs
        if bgType is None:
            for k in preferredOrder:
                try:
                    return self.__backgrounds[k]
                except KeyError:
                    pass
            return 0
            # raise Exception('No background spectrum has been taken')
        elif bgType in preferredOrder:
            try:
                return self.__backgrounds[bgType]
            except KeyError:
                raise KeyError('Background of type \'' + bgType + '\' has not been taken yet.')
        else:
            raise ValueError('Invalid background token: ' + bgType +
                             '. Need ' + str(', '.join(preferredOrder)))
