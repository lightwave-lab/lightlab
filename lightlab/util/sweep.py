''' Generalized sweep classes
'''

import matplotlib.pyplot as plt
import numpy as np
import time
from IPython import display
import matplotlib.cm
from collections import OrderedDict

from lightlab.util.data import argFlatten, rms
from lightlab.util.plot import plotCovEllipse
import lightlab.util.io as io
from lightlab import logger


class Sweeper(object):
    plotOptions = None
    monitorOptions = None

    def __init__(self):
        self.data = None
        self.savefile = None
        self.plotOptions = dict()
        self.monitorOptions = dict()

    def gather(self):
        print('gather method must be overloaded in subclass')

    def save(self, savefile=None):
        ''' Save data only

            Args:
                savefile (str/Path): file to save
        '''
        if savefile is None:
            if self.savefile is not None:
                savefile = self.savefile
            else:
                raise ValueError('No save file specified')
        io.savePickle(savefile, self.data)

    def load(self, savefile=None):
        ''' This is basically make it so that gather() and load() have the same effect.

            It does not keep actuation or measurement members, only whatever was put in self.data

            Args:
                savefile (str/Path): file to load
        '''
        if savefile is None:
            if self.savefile is not None:
                savefile = self.savefile
            else:
                raise ValueError('No save file specified')
        self.data = io.loadPickle(savefile)

    def setPlotOptions(self, **kwargs):
        ''' Valid options for NdSweeper
                * plType
                * xKey
                * yKey
                * axArr
                * cmap-surf
                * cmap-curves

            Valid options for CommandControlSweeper
                * plType
        '''
        for k, v in kwargs.items():
            if k not in self.plotOptions.keys():
                logger.warning(k, '%s is not a valid plot option.')
                logger.warning('Valid ones are %s', self.plotOptions.keys())
            else:
                self.plotOptions[k] = v
        return self.plotOptions

    def setMonitorOptions(self, **kwargs):
        ''' Valid options for NdSweeper
                * livePlot
                * plotEvery
                * stdoutPrint
                * runServer

            Valid options for CommandControlSweeper
                * livePlot
                * plotEvery
                * stdoutPrint
                * runServer
                * cmdCtrlPrint
        '''
        for k, v in kwargs.items():
            if k not in self.monitorOptions.keys():
                logger.warning(k, '%s is not a valid monitor option.')
                logger.warning('Valid ones are %s', self.monitorOptions.keys())
            else:
                self.monitorOptions[k] = v
        return self.monitorOptions

    @classmethod
    def fromFile(cls, filename):
        new = cls()
        new.load(filename)
        return new


class Actuation(object):
    function = None
    domain = None
    doOnEveryPoint = None

    def __init__(self, function=None, domain=None, doOnEveryPoint=False):
        self.function = function
        self.domain = domain
        self.doOnEveryPoint = doOnEveryPoint


class NdSweeper(Sweeper):
    ''' Generic sweeper.

        Here's the difference between measure and parse:
            measure is a call to something, usually an instrument and some simpe post processing, like peak finding.
                * It is stored in data
                * When subsuming, only unique measurements are kept

            parse gets this in a form to visualize interactively, perhaps save and/or score along the way
                * When subsuming, all parse functions are maintained

        Make sure that measure is *bound* if it is a method
    '''
    measure = None
    actuate = None
    parse = None
    static = None

    def __init__(self):
        ''' Specify the hard domain and actuate dimensions

            The sweep dimension order is major first, so put your slow actuations (e.g. tuning lasers)
                before the fast actuations (e.g. tuning current source)

            Args:
                domain (tuple, iterable): the sweep values, or a tuple of sweep values for different dimensions
                actuate (tuple, procedure-like): procedure, one argument per, that is called for each line of the sweep.
                    Return is optional
                actuNames (tuple, str, None): Names of actuator return values.
                    These are stored as data if present, under the key ''actuName-return''
                measure (dict): dict of functions, no arguments, called at every point.
                    Use descriptive keys please.
                parse (dict): dict of functions, operate on measurements, produce scalars
                    Use descriptive keys please.
        '''
        super().__init__()
        self.reinitActuation()

        self.measure = OrderedDict()
        self.actuate = OrderedDict()
        self.parse = OrderedDict()
        self.static = OrderedDict()

        self.monitorOptions = {'livePlot': False, 'plotEvery': 1,
                               'stdoutPrint': True, 'runServer': False}
        self.plotOptions = {'plType': 'curves', 'xKey': None, 'yKey': None, 'axArr': None,
                            'cmap-surf': matplotlib.cm.inferno, 'cmap-curves': matplotlib.cm.viridis}  # pylint: disable=no-member

    @classmethod
    def repeater(cls, nTrials):
        new = cls()
        new.addActuation('trial', lambda a: None, np.arange(nTrials))
        return new

    def gather(self, soakTime=None, autoSave=False, returnToStart=False):  # pylint: disable=arguments-differ
        ''' Perform the sweep

            Args:
                soakTime (None, float): wait this many seconds at the first point to let things settle
                autoSave (bool): save data on completion, if savefile is specified
                returnToStart (bool): If True, actuates everything to the first point after the sweep completes

            Returns:
                None
        '''
        # Initialize builders that start off with None grids
        if self.data is None:
            oldData = None
            self.data = OrderedDict()
        else:
            oldData = self.data.copy()
            for dKeySrc in (self.actuate, self.measure, self.parse):
                for dKey in dKeySrc.keys():
                    try:
                        del self.data[dKey]
                    except KeyError:
                        pass
        try:
            swpName = 'Generic sweep in ' + ', '.join(self.actuate.keys())
            prog = io.ProgressWriter(swpName, self.swpShape, **self.monitorOptions)

            # Soak at the first point
            if soakTime is not None:
                logger.debug('Soaking for %s seconds.', soakTime)
                for actuObj in self.actuate.values():
                    actuObj.function(actuObj.domain[0])
                time.sleep(soakTime)

            for index in np.ndindex(self.swpShape):
                pointData = OrderedDict()  # Everything that will be measured *at this index*

                for statKey, statMat in self.static.items():
                    pointData[statKey] = statMat[index]

                # Do the actuation, storing domain args and return values (if present)
                for iDim, actu in enumerate(self.actuate.items()):
                    actuKey, actuObj = actu
                    if actuObj.domain is None:
                        x = None
                    else:
                        x = actuObj.domain[index[iDim]]
                        pointData[actuKey] = x
                    if iDim == self.actuDims - 1 or index[iDim + 1] == 0 or actuObj.doOnEveryPoint:
                        y = actuObj.function(x)  # The actual function call occurs here
                        if y is not None:
                            pointData[actuKey + '-return'] = y

                # Do the measurement, store return values
                for measKey, measFun in self.measure.items():
                    pointData[measKey] = measFun()
                    # print('   Meas', measKey, ':', pointData[measKey])

                # Parse and store
                for parseKey, parseFun in self.parse.items():
                    try:
                        pointData[parseKey] = parseFun(pointData)
                    except KeyError as err:
                        if parseKey in self.parse.keys():
                            print('Parsing out of order.',
                                  'Parser', parseKey, 'depends on parser', err,
                                  'but is being executed first')
                        raise err

                # Insert point data into the full matrix data builder
                # On the first go through, initialize array of correct datatype
                for k, v in pointData.items():
                    if all(i == 0 for i in index):
                        if np.isscalar(v):
                            self.data[k] = np.zeros(self.swpShape, dtype=float)
                        else:
                            self.data[k] = np.empty(self.swpShape, dtype=object)
                    self.data[k][index] = v

                # Plotting during the sweep
                if self.monitorOptions['livePlot']:
                    if all(i == 0 for i in index):
                        axArr = None
                    axArr = self.plot(axArr=axArr, index=index)
                    flatIndex = np.ravel_multi_index(index, self.swpShape)
                    if flatIndex % self.monitorOptions['plotEvery'] == 0:
                        display.display(plt.gcf())
                        display.clear_output(wait=True)
                # Progress report
                prog.update()
            # End of the main loop

        except Exception as err:
            logger.error('Error while sweeping. Reloading old data')
            self.data = oldData
            raise err

        if returnToStart:
            for actuObj in self.actuate.values():
                actuObj.function(actuObj.domain[0])

        if autoSave:
            self.save()

    def addActuation(self, name, function, domain, doOnEveryPoint=False):
        ''' Specify an actuation dimension: what is called, the domain values to use as arguments.

            Args:
                name (str): key for accessing this actuator's value data
                function (func): actuation function, usually linked to hardware. One argument.
                domain (ndarray, None): 1D array of arguments that will be passed to the function.
                    If None, the function is called with a None argument every point (if doOnEveryPoint is True).
                doOnEveryPoint (bool): call this function in the inner loop (True)
                    or once before the corresponding rows(False)
        '''
        newActu = Actuation(function, domain, doOnEveryPoint)
        self.addActuationObject(name, newActu)

    def addActuationObject(self, name, actuationObj):
        self.actuate[name] = actuationObj
        self._recalcSwpShape()
        # If any static data is present, expand it into the new dimension
        # when you add an actuation, it goes in the lowest index (highest number)
        # so if you do data_new[..., 0], you get data_old
        for statKey, statVal in self.static.items():
            tileBy = (len(actuationObj.domain),) + statVal.ndim * (1,)
            self.static[statKey] = np.tile(statVal, tileBy).T

    def reinitActuation(self):
        self.actuate = OrderedDict()
        self.static = OrderedDict()
        self._recalcSwpShape()

    def _recalcSwpShape(self):
        self.actuDims = 0  # pylint: disable=attribute-defined-outside-init
        self.swpShape = ()  # pylint: disable=attribute-defined-outside-init
        for actu in self.actuate.values():
            if actu.domain is not None:
                self.actuDims += 1
                self.swpShape += (len(actu.domain), )

    def addMeasurement(self, name, function):
        ''' Specify a measurement to be taken at every sweep point.

            Args:
                name (str): key for accessing this measurement's value data
                function (func): measurement function, usually linked to hardware. No arguments.
        '''
        self.measure.update([(name, function)])

    def addParser(self, name, function):
        ''' Adds additional parsing formulas to data, and reparses, if data has been taken

            Args:
                name (str): key for accessing this parser's value data
                function (func): parsing function, not linked to hardware. One dictionary argument.
        '''
        self.parse.update([(name, function)])
        try:
            self._reparse(name)
        except KeyError:
            self.data[name] = None

    def _reparse(self, parseKeys=None):
        ''' Reprocess measured data into parsed data.
            If there is not enough data present, it does nothing.
            If the parser depends on

            Args:
                parseKeys (tuple, str, None): which parsers to recalculate. If None, does all.
                    Execution order depends on addParser calls, not parseKeys

            Returns:
                None
        '''
        if self.data is None:
            return
        if parseKeys is None:
            parseKeys = tuple(self.parse.keys())
        else:
            parseKeys = argFlatten(parseKeys, typs=tuple)

        for pk, pFun in self.parse.items():  # We're indexing this way to make sure parsing is done in the order of parse attribute, not the order of parseKeys
            if pk not in parseKeys:
                continue
            tempDataMat = np.zeros(self.swpShape)
            for index in np.ndindex(self.swpShape):
                dataOfPt = OrderedDict()
                for datKey, datVal in self.data.items():
                    if np.any(datVal.shape != self.swpShape):
                        logger.warning(
                            'Data member %s is wrong size for reparsing %s. Skipping.', datKey, pk)
                    else:
                        dataOfPt[datKey] = datVal[index]
                try:
                    tempDataMat[index] = pFun(dataOfPt)
                except KeyError:
                    logger.warning('Parser %s depends on unpresent data. Skipping.', pk)
                    break
            else:
                self.data[pk] = tempDataMat

    def addStaticData(self, name, contents):
        ''' Add a ndarray or scalar that can be referenced by parsers

            The array's shape must match that of the currently loaded actuation grid.

            If you then :meth:`addActuation`, the static data automatically expands in dimension to accomodate.
            Values are filled by tiling in the new dimension.

            Add static data after the actuations that have different static data,
            but before the actuations for which you want that data to be constant.

            Args:
                name (str): key for accessing this data
                contents (scalar, ndarray): data contents
        '''
        if np.isscalar(contents):
            contents *= np.ones(self.swpShape)
        if np.any(contents.shape != self.swpShape):
            raise ValueError('Static data ' + name + ' is wrong shape for sweep.' +
                             'Need ' + str(self.swpShape) + '. Got ' + str(contents.shape) +
                             'The order that actuations and static data are added matter.')
        self.static[name] = contents

    def subsume(self, other, useMinorOptions=False):
        ''' Makes the argument sweep a minor sweep within this one

            The new measurement dictionary will contain all measurements of both.
                If there is a duplicate key, the self measurement will take precedence

            Existing data is discarded.

            Args:
                other (NdSweeper): the minor sweep
                useMinorOptions (bool): where do the options come from? If False, they come from the major (i.e. self)
        '''
        if issubclass(type(other), type(self)):
            new = self.copy(includeData=False)
            for aNam, aObj in other.actuate.items():
                if aNam not in new.actuate.keys():
                    new.addActuationObject(aNam, aObj)
            for mNam, mVal in other.measure.items():
                if mNam not in new.measure.keys():
                    new.addMeasurement(mNam, mVal)
            for pNam, pVal in other.parse.items():
                if pNam not in new.parse.keys():
                    new.addParser(pNam, pVal)
            if useMinorOptions:
                new.plotOptions.update(other.plotOptions)
                new.monitorOptions.update(other.monitorOptions)
            return new
        elif type(other) is CommandControlSweeper:
            # do something else entirely
            raise NotImplementedError('subsuming CommandControlSweeper')

    def copy(self, includeData=True):
        ''' Shallow copy, which means function pointers are maintained

            If includeData, it does a deep copy of data
        '''
        new = NdSweeper()
        for aNam, aObj in self.actuate.items():
            new.addActuationObject(aNam, aObj)
        for mNam, mVal in self.measure.items():
            new.addMeasurement(mNam, mVal)
        for pNam, pVal in self.parse.items():
            new.addParser(pNam, pVal)
        if includeData:
            from copy import deepcopy
            new.data = deepcopy(self.data)
        new.plotOptions.update(self.plotOptions)
        new.monitorOptions.update(self.monitorOptions)
        return new

    def plot(self, slicer=None, tempData=None, index=None, axArr=None, pltKwargs=None):
        ''' Plots

            Much of the behavior to figure out labels and numbers for axes comes from the plotOptions attribute.

            The xKeys and yKeys are keys within this objects **data** dictionary (actuation, measurement, and parsers)
                The total number of plots will be the product of len('xKey') and len('yKey').
                xKeys can be anything, including parsed data members. By default it is the minor actuation variable
                yKeys can also be anything that has scalar elements.
                By default it is everything that is currently present, except xKeys and non-scalars

            When doing line plots in 2D sweeps, the legend does automatic labelling.
                Each line must correspond to an actuation dimension, otherwise it doesn't make sense.
                    This is despite the fact that the xKeys can still be anything.
                Usually, each line corresponds to a particular domain value of the major sweep axis;
                    however, if that is specified as an xKey, the lines will correspond to the minor axis.

            Surface plotting:
                Ignores whatever is in xKeys. The plotting domain is locked to the actuation domain in order to keep a rectangular grid.
                The values indicated in yKeys will become color data.

            Args:
                slicer (tuple, slice): domain slices
                axArr (ndarray), plt.axis): axes to plot on. Equivalent to what is returned by this method
                pltKwargs: passed through to plotting function

            Todo:
                * Graphics caching for 2D line plots
        '''
        global hCurves  # pylint: disable=global-statement
        if index is None or np.all(np.array(index) == 0):
            hCurves = None

        if pltKwargs is None:
            pltKwargs = {}

        # Which data dict to use and its dimensionality
        if tempData is None:
            fullData = self.data
        else:
            fullData = tempData
        if fullData is not None:
            plotDims = list(fullData.values())[0].ndim  # Instead of self.actuDims
        else:
            plotDims = self.actuDims
        assertValidPlotType(self.plotOptions['plType'], plotDims, type(self))
        # Cuts down the domain to the region of interest
        if slicer is None:
            slicer = (slice(None),) * plotDims
        else:
            slicer = argFlatten(slicer, typs=tuple)

        # Figure out what the keys of data are
        actuationKeys = list(self.actuate.keys())
        xKeys = argFlatten(self.plotOptions['xKey'], typs=tuple)
        yKeys = argFlatten(self.plotOptions['yKey'], typs=tuple)
        if len(xKeys) == 0:
            # default is the most minor sweep domain
            xKeys = (actuationKeys[-1], )
        if len(yKeys) == 0:
            # default is all scalar ranges
            for datKey, datVal in fullData.items():
                if (datKey not in xKeys and
                        datKey not in actuationKeys and
                        np.isscalar(datVal.item(0))):
                    yKeys += (datKey, )
        # Check it
        if (len(xKeys) == 0 or len(yKeys) == 0):
            raise ValueError('No axis key specified explicitly or found in self.actuate')
        for k in xKeys + yKeys:
            if k not in fullData.keys():
                raise KeyError(k + ' not found in data keys. ' +
                               'Available data are ' + ', '.join(fullData.keys()))

        # Make grid of axes based on number of pairs of variables
        plotArrShape = np.array([len(yKeys), len(xKeys)])
        if axArr is not None:
            pass
        elif self.plotOptions['axArr'] is not None:
            axArr = self.plotOptions['axArr']
        else:
            _, axArr = plt.subplots(nrows=plotArrShape[0], ncols=plotArrShape[1],
                                    figsize=(10, plotArrShape[0] * 2.5))  # pylint: disable=unused-variable

        axArr = np.array(axArr)
        # Force into a two dimensional array
        if axArr.ndim == 2:
            pass
        elif axArr.ndim == 1:
            if np.all(plotArrShape == 1):
                axArr = np.expand_dims(axArr, 0)
            elif plotArrShape[0] == 1:
                axArr = np.expand_dims(axArr, 0)
            elif plotArrShape[1] == 1:
                axArr = np.expand_dims(axArr, 1)
        elif axArr.ndim == 0:
            if np.all(plotArrShape == 1):
                axArr = np.expand_dims(np.expand_dims(axArr, 0), 0)
        # Check it
        if np.any(axArr.shape != plotArrShape):
            raise ValueError('Shape of axArray does not match plotArrShape')

        # Prepare options for plotting that do not depend on index or line no.
        sample_xK = xKeys[0]
        sample_xData = fullData[sample_xK][slicer]
        if self.plotOptions['plType'] == 'curves':
            pltArgs = ('.-', )
            if plotDims == 1:
                if hCurves is None:
                    hCurves = np.empty(axArr.shape, dtype=object)
            elif plotDims == 2:
                invertDomainPriority = False
                autoLabeling = (plotDims == self.actuDims)
                if autoLabeling:
                    if actuationKeys[0] != sample_xK:
                        curveKey = actuationKeys[0]
                    else:
                        curveKey = actuationKeys[1]
                        if index is not None:
                            index = index[::-1]
                        invertDomainPriority = True
                nLines = sample_xData.shape[0 if not invertDomainPriority else 1]
                colors = self.plotOptions['cmap-curves'](np.linspace(0, 1, nLines))

        # Loop over axes (i.e. axis key variables) and plot
        for iAx, ax in np.ndenumerate(axArr):
            xK = xKeys[iAx[1]]
            yK = yKeys[iAx[0]]
            # dereference and slice
            xData = fullData[xK][slicer]
            yData = fullData[yK][slicer]

            if self.plotOptions['plType'] == 'curves':
                if plotDims == 1:
                    # slice it
                    if index is not None:
                        xData = xData[:index[0] + 1]
                        yData = yData[:index[0] + 1]
                        ax.cla()
                    curv = ax.plot(xData, yData, *pltArgs, **pltKwargs)
                    # caching the part of the line that has already been drawn
                    if hCurves[iAx] is not None:  # pylint:disable=unsubscriptable-object
                        try:
                            hCurves[iAx][0].remove()
                        except ValueError:
                            # it was probably an old one
                            pass
                    hCurves[iAx] = curv
                elif plotDims == 2:
                    ax.cla()  # no caching, just clear
                    if invertDomainPriority:
                        xData = xData.T
                        yData = yData.T

                    for iLine in range(nLines):
                        # slicing data based on what the line and index are
                        xLine = xData[iLine, :]
                        yLine = yData[iLine, :]
                        if index is None:
                            pass
                        elif iLine < index[-2]:  # these lines are complete
                            pass
                        elif iLine == index[-2]:  # these lines are in-progress
                            xLine = xLine[slice(index[-1] + 1)]
                            yLine = yLine[slice(index[-1] + 1)]
                        elif iLine > index[-2]:  # these have not been started
                            break
                        # line options
                        pltKwargs['color'] = colors[iLine][:3]
                        if autoLabeling:
                            curveValue = self.actuate[curveKey].domain[iLine]
                            pltKwargs['label'] = '{} = {:.2f}'.format(curveKey, curveValue)
                        ax.plot(xLine, yLine, *pltArgs, **pltKwargs)
                    # legend
                    if autoLabeling and iAx[0] == 0 and iAx[1] == plotArrShape[1] - 1:  # AND it is the top right
                        ax.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
                else:
                    raise ValueError('Too many dimensions in sweep to plot. '
                                     'This should have been caught by assertValidPlotType.')

                if iAx[0] == plotArrShape[0] - 1:
                    ax.set_xlabel(xK)
                else:
                    ax.tick_params(labelbottom=False)
                if iAx[1] == 0:
                    ax.set_ylabel(yK)
                else:
                    ax.tick_params(labelleft=False)
            elif self.plotOptions['plType'] == 'surf':
                # xKeys we treat as meaningless. just use the actuation domains
                # We treat yData as color data
                doms = [None] * 2
                for iDim, actuObj in enumerate(self.actuate.values()):
                    doms[iDim] = actuObj.domain[slicer[iDim]]
                domainGrids = np.meshgrid(*doms[::-1], indexing='xy')
                pltKwargs['cmap'] = pltKwargs.pop('cmap', self.plotOptions['cmap-surf'])
                pltKwargs['shading'] = pltKwargs.pop('shading', 'gouraud')
                cax = ax.pcolormesh(*domainGrids, yData, **pltKwargs)
                plt.gcf().colorbar(cax, ax=ax)
                ax.autoscale(tight=True)
                ax.set_title(yK)
                if iAx[0] == plotArrShape[0] - 1:
                    ax.set_xlabel(actuationKeys[1])
                else:
                    ax.tick_params(labelbottom=False)
                ax.set_ylabel(actuationKeys[0])
        return axArr

    def saveObj(self, savefile=None):
        ''' Also saves what are the actuation keys.
            This is important for plotting when you reload
        '''
        if savefile is None:
            if self.savefile is not None:
                savefile = self.savefile
            else:
                raise ValueError('No save file specified')
        self.data['actuation-keys'] = list(self.actuate.keys())
        super().save(savefile)
        self.data.pop('actuation-keys')

    @classmethod
    def loadObj(cls, savefile, functionSource=None):
        ''' savefile must have been saved with saveObj.
            It restores actuation names and domains to help with plotting.

            Functions referring to equipment cannot be saved.
            If you give it a functionSource, then those can be restored.
            This is very useful if you have a parser such as live plot spectra,
            or move stuff here or there. Also useful if you want to re-gather
            for some reason.
        '''
        newObj = cls.fromFile(savefile)
        # Restore actuations
        try:
            actuationKeys = newObj.data.pop('actuation-keys')
        except KeyError:
            pass
        else:
            for iAct, actuName in enumerate(actuationKeys):
                # Try to extract the actuation function (not domain)
                if functionSource is not None:
                    actuObj = functionSource.actuate[actuName]
                else:
                    # no function was given, so gathering won't work
                    actuObj = Actuation()
                # Full data as taken, which is N-dimensional
                actData = newObj.data[actuName]
                # Extract one vector along the right direction to serve as domain
                sliceOneDim = [0] * len(actuationKeys)
                sliceOneDim[iAct] = slice(None)
                actuObj.domain = actData[sliceOneDim]
                # Do the full add
                newObj.addActuationObject(actuName, actuObj)
        newObj._recalcSwpShape()  # pylint: disable=protected-access

        # Restore parsers. Do not reparse them
        if functionSource is not None:
            newObj.parse = functionSource.parse
        return newObj

    def load(self, savefile=None):
        super().load(savefile)
        self._recalcSwpShape()


def simpleSweep(actuate, domain, measure=None):
    ''' Basic sweep in one dimension, without function keys, parsing, or plotting.

        Args:
            actuate (function): a procedure or function of one argument called at every point
            domain (ndarray): elements passed as an argument to actuate for each point
            measure (function, None): a function of no arguments called at every point. None means the return of actuate will act as the measurement

        Returns:
            (ndarray): what is measured. Same length as domain
    '''
    swpObj = NdSweeper()
    swpObj.addActuation('act0', actuate, domain)  # pylint:disable=no-member
    if measure is not None:
        swpObj.addMeasurement('meas0', measure)
    swpObj.setMonitorOptions(stdoutPrint=False)
    swpObj.gather()
    if measure is not None:
        return swpObj.data['meas0']
    else:
        return swpObj.data['act0-return']


class CommandControlSweeper(Sweeper):
    ''' Generic command-control sweep for evaluating a controller.

        The command function called at each point takes one argument that is an array (length M) and returns an array **of equal length**.

        The sweep is N (<= M) dimensional.
            * The user specifies the mapping between the sweep domain and the argument/return array indeces
            * The user specifies defaults for the other (M-N) arguments
            * Some of the uncontrolled arguments can be monitored

        Todo:
            How can we get this subsumed by a NdSweeper for trial repetition. CommandControlSweeper shouldn't be able to subsume as major
    '''
    def __init__(self, evaluate, defaultArg, swpInds, domain, nTrials=1):
        '''
            Args:
                evaluate (function): called at each point with array args/returns of equal length
                defaultArg (ndarray): default value that will be sent to the evaluate function
                swpIndeces (tuple, int): which channels to sweep
                domain (tuple, iterable): the values over which the sweep channels will be swept
        '''
        super().__init__()
        self.evaluate = evaluate
        self.isScalar = np.isscalar(defaultArg)
        if self.isScalar:
            defaultArg = [defaultArg]
        self.defaultArg = np.array(defaultArg, dtype=float)
        self.allDims = len(self.defaultArg)

        self.swpInds = argFlatten(swpInds, typs=tuple)
        self.swpDims = len(self.swpInds)
        self.domain = argFlatten(domain, typs=tuple)
        self.swpShape = tuple(len(dom) for dom in self.domain)
        if len(self.domain) != self.swpDims:
            raise ValueError('domain and swpInds must have the same dimension.' +
                             'Got {} and {}'.format(len(self.domain), len(self.swpInds)))

        self.plotOptions = {'plType': 'curves'}
        self.monitorOptions = {'livePlot': False, 'plotEvery': 1,
                               'stdoutPrint': True, 'runServer': False, 'cmdCtrlPrint': True}

        # Generate actuation sweep grid
        self.cmdGrid = np.array(np.meshgrid(*self.domain)).T
        assert(self.cmdGrid.shape == self.swpShape + (self.swpDims,))

        self.nTrials = nTrials

    def saveObj(self, savefile=None):
        ''' Instead of just saving data, save the whole damn thing.

            Cannot save evaluate function because it is unbound.

        '''
        if savefile is None:
            if self.savefile is not None:
                savefile = self.savefile
            else:
                raise ValueError('No save file specified')
        tempEvalRef = self.evaluate
        self.evaluate = None
        io.savePickle(savefile, self)
        self.evaluate = tempEvalRef

    @classmethod
    def loadObj(cls, savefile):
        ''' This is basically make it so that gather() and load() have the same effect.

            It does not keep actuation or measurement members, only whatever was put in self.data
        '''
        return io.loadPickle(savefile)

    def gather(self, autoSave=False, randomize=False):  # pylint: disable=arguments-differ
        ''' Executes the sweep

            Todo:
                Store all outputs, but provide a way just to get the controlled ones
        '''
        measGrid = np.zeros((self.nTrials,) + self.swpShape + (self.allDims,))

        swpName = 'Generic command-control sweep'
        prog = io.ProgressWriter(swpName, (self.nTrials,) + self.swpShape, **self.monitorOptions)

        if randomize:
            randizers = [None] * self.swpDims
            for iDim in range(self.swpDims):
                randizers[iDim] = np.random.permutation(self.swpShape[iDim])

        for index in np.ndindex((self.nTrials,) + self.swpShape):
            if randomize:
                index = list(index)
                for iDim in range(self.swpDims):
                    index[iDim + 1] = randizers[iDim][index[iDim + 1]]
                index = tuple(index)
            # iTrial = index[0]
            gridIndex = index[1:]
            cmdArr = self.defaultArg.copy()
            cmdArr[np.array(self.swpInds)] = self.cmdGrid[gridIndex]
            if self.isScalar:
                cmdArr = cmdArr[0]
            measArr = self.evaluate(cmdArr)
            if self.isScalar:
                measArr = np.array([measArr])
            measGrid[index] = measArr
            self.data = measGrid
            if self.monitorOptions['livePlot']:
                self.plot(index)
                flatIndex = np.ravel_multi_index(index, (self.nTrials,) + self.swpShape)
                if flatIndex % self.monitorOptions['plotEvery'] == 0:
                    display.clear_output(wait=True)
                    display.display(plt.gcf())  # Note this may have to be interAx instead of gcf
            if self.monitorOptions['cmdCtrlPrint']:
                print('(trial, gridIndex) =', index)
                print('  cmdArr  = ' + '   '.join(['{:.3f}'.format(v) for v in cmdArr]))
                print('  measArr = ' + '   '.join(['{:.3f}'.format(v) for v in measArr]))
            prog.update()
        if autoSave:
            self.save()

    def toSweepData(self):
        ''' Using the old school temporary definition from conductor

            This will eventually be deprecated
        '''
        monitorInds = tuple(filter(lambda y: y not in self.swpInds, range(self.allDims)))
        cmdMat = self.cmdGrid
        measMat = self.data[..., self.swpInds]
        monitMat = self.data[..., monitorInds] if len(monitorInds) > 0 else None
        return (cmdMat, measMat, monitMat)

    def plot(self, index=None, axArr=None):
        plType = self.plotOptions['plType']
        assertValidPlotType(plType, self.swpDims, type(self))

        if plType == 'cmdErr':
            plotCmdCtrl(self.toSweepData(), index=index, interactive=True, ax=axArr)
        elif plType == 'curves' and self.swpDims == 1:  # currently only works in 1 dimension
            if axArr is not None:
                plt.sca(axArr)
            elif index is None or np.all(index == 0):
                plt.subplots(figsize=(6, 6))
            else:
                plt.cla()
                # display.clear_output(wait=True)
            cmdMat, measMat, monitMat = self.toSweepData()  # pylint: disable=unused-variable
            xFull = cmdMat[:, 0]

            # All points over trials and the sweep parameter
            allPts = measMat[..., 0]
            # Plot the in-progress line
            if index is not None:
                if index[1] > 0:
                    xInProgress = cmdMat[:index[1] + 1, 0]
                    yInProgress = allPts[index[0], :index[1] + 1]
                    plt.plot(xInProgress, yInProgress, 'g.-')

            # Plot the lines that have finished, and their statistics
            if index is not None:
                if index[0] == 0:
                    return
                else:
                    allPts = measMat[:index[0], :, 0]
            means = np.mean(allPts, axis=0)
            stddevs = np.std(allPts, axis=0)

            # Plot dots
            plt.plot(xFull, allPts.T, 'k.')
            # Plot means
            plt.plot(xFull, means, 'r', lw=2)
            # Plot error bars
            for upDown in [-1, 1]:
                y = means + upDown * stddevs
                plt.plot(xFull, y, 'b')

            # Make the axes pretty
            if axArr is None:
                plt.axis('square')
            # Expand the window to fit all points
            minMaxCmd = np.array([np.min(cmdMat), np.max(cmdMat)])
            minMaxCmd[0] = min(np.min(cmdMat), np.min(allPts))
            minMaxCmd[1] = max(np.max(cmdMat), np.max(allPts))
            plt.xlim(minMaxCmd)
            plt.ylim(minMaxCmd)
            plt.xlabel('Command value')
            plt.ylabel('Evaluated value')
            plt.plot(minMaxCmd, minMaxCmd, '--k')

    def score(self, bits=False, worstCase=False):
        ''' Takes full sweep data and returns the worst-case accuracy and precision

            Args:
                bits (bool): if true, returns values as bits of dynamic range
                worstCase (bool): if true, takes the performance at the worst weight, else averages via RMS
        '''
        cmdWeights = self.cmdGrid
        measWeights = self.data[..., np.array(self.swpInds)]

        # Statistics of every dimension at every grid point (so we're norming over trials) --
        # errRmsVsWeight = rms(measWeights - cmdWeights, axis=0) # Total error
        meanVsWeight = np.mean(measWeights, axis=0)
        errMeanVsWeight = meanVsWeight - cmdWeights
        errStddevVsWeight = rms(measWeights - meanVsWeight, axis=0)

        # Statistics normed over channels at every grid point
        # netErrRmsVsWeight = rms(errRmsVsWeight, axis=-1)
        netErrMeanVsWeight = rms(errMeanVsWeight, axis=-1)
        netErrStddevVsWeight = rms(errStddevVsWeight, axis=-1)

        # Take the worst case grid point
        consolidateErrorVsWeight = lambda x: np.max(np.abs(x)) if worstCase else rms(x, axis=None)
        accuracy = consolidateErrorVsWeight(netErrMeanVsWeight)  # This gives accuracy
        precision = consolidateErrorVsWeight(netErrStddevVsWeight)  # Precision

        if not bits:
            return accuracy, precision
        else:
            domainSpan = np.abs(np.max(cmdWeights) - np.min(cmdWeights))
            accuracyBits = np.log2(domainSpan / accuracy)
            precisionBits = np.log2(domainSpan / precision)
            return accuracyBits, precisionBits


interAx = None
hCurves = None
hArrow = None
hEllipse = None


def plotCmdCtrl(sweepData, index=None, ax=None, interactive=False):
    ''' sweepData should have ALL the command weights specified

        Args:
            sweepData (tuple): cmdWeights, measWeights, monitWeights (optional)
                measWeights has shape (nTrials, len(swp1), len(sp2) or 1, len(sweepingChannels))
            index (tuple): tells which parts of measured weights are valid. If None, assumes sweepData is complete
            interactive (bool): show plot immediately after call, even with incomplete data (index must be specified)

        Todo:
            Fix the global hack for persistent plots -- actually, this is fine
    '''
    global interAx  # pylint: disable=global-statement
    global hArrow  # pylint: disable=global-statement
    global hEllipse  # pylint: disable=global-statement

    cmdWeights, measWeights, monitWeights = sweepData

    gridShape = cmdWeights.shape[:-1]
    is2D = (cmdWeights.shape[-1] == 2)
    if index is None:
        # Just do a bunch of incrementals over the last trial without refresh
        interAx = ax
        if is2D:
            for gridIndex in np.ndindex(gridShape):
                fullIndex = (measWeights.shape[0] - 1, *gridIndex)
                plotCmdCtrl(sweepData, index=fullIndex, interactive=False)
        else:
            plotCmdCtrl(sweepData, index=(measWeights.shape[0], 0, 0), interactive=False)
    else:
        # This is done only on the first point of initialization
        if interAx is None or all(i == 0 for i in index):
            # Initialize plotting objects
            if ax is None:
                fig, ax = plt.subplots(figsize=(5, 5))  # pylint: disable=unused-variable
            interAx = ax
            plt.cla()
            if is2D:
                hArrow = np.empty(gridShape, dtype=object)
                hEllipse = np.empty(gridShape, dtype=object)

            # Lay down grid
            if is2D:
                xSweep = cmdWeights[:, 0, 0]
                xRange = (np.min(xSweep), np.max(xSweep))
                ySweep = cmdWeights[0, :, 1]
                yRange = (np.min(ySweep), np.max(ySweep))
                for sPt in xSweep:
                    interAx.plot(2 * [sPt], yRange, 'k-')
                for sPt in ySweep:
                    interAx.plot(xRange, 2 * [sPt], 'k-')
                # plt.xlim(xRange + np.array([-1, 1]) * np.diff(xRange)[0] * .1)
                # plt.ylim(yRange + np.array([-1, 1]) * np.diff(yRange)[0] * .1)
                # interAx.set(aspect='equal')
            else:
                xSweep = cmdWeights[:, 0]
                xRange = (np.min(xSweep), np.max(xSweep))
                interAx.plot(xRange, 2 * [0], 'k-')
                plt.xlim(xRange)
                plt.ylim(xRange - np.mean(xRange))
                # interAx.set(aspect='equal')

        # This is done for every point
        if not is2D:
            if index[0] == 0:
                return
            plt.cla()
            x = cmdWeights[:, 0]

            # All points over trials and the sweep parameter
            allPts = measWeights[:index[0], :, 0]
            allErrors = allPts - x
            meanErrors = np.mean(allErrors, axis=0)
            stddevs = np.std(allPts, axis=0)

            # Plot dots
            for iv, v in np.ndenumerate(allErrors):
                interAx.plot(x[iv[1]], v, '.k')

            # Plot means
            interAx.plot(x, meanErrors, 'r', lw=2)

            # Plot error bars
            for upDown in [-1, 1]:
                y = meanErrors + upDown * stddevs
                interAx.plot(x, y, 'b')

            # Monitor plotting if it's there:
            if monitWeights is not None:
                allPts = monitWeights[:index[0], :, 0]
                for iv, v in np.ndenumerate(allPts):
                    interAx.plot(x[iv[1]], v, '.m')
                monitMean = np.mean(allPts, axis=0)
                interAx.plot(x, monitMean, 'm', lw=2)
                stddevs = np.std(allPts, axis=0)
                y = monitMean[:, None] + np.array([[-1, 1]]) * stddevs[:, None]
                interAx.plot(x, y, 'g')
        else:  # 2D
            gridIndex = index[1:]
            valsAtThisGridPt = measWeights[(slice(index[0] + 1), *index[1:])]
            # plot newest raw point itself (and others at this grid point)
            for pt in valsAtThisGridPt:
                interAx.plot(*pt, '.k')

            # plot mean error line
            mean = np.mean(valsAtThisGridPt, axis=0)
            target = cmdWeights[gridIndex]
            arro = interAx.plot(*zip(target, mean), 'r', lw=2)  # pylint: disable=zip-builtin-not-iterating

            # plot variance ellipse
            if index[0] > 0:
                cov = np.cov(valsAtThisGridPt, rowvar=False)
                elli = plotCovEllipse(cov, mean, volume=0.5, ax=interAx, ec='b', fc='none')
            else:
                elli = None

            if interactive:
                # Replace previous graphics objects from this grid point
                if hArrow[gridIndex] is not None:
                    hArrow[gridIndex][0].remove()
                hArrow[gridIndex] = arro
                if hEllipse[gridIndex] is not None:
                    hEllipse[gridIndex].remove()
                hEllipse[gridIndex] = elli

        # if interactive:
        #     display.clear_output(wait=True)
        #     display.display(interAx.figure)


# Information on types of plots
# (set of possible dimensions, type of sweep in {'nd', 'cmd'})
pTypes = {}
pTypes['curves'] = ({1, 2}, {NdSweeper.__name__, CommandControlSweeper.__name__})
pTypes['surf'] = ({2}, {NdSweeper.__name__})
pTypes['cmdErr'] = ({1, 2}, {CommandControlSweeper.__name__})


def availablePlots(dims=None, swpType=None):
    ''' Filter by dims and swpType

        If the argument is none, do not filter by that
    '''
    avail = []
    for k, v in pTypes.items():
        if dims is None or dims in v[0]:
            if swpType is None \
                    or type(swpType) is type and swpType.__name__ in v[1] \
                    or type(swpType) is str and swpType in v[1]:
                avail.append(k)
    return avail


def assertValidPlotType(plType, dims=None, swpClass=None):
    if plType not in availablePlots(dims, swpClass):
        errStr = ['Invalid plot type.']
        errStr.append(f'This sweep is a {dims}-dimensional {swpClass.__name__}.')
        if plType not in availablePlots():
            errStr.append(f'{plType} is not a valid plot type at all.')
        else:
            errStr.append(f'{plType} is not a valid plot type for this kind of sweep.')
        errStr.append('Available plots are: {}'.format(', '.join(availablePlots(dims, swpClass))))
        logger.error('\n'.join(errStr))
        raise KeyError(plType)
