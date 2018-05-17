''' One-dimensional data structures with substantial processing abilities
'''
import matplotlib.pyplot as plt
import numpy as np
from IPython import display
import lightlab.util.io as io

from .peaks import findPeaks, ResonanceFeature
from .basic import rms
from .function_inversion import interpInverse


class MeasuredFunction(object):  # pylint: disable=eq-without-hash
    ''' Array of x,y points.
        This is the workhorse class of ``lightlab`` data structures.
        Examples can be found throughout Test notebooks.

        Supports many kinds of operations:

        1. Data access (``mf(x)``, ``len(mf)``, ``mf[i]``, :meth:`getData`)
            Calling the object with x-values interpolates and returns y-values.

        2. Storage (:meth:`copy`, :meth:`save`, :meth:`load`, :meth:`loadFromFile`)
            see method docstrings

        3. x-axis signal processing (:meth:`getSpan`, :meth:`crop`, :meth:`shift`, :meth:`flip`, :meth:`resample`, :meth:`uniformlySample`)
            see method docstrings

        4. y-axis signal processing (:meth:`getRange`, :meth:`clip`, :meth:`debias`, :meth:`unitRms`, :meth:`getMean`, :meth:`moment`)
            see method docstrings

        5. Advanced signal processing (:meth:`invert`, :meth:`lowPass`, :meth:`centerOfMass`, :meth:`findResonanceFeatures`)
            see method docstrings

        6. Binary math (``+``, ``-``, ``*``, ``/``, ``==``)
            Operands must be either
                * the same subclass of MeasuredFunction, or
                * scalar numbers, or
                * functions/bound methods: these must be callable with one argument that is an ndarray

            If both are MeasuredFunction, the domain used will be the smaller of the two

        7. Plotting (:meth:`simplePlot`)
            Args and Kwargs are passed to pyplot's plot function.
            Supports live plotting for notebooks

        8. Others (:meth:`deleteSegment`, :meth:`splice`)
            see method docstrings
    '''

    absc = None  #: abscissa, a.k.a. the x-values or domain
    ordi = None  #: ordinate, a.k.a. the y-values

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

    def save(self, savefile):
        io.saveMat(savefile, {'absc': self.absc, 'ordi': self.ordi})

    @classmethod
    def load(cls, savefile):
        dataDict = io.loadMat(savefile)
        absc = dataDict['absc']
        ordi = dataDict['ordi']
        return cls(absc, ordi)

    def simplePlot(self, *args, livePlot=False, **kwargs):
        r''' Plots on the current axis

        Args:
            livePlot (bool): if True, displays immediately in IPython notebook
            \*args (tuple): arguments passed through to ``pyplot.plot``
            \*\*kwargs (dict): arguments passed through to ``pyplot.plot``

        Returns:
            Whatever is returned by ``pyplot.plot``
        '''
        curve = plt.plot(*(self.getData() + args), **kwargs)
        if 'label' in kwargs.keys():
            plt.legend()
        if livePlot:
            display.display(plt.gcf())
            display.clear_output(wait=True)
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

    def reverse(self):
        ''' Flips the ordinate, keeping abscissa in order

            Returns:
                MeasuredFunction: new object
        '''
        return self.__newOfSameSubclass(self.absc, self.ordi[::-1])

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
                None: it modifies this object
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

    def findResonanceFeatures(self, **kwargs):
        r''' A convenient wrapper for :func:`~lightlab.util.data.peaks.findPeaks`

            Args:
                \*\*kwargs: passed to :func:`~lightlab.util.data.peaks.findPeaks`

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

    # Mathematics

    def __binMathHelper(self, other):
        ''' returns the new abcissa and a tuple of arrays: the ordinates to operate on
        '''
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

    def __eq__(self, other):
        if isinstance(self, type(other)):
            return np.all(self.absc == other.absc) and np.all(self.ordi == other.ordi)
        return False


class Spectrum(MeasuredFunction):
    ''' Adds handling of linear/dbm units.

        Use :meth:`lin` and :meth:`dbm` to make sure what you're getting
        what you expect for things like binary math and peakfinding, etc.
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

    def simplePlot(self, *args, livePlot=False, **kwargs):
        ''' More often then not, this is db vs. wavelength, so label it
        '''
        super().simplePlot(*args, livePlot=livePlot, **kwargs)
        plt.xlabel('Wavelength (nm)')
        plt.ylabel('Transmission ({})'.format('dB' if self.inDbm else 'lin'))

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
        r''' Overloads :meth:`.MeasuredFunction.findResonanceFeatures` to make sure it's in db scale

            Args:
                \*\*kwargs: kwargs passed to :mod:`~lightlab.util.data.peaks.findPeaks`

            Returns:
                list[ResonanceFeature]: the detected features as nice objects
        '''
        kwargs['isDb'] = True
        return MeasuredFunction.findResonanceFeatures(self.db(), **kwargs)


class Waveform(MeasuredFunction):
    ''' Typically used for time, voltage functions.
        This is very similar to what is referred to as a "signal."

        Has class methods for generating common time-domain signals
    '''
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
