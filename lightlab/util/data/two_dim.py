'''
    Two dimensional measured objects where the second abscissa variable is either
        * discrete (:class:`FunctionBundle`), or
        * continuous (:class:`MeasuredSurface`)
'''
import matplotlib.pyplot as plt
import numpy as np
from scipy import interpolate
import matplotlib.cm as cm

from .one_dim import MeasuredFunction, Waveform


class FunctionBundle(object):  # pylint: disable=eq-without-hash
    ''' A bundle of :class:`~lightlab.util.data.one_dim.MeasuredFunction`'s: "z" vs. "x", "i"

        The key is that they have the same abscissa base.
        This class will take care of resampling in a common abscissa base.

        The bundle can be:
            * iterated to get the individual :class`~lightlab.util.data.one_dim.MeasuredFunction`'s
            * operated on with other ``FunctionBundles``
            * plotted with :meth`simplePlot` and :meth:`multiAxisPlot`

        Distinct from a :class:`MeasuredSurface` because
        the additional axis does not represent a continuous thing.
        It is discrete and sometimes unordered.

        Distince from a :class:`FunctionalBasis` because
        it does not support most linear algebra-like stuff
        (e.g. decomposision, matrix multiplication, etc.).
        This is not a strict rule.
    '''

    def __init__(self, measFunList=None):
        ''' Can be initialized fully, or initialized with None to be built interactively.

            Args:
                measFunList (list[MeasuredFunction] or None): list of MeasuredFunctions that must have the same abscissa.
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

            Todo:
                This should handle slices.
                If it gets a slice, it should return a function bundle
        '''
        theOrdi = self.ordiMat[
            index, :].A1  # A1 is a special numpy thing that converts from matrix to 1-d array
        return self.memberType(self.absc, theOrdi)

    def __len__(self):
        return self.ordiMat.shape[0]

    def __eq__(self, other):
        return (self.memberType is other.memberType and
                self.absc == other.absc and
                self.ordiMat == other.ordiMat)

    def __add__(self, other):
        if np.isscalar(other):
            other = np.ones(self.nDims) * other
        newObj = self.copy()
        for iDim in range(self.nDims):
            newObj.ordiMat[iDim] = self.ordiMat[iDim] + other[iDim]
        return newObj

    def __radd__(self, other):
        return self.__add__(other)

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

    def debias(self):
        ''' Returns a bundle with each waveform in unit variance '''
        newBundle = type(self)()
        for wfm in self:
            newBundle.addDim(wfm.debias())
        return newBundle

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
        if len(axList) != len(self):
            raise ValueError('Wrong number of axes. Got {}, need {}.'.format(
                len(axList), len(self)))
        for i, ax in enumerate(axList):
            plt.sca(ax)
            self[i].simplePlot(*args, **kwargs)
            if titleRoot is not None:
                plt.title(titleRoot.format(i + 1))
                # plt.xlabel('Time (s)')
            if i < len(self) - 1:
                ax.xaxis.set_ticklabels([])
                ax.set_xlabel('')
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


class MeasuredSurface(object):
    ''' Basically a two dimensional measured function: "z" vs. "x", "y"

        Useful trick when gathering data: build incrementally using :meth:`FunctionBundle.addDim`,
        then convert that to this class using :meth:`MeasuredSurface.fromFunctionBundle`.
    '''

    def __init__(self, absc, ordi):
        '''
            Args:
                absc (ndarray): same meaning as measured function
                ordi (ndarray): two-dimensional array or matrix
        '''
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

            Args:
                otherBund (FunctionBundle): The source. The ordering of functions matters
                addedAbsc (np.ndarray): the second dimension abscissa array (default, integers)

            Returns:
                (:class:`MeasuredSurface`) new object
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
        if 'cmap' not in kwargs.keys():
            kwargs['cmap'] = cm.inferno  # pylint: disable=no-member
        if 'shading' not in kwargs.keys():
            kwargs['shading'] = 'flat'
        YY, XX = np.meshgrid(self.absc[0], self.absc[1])
        plt.pcolormesh(XX, YY, np.array(self.ordi.T), *args, **kwargs)
        plt.autoscale(tight=True)


class Spectrogram(MeasuredSurface):
    pass


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
