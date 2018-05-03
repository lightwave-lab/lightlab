''' Useful stuff having to do with data handling and processing.
The Spectrum class is nice for working with dbm and linear units, and also for interpolating at any value.
findPeaks obviously is important.
'''
import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate
from IPython import display
import lightlab.util.io as io
from lightlab import logger


class MeasuredFunction(object):
    ''' Takes measured points and can be called and processed in various ways

        Calling the object interpolates for the array of provided test values.

        Supports addition and subtraction with the +/- operators.
            * **not commutative**
            * The domain used will be the one on the left of the operator

        For simple plotting on the current axis, use :meth:`simplePlot`
    '''

    def __init__(self, abscissaPoints, ordinatePoints, unsafe=False):
        '''
            Args:
                abscissaPoints (array): abscissa, a.k.a. independent variable, a.k.a. domain
                ordinatePoints (array): ordinate, a.k.a. dependent variable, a.k.a. range
                unsafe (bool): if True, faster, give it 1-D np.ndarrays of the same length, or you will get weird errors later on
        '''
        if unsafe:
            self.absc = abscissaPoints
            self.ordi = ordinatePoints
        else:
            checkVals = [None, None]
            for iv, arr in enumerate((abscissaPoints, ordinatePoints)):
                if isinstance(arr, np.ndarray):
                    if arr.ndim > 1:
                        raise ValueError(
                            'Must be a one dimensional array. Got shape ' + str(arr.shape))
                    if arr.ndim == 0:
                        arr = np.array([arr])
                    checkVals[iv] = arr.copy()
                elif isinstance(arr, (list, tuple)):
                    checkVals[iv] = np.array(arr)
                elif np.isscalar(arr):
                    checkVals[iv] = np.array([arr])
                else:
                    raise TypeError('Unsupported type: ' + str(type(arr)) +
                                    '. Need np.ndarray, scalar, list, or tuple')
            self.absc, self.ordi = tuple(checkVals)
            if self.absc.shape != self.ordi.shape:
                raise ValueError('Shapes do not match. Got ' +
                                 str(self.absc.shape) + ' and ' + str(self.ordi.shape))

    # Data structuring and usage stuff

    def __call__(self, testAbscissa=None):
        ''' Interpolates the discrete function

            Args:
                testAbscissa (array): test points in the domain

            Returns:
                testOrdinate (array): interpolated output values
        '''
        if np.isscalar(self.absc):
            return self.ordi[0]
        return np.interp(testAbscissa, self.absc, self.ordi)

    def __len__(self):
        return len(self.absc)

    def __getitem__(self, sl):
        ''' Slice this function.

            Args:
                sl (int, slice): which indeces to pick out

            Returns:
                (MeasuredFunction/<childClass>): sliced version
        '''
        if type(sl) not in [int, slice]:
            raise ValueError('MeasuredFunction [] only works with integers and slices. ' +
                             'Got ' + str(sl) + ' (' + str(type(sl)) + ').')
        newAbsc = self.absc[sl]
        newOrdi = self.ordi[sl]
        return self.__newOfSameSubclass(newAbsc, newOrdi)

    def getData(self):
        ''' Gives a tuple of the enclosed array data.

            It is copied, so you can do what you want with it

            Returns:
                tuple(array,array): the enclosed data
        '''
        return np.copy(self.absc), np.copy(self.ordi)

    def copy(self):
        ''' Gives a copy, so that further operations can be performed without side effect.

            Returns:
                (MeasuredFunction/<childClass>): new object with same properties
        '''
        return self.__newOfSameSubclass(self.absc, self.ordi)

    def save(self, savefile=None):
        if savefile is None:
            logger.error('Warning: No save file specified')
        io.saveMat(savefile, {'absc': self.absc, 'ordi': self.ordi})

    def load(self, savefile=None):
        if savefile is None:
            logger.warning('Warning: No save file specified')
        dataDict = io.loadMat(savefile)
        self.absc, self.ordi = dataDict['absc'], dataDict['ordi']
        return self

    @classmethod
    def loadFromFile(cls, savefile=None):
        if savefile is None:
            logger.warning('Warning: No save file specified')
        dataDict = io.loadMat(savefile)
        absc, ordi = dataDict['absc'], dataDict['ordi']
        return cls(absc, ordi)

    def simplePlot(self, *args, livePlot=False, **kwargs):
        ''' Plots on the current axis

        Args:
            *args (tuple): arguments passed through to ``pyplot.plot``
            **kwargs (dict): arguments passed through to ``pyplot.plot``

        Returns:
            Whatever is returned by ``pyplot.plot``
        '''
        curve = plt.plot(*(self.getData() + args), **kwargs)
        if 'label' in kwargs.keys():
            plt.legend()
        if livePlot:
            display.clear_output(wait=True)
            display.display(plt.gcf())
        return curve

    # Simple data handling operations

    def __newOfSameSubclass(self, newAbsc, newOrdi):
        ''' Helper functions that ensures proper inheritance of other methods.

            Returns a new object of the same type and
            with the same metadata (i.e. everything but absc and ordi) as self.

            This is useful for many kinds of operations where the returned
            MeasuredFunction or ChildClass is further processed

            Args:
                newAbsc (array): abscissa of new MeasuredFunction
                newOrdi (array): ordinate of new MeasuredFunction

            Returns:
                (MeasuredFunction): new object, which is a child class of MeasuredFunction
        '''
        newObj = type(self)(newAbsc.copy(), newOrdi.copy(), unsafe=True)
        for attr, val in self.__dict__.items():
            if attr not in ['absc', 'ordi']:
                newObj.__dict__[attr] = val
        return newObj

    def getSpan(self):
        ''' The span of the domain

            Returns:
                (list[float,float]): the minimum and maximum abscissa points
        '''
        return [min(self.absc), max(self.absc)]

    def getRange(self):
        ''' The span of the ordinate

            Returns:
                (list[float,float]): the minimum and maximum values
        '''
        return [min(self.ordi), max(self.ordi)]

    def crop(self, segment):
        ''' Crop abscissa to segment domain

            Args:
                segment (list[float,float]): the span of the new abscissa domain

            Returns:
                MeasuredFunction: new object
        '''
        dx = abs(np.diff(self.absc[0:2])[0])
        newAbsc = np.arange(*(tuple(segment) + (dx,)))
        return self.__newOfSameSubclass(newAbsc, self(newAbsc))

    def clip(self, amin, amax):
        ''' Clip ordinate to min/max range

            Args:
                amin (float): minimum value allowed in the new MeasuredFunction
                amax (float): maximum value allowed in the new MeasuredFunction

            Returns:
                MeasuredFunction: new object
        '''
        return self.__newOfSameSubclass(self.absc, np.clip(self.ordi, amin, amax))

    def shift(self, shiftBy):
        ''' Shift abscissa. Good for biasing wavelengths.

            Args:
                shiftBy (float): the number that will be added to the abscissa

            Returns:
                MeasuredFunction: new object
        '''
        return self.__newOfSameSubclass(self.absc + shiftBy, self.ordi)

    def flip(self):
        ''' Flips the abscissa, BUT DOES NOTHING the ordinate.

            Usually, this is meant for spectra centered at zero.
            I.e.: flipping would be the same as negating abscissa

            Returns:
                MeasuredFunction: new object
        '''
        return self.__newOfSameSubclass(self.absc[::-1], self.ordi)

    def debias(self):
        ''' Removes mean from the function

            Returns:
                MeasuredFunction: new object
        '''
        bias = np.mean(self.ordi)
        return self.__newOfSameSubclass(self.absc, self.ordi - bias)

    def unitRms(self):
        ''' Returns function with unit RMS or power
        '''
        rmsVal = rms(self.debias().ordi)
        return self * (1 / rmsVal)

    def getMean(self):
        return np.mean(self.ordi)

    def resample(self, nsamp=100):
        ''' Resample over the same domain span, but with a different number of points.

            Args:
                nsamp (int): number of samples in the new object

            Returns:
                MeasuredFunction: new object
        '''
        newAbsc = np.linspace(*self.getSpan(), int(nsamp))
        return self.__newOfSameSubclass(newAbsc, self(newAbsc))

    def uniformlySample(self):
        ''' Makes sure samples are uniform

            Returns:
                MeasuredFunction: new object
        '''
        dxes = np.diff(self.absc)
        if all(dxes == dxes[0]):
            return self
        else:
            return self.resample(len(self))

    def addPoint(self, xyPoint):
        ''' Adds the (x, y) point to the stored absc and ordi

            Args:
                xyPoint (tuple): x and y values to be inserted

            Returns:
                None: modifies this object
        '''
        x, y = xyPoint
        for i in range(len(self)):
            if x < self.absc[i]:
                break
        else:
            i = len(self)
        self.absc = np.insert(self.absc, i, x)
        self.ordi = np.insert(self.ordi, i, y)

    # Signal processing stuff

    def lowPass(self, windowWidth=None, mode='valid'):
        ''' Low pass filter performed by convolving a moving average window.

            The convolutional ``mode`` can be one of the following string tokens
                * 'valid': the new span is reduced, but data is good looking
                * 'same': new span is the same as before, but there are edge artifacts

            Args:
                windowWidth (float): averaging window width in units of the abscissa
                mode (str): convolutional mode

            Returns:
                MeasuredFunction: new object
        '''
        if windowWidth is None:
            windowWidth = (max(self.absc) - min(self.absc)) / 10
        dx = abs(np.diff(self.absc[0:2])[0])
        windPts = np.int(windowWidth / dx)
        if windPts % 2 == 0:  # Make sure windPts is odd so that basis doesn't shift
            windPts += 1
        if windPts >= np.size(self.ordi):
            raise Exception('windowWidth is ' + str(windPts) +
                            ' wide, which is bigger than the data itself (' + str(np.size(self.ordi)) + ')')

        filt = np.ones(windPts) / windPts
        invalidIndeces = int((windPts - 1) / 2)

        if mode == 'valid':
            newAbsc = self.absc[invalidIndeces:-invalidIndeces].copy()
            newOrdi = np.convolve(filt, self.ordi, mode='valid')
        elif mode == 'same':
            newAbsc = self.absc.copy()
            newOrdi = self.ordi.copy()
            newOrdi[invalidIndeces:-invalidIndeces] = np.convolve(filt, self.ordi, mode='valid')
        return self.__newOfSameSubclass(newAbsc, newOrdi)

    def deleteSegment(self, segment):
        ''' Removes the specified segment from the abscissa.

            This means calling within this segment will give the first-order interpolation of its edges.

            Usually, deleting is followed by splicing in some new data in this span

            Args:
                segment (list[float,float]): span over which to delete stored points

            Returns:
                MeasuredFunction: new object
        '''
        nonNullInds = np.logical_or(self.absc < min(segment), self.absc > max(segment))
        newAbsc = self.absc[nonNullInds]
        return self.__newOfSameSubclass(newAbsc, self(newAbsc))

    def splice(self, other, segment=None):
        ''' Returns a Spectrum that is this one,
            except with the segment replaced with the other one's data

            The abscissa of the other matters.
            There is nothing changing (abscissa, ordinate) point pairs,
            only moving them around from ``other`` to ``self``.

            If segment is not specified, uses the full domain of the other

            Args:
                other (MeasuredFunction): the origin of new data
                segment (list[float,float]): span over which to do splice stored points

            Returns:
                MeasuredFunction: new object
        '''
        if segment is None:
            segment = other.getSpan()
        spliceInds = np.logical_and(self.absc > min(segment), self.absc < max(segment))
        newOrdi = self.ordi.copy()
        newOrdi[spliceInds] = other(self.absc[spliceInds])
        return self.__newOfSameSubclass(self.absc, newOrdi)

    def invert(self, yVals, directionToDescend=None):
        ''' Descends down the function until yVal is reached in ordi. Returns the absc value

            If the function is peaked, you should specify a direction to descend.

            If the function is approximately monotonic, don't worry about it.

            Args:
                yVals (scalar, ndarray): array of y values to descend to
                directionToDescend (['left', 'right', None]): use if peaked function to tell which side.
                    Not used if monotonic

            Returns:
                (scalar, ndarray): corresponding x values
        '''
        maxInd = np.argmax(self.ordi)
        minInd = np.argmin(self.ordi)
        if directionToDescend is None:
            if minInd < maxInd:
                directionToDescend = 'left'
            else:
                directionToDescend = 'right'
        if np.isscalar(yVals):
            yValArr = np.array([yVals])
        else:
            yValArr = yVals
        xValArr = np.zeros(yValArr.shape)
        for iVal, y in enumerate(yValArr):
            xValArr[iVal] = interpInverse(*self.getData(),
                                          startIndex=maxInd,
                                          direction=directionToDescend,
                                          threshVal=y)
        if np.isscalar(yVals):
            return xValArr[0]
        else:
            return xValArr

    def centerOfMass(self):
        ''' Returns abscissa point where mass is centered '''
        deb = self.debias().clip(0, None)
        weighted = np.multiply(*deb.getData())
        com = np.sum(weighted) / np.sum(deb.ordi)
        return com

    def moment(self, order=2, relativeGauss=False):
        ''' The order'th moment of the function

            Args:
                order (integer): the polynomial moment of inertia. Don't trust the normalization of > 2'th order.
                    order = 1: mean
                    order = 2: variance
                    order = 3: skew
                    order = 4: kurtosis

            Returns:
                (float): the specified moment
        '''
        mean = np.mean(self.ordi)
        if order == 1:
            return mean
        variance = np.mean(np.power(self.ordi - mean, 2))
        if order == 2:
            return variance
        if order == 4:
            kurtosis = np.mean(np.power(self.ordi - mean, 4))
            kurtosis /= variance ** 2
            if relativeGauss:
                kurtosis -= 3
            return kurtosis

    # Mathematics

    # Operands must be either
    #     the same subclass of MeasuredFunction, or
    #     scalar numbers, or
    #     functions/bound methods: these must be callable with one argument that is an ndarray
    #         Please god no side-effects in these functions

    # The returned result is the same subclass as self,
    # and its properties other than absc and ordi will be the SAME as the first operand

    def __binMathHelper(self, other):
        ''' returns the new abcissa and a tuple of arrays: the ordinates to operate on
        '''
        # if type(other).__name__ == type(self).__name__: # using name to get around autoreload bug
        #     for obj in (self, other):
        #         if isinstance(obj.ordi, MeasuredFunction):
        #             raise TypeError('You have an ordinate that is a MeasuredFunction!' +
        #                 ' This is a common error. In ' + str(obj))
        #     if np.all(self.absc == other.absc):
        #         newAbsc = self.absc
        #         ords = (self.ordi, other.ordi)
        #     else:
        #         newAbsc = type(self).__minAbsc(self, other)
        #         ords = (self(newAbsc), other(newAbsc))
        # elif isinstance(other, (float, int)) or np.isscalar(other):
        #     newAbsc = self.absc
        #     ords = (self.ordi, other * np.ones(len(newAbsc)))
        # elif isinstance(other, (types.FunctionType, types.MethodType)):
        #     newAbsc = self.absc
        #     try:
        #         ords = (self.ordi, other(newAbsc))
        #     except Exception as err:
        #         logger.error('Call to {} failed'.format(other))
        #         raise err
        # else:
        #     raise TypeError('Unsupported types for binary math: ' + type(self).__name__ + ', ' + type(other).__name__)
        # return newAbsc, ords
        try:
            ab = other.absc
        except AttributeError:  # in other.absc
            pass
        else:
            if np.all(ab == self.absc):
                newAbsc = self.absc
                ords = (self.ordi, other.ordi)
            else:
                newAbsc = type(self).__minAbsc(self, other)
                ords = (self(newAbsc), other(newAbsc))
            return newAbsc, ords

        newAbsc = self.absc
        try:
            other = float(other)
        except TypeError:  # not an int, float, or np.ndarry with all singleton dimensions
            pass
        else:
            ords = (self.ordi, other * np.ones(len(newAbsc)))
            return newAbsc, ords

        try:
            othOrd = other(newAbsc)
        except TypeError:  # not callable
            pass
        else:
            ords = (self.ordi, othOrd)
            return newAbsc, ords

        # time to fail
        if isinstance(other, np.ndarray):
            raise TypeError('Cannot do binary math with MeasuredFunction and numpy array')
        for obj in (self, other):
            if isinstance(obj.ordi, MeasuredFunction):
                raise TypeError('You have an ordinate that is a MeasuredFunction!' +
                                ' This is a common error. It\'s in ' + str(obj))
        raise TypeError('Unsupported types for binary math: ' +
                        type(self).__name__ + ', ' + type(other).__name__)

    @staticmethod
    def __minAbsc(fa, fb):
        ''' Get the shorter abscissa '''
        selfRange = abs(fa.absc[0] - fa.absc[-1])
        otherRange = abs(fb.absc[0] - fb.absc[-1])
        if selfRange < otherRange:
            newAbsc = fa.absc.copy()
        else:
            newAbsc = fb.absc.copy()
        return newAbsc

    def __sub__(self, other):
        ''' Returns the subtraction of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self.__binMathHelper(other)
        return self.__newOfSameSubclass(newAbsc, ords[0] - ords[1])

    def __rsub__(self, other):
        newAbsc, ords = self.__binMathHelper(other)
        return self.__newOfSameSubclass(newAbsc, ords[1] - ords[0])

    def __add__(self, other):
        ''' Returns the subtraction of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self.__binMathHelper(other)
        return self.__newOfSameSubclass(newAbsc, ords[0] + ords[1])

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        ''' Returns the product of the two functions, in the domain of the shortest abscissa object.
        The other object can also be a scalar '''
        newAbsc, ords = self.__binMathHelper(other)
        return self.__newOfSameSubclass(newAbsc, ords[0] * ords[1])

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self * (1 / other)

    def __rdiv__(self, other):  # pylint: disable=unused-argument
        return NotImplemented

    def __eq__(self, other):
        if isinstance(self, type(other)):
            return np.all(self.absc == other.absc) and np.all(self.ordi == other.ordi)
        return False

    def findResonanceFeatures(self, **kwargs):
        r''' A convenient wrapper for :py:func:`findPeaks` that works with this class.

            Args:
                \*\*kwargs: kwargs passed to :py:func:`findPeaks`

            Returns:
                list[ResonanceFeature]: the detected features as nice objects
        '''
        mFun = self.uniformlySample()
        dLam = np.diff(mFun.getSpan())[0] / len(mFun)

        xArr, yArr = mFun.getData()

        # Use the class-free peakfinder on arrays
        pkInds, pkIndWids = findPeaks(yArr, **kwargs)

        # Translate back into units of the original MeasuredFunction
        pkLambdas = xArr[pkInds]
        pkAmps = yArr[pkInds]
        pkWids = pkIndWids * dLam

        # Package into resonance objects
        try:
            isPeak = kwargs['isPeak']
        except KeyError:
            isPeak = True
        resonances = np.empty(len(pkLambdas), dtype=object)
        for iPk in range(len(resonances)):
            resonances[iPk] = ResonanceFeature(
                pkLambdas[iPk], pkWids[iPk], pkAmps[iPk], isPeak=isPeak)
        return resonances


class Spectrum(MeasuredFunction):
    ''' simply stores a nm, dbm pair

        Also provides some decent handling of linear/dbm units.

        Use :meth:`lin` and :meth:`dbm` to make sure what you're getting
        for things like binary math and peakfinding, etc.
    '''

    def __init__(self, nm, power, inDbm=True, unsafe=False):
        '''
            Args:
                nm (array): abscissa
                power (array): ordinate
                inDbm (bool): is the ``power`` in linear or dbm units?
        '''
        super().__init__(nm, power, unsafe=unsafe)
        self.__inDbm = inDbm

    @property
    def inDbm(self):
        ''' Is it in dbm units currently?

            Returns:
                bool:
        '''
        return self.__inDbm

    # @inDbm.setter
    # def inDbm(self, newInDbm=True):
    #     ''' Changes overall state of the spectrum '''
    #     raise Exception('Spectrum dbm/linear is immutable.')

    def lin(self):
        ''' The spectrum in linear units

            Returns:
                Spectrum: new object
        '''
        if not self.inDbm:
            return type(self)(self.absc.copy(), self.ordi.copy(), inDbm=False)
        else:
            return type(self)(self.absc.copy(), 10 ** (self.ordi.copy() / 10), inDbm=False)

    def db(self):
        ''' The spectrum in decibel units

            Returns:
                Spectrum: new object
        '''
        if self.inDbm:
            return type(self)(self.absc.copy(), self.ordi.copy(), inDbm=True)
        else:
            clippedOrdi = np.clip(self.ordi, 1e-12, None)
            return type(self)(self.absc.copy(), 10 * np.log10(clippedOrdi), inDbm=True)

    def __binMathHelper(self, other):
        ''' Adds a check to make sure lin/db is in the same state '''
        if type(other) is type(self) and other.inDbm is not self.inDbm:
            raise Exception('Can not do binary math on Spectra in different formats')
        return super().__binMathHelper(other)

    # Peak and trough related

    def refineResonanceWavelengths(self, filtShapes, seedRes=None, isPeak=None):
        ''' Convolutional resonance correction to get very robust resonance wavelengths

            Does the resonance finding itself, unless an initial approximation is provided.

            Also, has some special options for ``Spectrum`` types to make sure db/lin is optimal

            Args:
                filtShapes (list[MeasuredFunction]): shapes of each resonance. Must be in order of ascending abscissa/wavelength
                seedRes (list[ResonanceFeature]): rough approximation of resonance properties. If None, this method will find them.
                isPeak (bool): required to do peak finding, but not used if ``seedRes`` is specified

            Returns:
                list[ResonanceFeature]: the detected and refined features as nice objects

            Todo:
                take advantage of fft convolution for speed
        '''
        if seedRes is None:
            if isPeak is None:
                raise Exception('If seed resonance is not specified, isPeak must be specified.')
            seedRes = self.findResonanceFeatures(expectedCnt=len(filtShapes), isPeak=isPeak)
        else:
            isPeak = seedRes[0].isPeak
        fineRes = np.array([r.copy() for r in seedRes])

        useFilts = filtShapes.copy()
        if type(self) == Spectrum:
            # For Spectrum objects only
            if isPeak:
                spectFun = self.lin()
            else:
                spectFun = 1 - self.lin()
            for i in range(len(filtShapes)):
                if type(filtShapes[i]).__name__ != 'Spectrum':
                    raise Exception(
                        'If calling object is Spectrum, the filter shapes must also be Spectrum types')
                if isPeak:
                    useFilts[i] = filtShapes[i].lin()
                else:
                    useFilts[i] = 1 - filtShapes[i].lin()
        else:
            spectFun = self

        confidence = 1000
        for i, r in enumerate(fineRes):
            thisFilt = useFilts[i]
            cropWind = max(thisFilt.absc) * np.array([-1, 1])
            subSpect = spectFun.shift(-r.lam).crop(cropWind)
            basis = subSpect.absc
            convArr = np.convolve(subSpect(basis), thisFilt(basis)[::-1], 'same')
            lamOffset = basis[np.argmax(convArr)]
            fineRes[i].lam = r.lam + lamOffset
            thisConf = np.max(convArr) / np.sum(thisFilt(basis) ** 2)
            confidence = min(confidence, thisConf)
        return fineRes, confidence

    def findResonanceFeatures(self, **kwargs):
        ''' Overloads :py:mod:``MeasuredFunction.findResonanceFeatures`` to make sure it's in db scale

            Args:
                **kwargs: kwargs passed to :py:mod:`findPeaks`

            Returns:
                list[ResonanceFeature]: the detected features as nice objects
        '''
        kwargs['isDb'] = True
        return MeasuredFunction.findResonanceFeatures(self.db(), **kwargs)


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


# Classless peak finding and monotonic descent functions


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
        # plt.plot(yArr)
        # raise Exception
    elif iHit in [0]:
        return xArr[iHit]
    else:  # interpolate
        q = yArr[iHit - 1:iHit + 1][::-1]
        v = xArr[iHit - 1:iHit + 1][::-1]
        return np.interp(0, q, v)


class MeasuredSurface(object):
    ''' Basically a two dimensional measured function '''

    def __init__(self, absc, ordi):
        if type(absc) == np.ndarray and absc.ndim != 1:
            raise Exception(
                'absc should be a 2-element list of arrays or an array of objects (which are arrays)')
        if len(absc) != 2:
            raise Exception('Wrong number of abscissas. Need two')
        abscshape = np.zeros(2)
        for iDim in range(2):
            abscshape[iDim] = len(absc[iDim])
        if not np.all(ordi.shape == abscshape):
            raise Exception('Dimensions of ordinate and abscissa do not match')
        self.absc = absc
        self.ordi = ordi

    @classmethod
    def fromFunctionBundle(cls, otherBund, addedAbsc=None):
        ''' gives back a MeasuredSurface from a function Bundle

            Params:
                otherBund: The FunctionBundle. The ordering matters
                addedAbsc: the other dimension abscissa array (default, integers)

            Returns:
                MeasuredSurface object
        '''
        existingAbsc = otherBund.absc
        if addedAbsc is None:
            addedAbsc = np.arange(otherBund.nDims)
        return cls([addedAbsc, existingAbsc], otherBund.ordiMat)

    def __call__(self, testAbscissaVec=None):
        f = interpolate.interp2d(*self.absc, z=self.ordi, kind='cubic')
        return f(*testAbscissaVec)

    def item(self, index, dim=None):
        if np.isscalar(index):
            assert(dim is not None)
            newAbsc = self.absc[dim]
            if dim == 0:
                newOrdi = self.ordi[index, :]
            else:
                newOrdi = self.ordi[:, index]
            return MeasuredFunction(newAbsc, newOrdi)
        else:
            assert(len(index) == 2)
            firstDimMf = self.item(index[0], dim=0)
            return firstDimMf[index[1]]

    def shape(self):
        return self.ordi.shape

    def simplePlot(self, *args, **kwargs):
        import matplotlib.cm as cm
        if 'cmap' not in kwargs.keys():
            kwargs['cmap'] = cm.inferno  # pylint: disable=no-member
        if 'shading' not in kwargs.keys():
            kwargs['shading'] = 'flat'
        YY, XX = np.meshgrid(self.absc[0], self.absc[1])
        plt.pcolormesh(XX, YY, np.array(self.ordi.T), *args, **kwargs)
        plt.autoscale(tight=True)

    # def cut(self, dim, value):
    #     oneDimMf = MeasuredFunction()
    #     for abOtherDim in self.absc[1-dim]:


class MeasuredErrorField(object):
    ''' A field that hold two abscissa arrays and two ordinate matrices

        Error is the measuredGrid - nominalGrid, which is a vector field
    '''

    def __init__(self, nominalGrid, measuredGrid):
        assert(nominalGrid.ndim == 3)
        self.nomiGrid = nominalGrid
        if measuredGrid.ndim == 4:
            self.measGrid = np.mean(measuredGrid, axis=0)
        elif measuredGrid.ndim == 3:
            self.measGrid = measuredGrid
        else:
            raise Exception('measuredGrid must be dimension 3 (meaned) or 4 (trials)')

    def __call__(self, testVec=None):
        xVec = self.nomiGrid[:, :, 0]
        yVec = self.nomiGrid[:, :, 1]
        uVec = self.measGrid[:, :, 0]
        vVec = self.measGrid[:, :, 1]
        u = interpolate.interp2d(xVec, yVec, uVec, kind='linear')
        v = interpolate.interp2d(xVec, yVec, vVec, kind='linear')
        testU = u(*testVec)[0]
        testV = v(*testVec)[0]
        return np.array([testU, testV])

    def errorAt(self, testVec=None):
        return self(testVec) - testVec

    def invert(self, desiredVec):
        reflectedVec = desiredVec - self.errorAt(desiredVec)
        avgErr = (self.errorAt(desiredVec) + self.errorAt(reflectedVec)) / 2
        commandVec = desiredVec - avgErr
        return commandVec

    def zeroCenteredSquareSize(self):
        ''' Very stupid, just look at corner points

            Returns:
                (tuple(float)): square sides of nominal and measured grids

        '''
        def cornerInd(grid, minOrMax):
            score = np.sum(grid, axis=2)
            cornerFlatInd = np.argmin(score) if minOrMax else np.argmax(score)
            return np.unravel_index(cornerFlatInd, grid.shape[:2])

        def zcSz(grid, corner):
            cornerVec = grid[(corner + (slice(None), ))]
            sqSide = np.min(np.abs(cornerVec))
            return sqSide

        nomiCornerInds = [cornerInd(self.nomiGrid, m) for m in [True, False]]
        nomiSq = np.min([zcSz(self.nomiGrid, nomiCornerInds[i]) for i in range(2)])
        measSq = np.min([zcSz(self.measGrid, nomiCornerInds[i]) for i in range(2)])
        return nomiSq, measSq

    # def __init__(self, abscissas, ordinates):
    #     if type(abscissas) == np.ndarray and absc.ndim != 1:
    #         raise Exception('absc should be a 2-element list of arrays or an array of objects (which are arrays)')
    #     if len(abscissas) != 2:
    #         raise Exception('Wrong number of abscissas. Need two')
    #     abscshape = np.zeros(2)
    #     for iDim in range(2):
    #         if abscissas[iDim].ndim != 1:
    #             raise Exception('abscissa elements must be 1d arrays')
    #         abscshape[iDim] = len(abscissas[iDim])

    #     if type(ordinates) == np.ndarray and absc.ndim != 1:
    #         raise Exception('ordinates should be a 2-element list of arrays or an array of objects (which are arrays)')
    #     if len(ordinates) != 2:
    #         raise Exception('Wrong number of ordinates. Need two')
    #     ordishape = np.zeros(2)
    #     for iSurf in range(2):
    #         if ordinates[iSurf].ndim != 2:
    #             raise Exception('ordinate elements must be 2d arrays')
    #         if not np.all(ordinates[iSurf].shape == abscshape):
    #             raise Exception('Dimensions of ordinate and abscissa do not match')

    #     self.surfs = np.empty(2, dtype=object)
    #     for iSurf in range(2):
    #         self.surfs[iSurf] = MeasuredSurface(abscissas, ordinates[iSurf])


class Spectrogram(MeasuredSurface):
    pass


class Waveform(MeasuredFunction):
    ''' stores a time, voltage pair. That's about it right now '''

    def __init__(self, t, v, unsafe=False):
        super().__init__(t, v, unsafe=unsafe)

    @classmethod
    def pulse(cls, tArr, tOn, tOff):
        vForm = np.zeros(len(tArr))
        vForm[tArr > tOn] = 1.
        vForm[tArr > tOff] = 0.
        return cls(tArr, vForm)

    @classmethod
    def whiteNoise(cls, tArr, rmsPow):
        vForm = np.random.randn(len(tArr))
        firstRms = rms(vForm)
        return cls(tArr, vForm * np.sqrt(rmsPow / firstRms))


class FunctionBundle(object):
    ''' A bundle of measured functions.

        The key is that they have the same abscissa base. This class will take care of resampling in a common abscissa base.
        The bundle can be:

        * iterated to get the individual MeasuredFunctions
        * operated on with other FunctionBundles
        * plotted with simplePlot and multiAxisPlot

        This provides nice plotting functions for things like eyes, but not decomposition methods: see `FunctionalBasis`
    '''

    def __init__(self, measFunList=None):
        ''' Can be initialized fully, or initialized with None to be built interactively.

            Args:
                measFunList (list[MeasuredFunction],None): list of MeasuredFunctions that must have the same abscissa.
        '''
        self.absc = None
        self.ordiMat = None
        self.memberType = None
        self.nDims = 0
        if measFunList is not None:
            if type(measFunList) is list:
                for m in measFunList:
                    self.addDim(m)
            else:
                self.addDim(measFunList)

    def addDim(self, newMeasFun):
        if self.absc is None:
            self.absc = newMeasFun.absc
            self.ordiMat = np.matrix(newMeasFun.ordi)
            self.memberType = type(newMeasFun)
        else:
            y = self._putInTimebase(newMeasFun)  # This does the checking for type and timebase
            self.ordiMat = np.append(self.ordiMat, [y], axis=0)
        self.nDims += 1

    def __getitem__(self, index):
        ''' Iterator that gives out individual measured functions of the type used
        '''
        theOrdi = self.ordiMat[
            index, :].A1  # A1 is a special numpy thing that converts from matrix to 1-d array
        return self.memberType(self.absc, theOrdi)

    def __len__(self):
        return self.ordiMat.shape[0]

    def __mul__(self, other):
        if np.isscalar(other):
            other = np.ones(self.nDims) * other
        newObj = self.copy()
        for iDim in range(self.nDims):
            newObj.ordiMat[iDim] = self.ordiMat[iDim] * other[iDim]
        return newObj

    def __rmul__(self, other):
        return self.__mul__(other)

    def __truediv__(self, other):
        return self * (1 / other)

    def copy(self):
        newObj = type(self)()
        newObj.__dict__ = self.__dict__.copy()
        newObj.ordiMat = self.ordiMat.copy()
        return newObj

    def max(self):
        ''' Returns a single MeasuredFunction(subclass) that is the maximum of all in this bundle
        '''
        return self.memberType(self.absc, np.max(self.ordiMat, axis=0).A1)

    def min(self):
        ''' Returns a single MeasuredFunction(subclass) that is the minimum of all in this bundle
        '''
        return self.memberType(self.absc, np.min(self.ordiMat, axis=0).A1)

    def mean(self):
        ''' Returns a single MeasuredFunction(subclass) that is the mean of all in this bundle
        '''
        return self.memberType(self.absc, np.mean(self.ordiMat, axis=0).A1)

    def crop(self, segment):
        ''' Crop abscissa to segment domain

            Args:
                segment (list[float,float]): the span of the new abscissa domain

            Returns:
                MeasuredFunction: new object
        '''
        newObj = type(self)()
        for iFun in range(len(self)):
            fun = self[iFun].crop(segment)
            newObj.addDim(fun)
        return newObj

    def reverse(self):
        self.ordiMat = self.ordiMat[::-1]

    def unitRms(self):
        ''' Returns a bundle with each waveform in unit variance '''
        newBundle = type(self)()
        for wfm in self:
            newBundle.addDim(wfm.unitRms())
        return newBundle

    def resample(self, nsamp=100):
        ''' Resample over the same domain span, but with a different number of points.

            Args:
                nsamp (int): number of samples in the new object

            Returns:
                FunctionBundle: new object
        '''
        newBundle = type(self)()
        for item in self:
            newBundle.addDim(item.resample(nsamp))
        return newBundle

    def _putInTimebase(self, testFun):
        ''' Makes sure signal type is correct and time basis is the same

            Args:
                testFun (MeasuredFunction): the new function, as encapsulated by an object

            Returns:
                array: the ordinate of the new function in the right timebase

            Raises:
                TypeError: if the type of ``testFun`` is different than the others in this FunctionalBasis
        '''
        if type(testFun).__name__ is not self.memberType.__name__:
            raise TypeError('This FunctionalBasis expects ' + str(self.memberType) +
                            ', but was given ' + str(type(testFun)) + '.')
        # Check time base
        if np.any(testFun.absc != self.absc):
            # logger.warning('Warning: Basis signal time abscissa are different. Interpolating...')
            return testFun(self.absc)
        else:
            return testFun.ordi

    def simplePlot(self, *args, **kwargs):
        '''
        '''
        for f in self:
            f.simplePlot(*args, **kwargs)

    def multiAxisPlot(self, *args, axList=None, titleRoot=None, **kwargs):
        ''' titleRoot must take one argument in its format method, which is given the index
            Returns:
                (list(axis)): The axes that were plotted upon
        '''
        if axList is None:
            _, axList = plt.subplots(nrows=len(self), figsize=(14, 14))
            # fi, axList = plt.subplots(nrows=len(self), figsize=(14,16))
        if len(axList) != len(self):
            raise ValueError('Wrong number of axes. Got {}, need {}.'.format(
                len(axList), len(self)))
        for i, ax in enumerate(axList):
            plt.sca(ax)
            self[i].simplePlot(*args, **kwargs)
            if titleRoot is not None:
                plt.title(titleRoot.format(i + 1))
                # plt.xlabel('Time (s)')
            # plt.ylabel('Intensity (a.u.)')
            # plt.xlim(0,2e-8)
        return axList

    def histogram(self):
        ''' Gives a MeasuredFunction of counts vs. ordinate values (typically voltage)
            Does not maintain any abscissa information

            At this point, does not allow caller to set the arguments passed to np.histogram

            This is mainly just for plotting
        '''
        hist, bins = np.histogram(self.ordiMat, bins='auto', density=False)
        histFun = MeasuredFunction([], [])
        for iBin, thisOrdi in enumerate(hist):
            thisAbsc = np.mean(bins[iBin:iBin + 1])
            histFun.addPoint((thisAbsc, thisOrdi))
        return histFun

    def weightedAddition(self, weiVec):
        ''' Calculates the weighted addition of the basis signals

            Args:
                weiVec (array): weights to be applied to the basis functions

            Returns:
                (MeasuredFunction): weighted addition of basis signals
        '''
        assert(len(weiVec) == self.nDims)
        weiVec = np.reshape(weiVec, (1, self.nDims))
        outOrdi = np.dot(weiVec, self.ordiMat)
        return self.memberType(self.absc, outOrdi.A1)

    def moment(self, order=2, allDims=True, relativeGauss=False):
        ''' The order'th moment of all the points in the bundle.

            Args:
                order (integer): the polynomial moment of inertia. Don't trust the normalization of > 2'th order.
                    order = 1: mean
                    order = 2: variance
                    order = 3: skew
                    order = 4: kurtosis
                allDims (bool): if true, collapses all signals, returning a scalar

            Returns:
                (ndarray or float): the specified moment(s)
        '''
        byDim = np.zeros(len(self))
        for iDim in range(len(self)):
            byDim[iDim] = self[iDim].moment(order, relativeGauss=relativeGauss)
        if allDims:
            return np.mean(byDim)
        else:
            return byDim

    def componentAnalysis(self, *args, pcaIca=True, lNorm=2, expectedComponents=None, **kwargs):
        ''' Gives the waveform representing the principal component of the order

            Args:
                pcaIca (bool): if True, does PCA; if False, does ICA
                lNorm (int): how to normalize weight vectors. L1 norm uses the maximum abs weight, while L2 norm (default) is vector unit
                expectedComponents (FunctionBundle or subclass): Used for flipping signs
                args, kwargs: Feed through to sklearn.decomposition.[PCA(), FastICA()]

            Returns:
                (FunctionBundle or subclass): principal component waveforms
        '''
        from sklearn.decomposition import PCA, FastICA
        compBuiltIn = PCA if pcaIca else FastICA
        compAnal = compBuiltIn(*args, **kwargs)
        compAnal.fit(self.ordiMat.T)
        pcBundle = type(self)()
        for c in compAnal.components_:
            if lNorm == 1:
                w = c / np.sqrt(np.max(c ** 2))
            elif lNorm == 2:
                w = c / np.sqrt(np.sum(c ** 2))
            else:
                raise Exception('Are you serious? Use a valid L-norm')
            pcWfm = self.weightedAddition(w)
            pcBundle.addDim(pcWfm)
        if expectedComponents is not None:
            pcBundle = pcBundle.correctSigns(expectedComponents, maintainOrder=pcaIca)
        return pcBundle

    def correctSigns(self, otherBundle, maintainOrder=True):
        ''' Goes through each component and flips the sign if correlation is negative

            ICA also has a permutation indeterminism.
        '''
        if len(self) != len(otherBundle):
            raise ValueError('Self and other bundle must be the same length')
        newBundle = type(self)()
        usedPermInds = []
        for iDim, oSig in enumerate(otherBundle):
            if maintainOrder:
                sSig = self[iDim]
                if (sSig * oSig).getMean() > 0:
                    newWfm = sSig
                else:
                    newWfm = -1 * sSig
            else:
                permCorrs = np.zeros(len(self))
                for jDim, sSig in enumerate(self):
                    if jDim not in usedPermInds:
                        permCorrs[jDim] = (sSig * oSig).getMean()
                permInd = np.argmax(np.abs(permCorrs))
                permSign = int(np.sign(permCorrs[permInd]))
                newWfm = permSign * self[permInd]
                usedPermInds.append(permInd)
            newBundle.addDim(newWfm)
        return newBundle


class FunctionalBasis(FunctionBundle):
    ''' A FunctionBundle that supports additional linear algebra methods

        Created for weighted addition, decomposition, and component analysis
    '''

    # def __init__(self, measFunList=None):
    #     ''' Can be initialized fully, or initialized with None to be built interactively.

    #         Args:
    #             measFunList (list[MeasuredFunction],None): list of MeasuredFunctions that must have the same abscissa.
    #     '''
    #     super().__init__(measFunList)

    @classmethod
    def independentDefault(cls, nDims):
        ''' Gives a basis of non-overlapping pulses. Waveforms only
        '''
        newAbsc = np.linspace(0, 1, 1000)
        pWid = .5 / nDims
        newObj = cls()
        for iDim in range(nDims):
            on = (iDim + .25) / nDims
            sig = Waveform.pulse(newAbsc, tOn=on, tOff=on + pWid)
            newObj.addDim(sig)
        return newObj

    def innerProds(self, trial):
        ''' takes the inner products of the trial function onto this basis.
        '''
        tvec = self._putInTimebase(trial)
        tmat = np.tile(tvec, (self.nDims, 1))
        products = np.sum(np.multiply(tmat, self.ordiMat), axis=1).A1
        return products

    def magnitudes(self):
        ''' The inner product of the basis with itself
        '''
        return np.sum(np.multiply(self.ordiMat, self.ordiMat), axis=1).A1

    def project(self, trial):
        ''' Projects onto normalized basis
        If the basis is orthogonal, this is equivalent to weight decomposition
        '''
        return self.innerProds(trial) / self.magnitudes()

    def decompose(self, trial, moment=1):
        ''' Uses the Moore-Penrose pseudoinverse to get weight decomposition without orthogonality

            Args:
                trial (MeasuredFunction): signal to be decomposed
                moment (float): polynomial moment of the basis to use when decomposing
        '''
        tvec = self._putInTimebase(trial)
        momBasis = np.power(self.ordiMat, moment)
        basisInverse = np.linalg.pinv(momBasis)
        return np.dot(tvec, basisInverse).A1

    def matrixMultiply(self, weiMat):
        assert(weiMat.shape[1] == self.nDims)
        outBasis = type(self)()
        for weiVec in weiMat:
            weightedDim = self.weightedAddition(weiVec)
            outBasis.addDim(weightedDim)
        return outBasis

    def getMoment(self, weiVecs=None, order=2, relativeGauss=False):
        ''' This is actually the projected moment. Named for compatibility with bss package

            Make sure weiVecs is two dimensional
        '''
        moms = np.zeros(len(weiVecs))
        for iv, v in enumerate(weiVecs):
            weighted = self.weightedAddition(v)
            calcMom = weighted.moment(order, relativeGauss=relativeGauss)
            moms[iv] = calcMom
        return moms

    def remainder(self, trial):
        ''' Gives the remaining parts of the signal that are not explained by the minimum-squared-error decomposition
        '''
        explainedWeights = self.decompose(trial)
        explainedSignal = self.weightedAddition(explainedWeights)
        return trial - explainedSignal

    def covariance(self):
        ''' Returns covariance matrix of the basis, which is nDims x nDims '''
        return np.cov(self.ordiMat)


# Argument sanitizing
def verifyListOfType(arg, checkType):
    ''' Checks to see if the argument is a list or a single object of the checkType
    Returns a list, even if it is length one
    If arg is None, it returns None
    '''
    if arg is None:
        return None
    if isinstance(arg, checkType):
        arg = [arg]
    if isinstance(arg, (list, tuple)):
        for a in arg:
            if not isinstance(a, checkType):
                raise Exception('Incorrect type, expecting ' + str(checkType) +
                                '. Got ' + str(type(a)))
    return arg


def argFlatten(*argLists, typs=(list, tuple, set)):
    ''' Takes a combination of multiple arguments and flattens the ones of type typs.
        None arguments are ignored, no error.

        Args:
            *argLists: multiple arguments that could be lists or tuples
            typs (tuple): types of things to flatten

        Returns:
            (tuple)

        It goes like this::

            dUtil.argFlatten()                                        # == ()
            dUtil.argFlatten(1)                                       # == (1,)
            dUtil.argFlatten((3, 4))                                  # == (3, 4)
            dUtil.argFlatten(1, (3, 4), np.zeros(2))                  # == (1, 3, 4, ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2))                  # == (1, 3, 4, ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2), typs=tuple)      # == (1, [3, 4], ndarray([0,0]))
            dUtil.argFlatten(1, [3, 4], np.zeros(2), typs=np.ndarray) # == (1, [3, 4], 0., 0.)
    '''
    flatList = []
    for arg in argLists:
        if arg is None:
            continue
        if not isinstance(arg, typs):
            arg = [arg]
        flatList.extend(list(arg))
    return tuple(flatList)


MANGLE_LEN = 256  # magic constant from compile.c


def mangle(name, klass):
    ''' Sanitizes attribute names that might be "hidden,"
        denoted by leading '__'. In :py:class:`~lightlab.laboratory.Hashable` objects,
        attributes with this kind of name can only be class attributes.

        See :py:mod:`~tests.test_instrument_overloading` for user-side implications.

        Behavior::

            mangle('a', 'B') == 'a'
            mangle('_a', 'B') == '_a'
            mangle('__a__', 'B') == '__a__'
            mangle('__a', 'B') == '_B__a'
            mangle('__a', '_B') == '_B__a'
    '''
    if not name.startswith('__'):
        return name
    if len(name) + 2 >= MANGLE_LEN:
        return name
    if name.endswith('__'):
        return name
    try:
        i = 0
        while klass[i] == '_':
            i = i + 1
    except IndexError:
        return name
    klass = klass[i:]

    tlen = len(klass) + len(name)
    if tlen > MANGLE_LEN:
        klass = klass[:MANGLE_LEN - tlen]

    return "_%s%s" % (klass, name)


# Simple common array operations
def rms(diffArr, axis=0):
    return np.sqrt(np.mean(diffArr ** 2, axis=axis))


def minmax(arr):
    ''' Returns a list of [min and max] of the array '''
    return np.array([np.min(arr), np.max(arr)])
