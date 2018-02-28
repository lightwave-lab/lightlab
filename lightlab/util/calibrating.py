from .data import Spectrum
import numpy as np
import matplotlib.pyplot as plt

class SpectrumMeasurementAssistant(object):
    ''' Class for preprocessing measured spectra
    Calculates background spectra by 1) smoothing, 2) tuning/splicing, and 3) peak nulling
    Also handles resonance finding (This could move to a separate manager or external function)
    Interfaces directly with OSA. It DOES NOT set tuning states.
    '''

    bgSmoothWindow = 3.0 # in nm
    def __init__(self, nChan=1, arePeaks=False, visualize=False, wlRange=None):
        self.nChan = nChan
        self.nChanStore = nChan
        self.arePeaks = arePeaks
        self.__backgrounds = {}
        self.wlRange = wlRange
        # self.__bgSmoothed = None # Constant background spectrum due to fading, EDFA profile, etc.
        # self.__bgTuned = None # Constant background taking into account resonance tuning
        # self.__bgNulled = None # Constant background using resonance shapes
        # Plotting
        if visualize:
            self.fig = {}
            self.fig['spect'] = plot.DynamicLine('b-', geometry=[(0,0), (4,3)])
            self.fig['peaks'] = [plot.DynamicLine('k', self.fig['spect']) for _ in range(self.nChan)]
        else:
            self.fig = None
        self.peakfinderOptions = {}
        self.filtShapesForConvolution = None

        self.peakRemove = None

    def setIsPeaks(arePeaks = False):
        self.arePeaks = arePeaks

    # # Removed due to dependence on inst
    # def rawSpect(self, avgCnt=1):
    #     nm, dbm = inst.spectrum(self.wlRange, avgCnt)
    #     return Spectrum(nm, dbm)

    def fgSpect(self, avgCnt=1, raw=None, bgType=None):
        ''' Returns the current spectrum with background removed.

            Also plots so you can see what's going on, if visualize mode was specified

            If raw is specified, does not sweep, just removes background
        '''
        if raw is None:
            raw = self.rawSpect(avgCnt)
        if 'smoothed' not in self.__backgrounds.keys():
            self.setBgSmoothed(raw)
        unbiased = raw - self.getBgSpect(bgType)
        if self.peakRemove is not None:
            unbiased = unbiased - self.peakRemove
        if self.fig is not None:
            self.fig['spect'].refresh(*unbiased.getData())
        return unbiased

    def resonances(self, spect=None):
        ''' Returns the current wavelengths of detected peaks in order sorted by wavelength.
        Uses the simple findPeaks function, but it could later use a convolutive peak finder for more accuracy.
        :param spect: if this is specified, then a new spectrum will not be taken
        '''
        if spect is None:
            spect = self.fgSpect()
        # Standard peak finder
        res = spect.findResonanceFeatures(expectedCnt=self.nChan, isPeak=self.arePeaks, **self.peakfinderOptions)
        # Advanced correlation based peak finder
        if self.filtShapesForConvolution is not None:
            fineRes, confidence = spect.refineResonanceWavelengths(self.filtShapesForConvolution, seedRes=res)
            res = fineRes
        if self.fig is not None:
            for iPk in range(self.nChan):
                self.fig['peaks'][iPk].refresh(*res[iPk].plottingData())
        lamSort = np.argsort([r.lam for r in res])
        return res[lamSort]

    def fgResPlot(self, spect=None, axis=None):
        ''' Takes a foreground spectrum, plots it and its peaks.
        Currently the axis input is unused.
        '''
        if spect is None:
            spect = self.fgSpect()
        res = self.resonances(spect)
        spect.simplePlot()
        _ = [r.simplePlot() for r in res]

    def setBgConst(self, raw):
        ''' Makes a background the maximum transmission observed '''
        self.__backgrounds['smoothed'] = max(raw.ordi)

    def setBgSmoothed(self, raw=None):
        ''' Attempts to find background using a low-pass filter.
        Does not return. Stores results in the assistant variables.
        '''
        if raw is None:
            raw = self.rawSpect()
        if self.arePeaks:
            debug('Warning fake background spectrum is being used on the drop port')
            self.setBgConst(raw)
        else:
            self.__backgrounds['smoothed'] = raw.lowPass(windowWidth=type(self).bgSmoothWindow)

    def setBgTuned(self, base, displaced):
        ''' Insert the pieces of the displaced spectrum into where the peaks are
            It is assumed that these spectra were taken with this object's fgSpect method
        '''
        if self.arePeaks:
            debug('Warning fake background spectrum is being used on the drop port')
            self.__backgrounds['tuned'] = self.getBgSpect()
            return
        res = self.resonances(base)
        baseRaw = base + self.getBgSpect()
        displacedRaw = displaced + self.getBgSpect()
        for r in res:
            spliceWind = r.lam + 3 * r.fwhm * np.array([-1,1])/2
            baseRaw = baseRaw.splice(displacedRaw, segment=spliceWind)
        self.__backgrounds['tuned'] = baseRaw

    def setBgNulled(self, filtShapes, avgCnt=3):
        ''' Uses the peak shape information to null out resonances
        This gives the best estimate of background INDEPENDENT of the tuning state.
        It is assumed that the fine background taken by tuning is present, and the filter shapes were taken with that
        spect should be a foreground spect, but be careful when it is also derived from bgNulled
        '''
        if self.arePeaks:
            debug('Warning, null-based background spectrum not used for drop port. Ignoring')
            self.__backgrounds['nulled'] = self.getBgSpect()
        else:
            spect = self.fgSpect(avgCnt, bgType='tuned')
            newBg = spect.copy()
            for i,r in enumerate(self.resonances(newBg)):
                nulledPiece = spect - filtShapes[i].db().shift(r.lam)
                newBg = newBg.splice(nulledPiece)
            self.__backgrounds['nulled'] = self.getBgSpect(bgType='tuned') - newBg

    def getBgSpect(self, bgType=None):
        preferredOrder = ['nulled', 'tuned', 'smoothed']
        if bgType is None:
            for k in preferredOrder:
                try:
                    return self.__backgrounds[k]
                except KeyError as e:
                    pass
            else:
                raise Exception('No background spectrum has been taken')
        elif bgType in preferredOrder:
            try:
                return self.__backgrounds[bgType]
            except KeyError as e:
                raise KeyError('Background of type \'' + bgType + '\' has not been taken yet.')
        else:
            raise ValueError('Invalid background token: ' + bgType +
                '. Need \'nulled\', \'tuned\', or \'smoothed\'')

    def getAtten(self):
        attenDbm = self.getBgSpect().getMean()
        return np.power(10.0, np.divide(attenDbm, 10.0))

    def removePeaks(self, peaks):

        # Pull Filter Shapes
        spect = self.fgSpect(avgCnt=5, bgType='tuned')
        filtShapes = list()
        for i, r in enumerate(self.resonances(spect)):
            if i not in peaks:
                continue
            relWindow = 7 * r.fwhm * np.array([-1,1])/2
            proximitySpect = spect.shift(-r.lam).crop(relWindow).shift(r.lam)
            filtShapes.append(proximitySpect)

        try:
            assert len(filtShapes) == len(peaks)
        except:
            print(len(filtShapes))
            assert False

        bgs = self.getBgSpect("tuned").debias()

        for sp in filtShapes:
            bgs = bgs.splice(sp)

        self.peakRemove = bgs
        self.nChan -= len(peaks)


    def undoRemovePeaks(self):
        self.peakRemove = None
        self.nChan = self.nChanStore

    def getPeakRemove(self):
        return self.peakRemove
