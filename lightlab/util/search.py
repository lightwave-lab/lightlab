''' Searching with actuate-measure functions,
    usually around peaks and monotonic functions
'''
import matplotlib.pyplot as plt
import numpy as np
from IPython import display

from lightlab.util.data import MeasuredFunction
from lightlab.util.io import RangeError
from lightlab import logger


class SearchRangeError(RangeError):
    ''' The first argument is direction, the second is a best guess
    '''
    pass


def plotAfterPointMeasurement(trackerMF, yTarget=None):
    ''' This mutates trackerMF

        Args:
            trackerMF (MeasuredFunction): function that will be plotted
            yTarget (float): plotted as dashed line if not None
    '''
    display.clear_output(wait=True)
    plt.cla()
    trackerMF.simplePlot('.-')
    if yTarget is not None:
        targLineSpan = plt.xlim()
        plt.plot(targLineSpan, 2 * [yTarget], '--k', lw=.5)
    display.display(plt.gcf())


def peakSearch(evalPointFun, startBounds, nSwarm=3, xTol=0., yTol=0., livePlot=False):
    ''' Returns the optimal input that gives you the peak, and the peak value

        You must set either xTol or yTol.
        Be careful with yTol! It is best used with a big swarm.
        It does not guarantee that you are that close to peak, just that the swarm is that flat

        This algorithm is a modified swarm that is robust to outliers, sometimes.
            Each iteration, it takes <nSwarm> measurements and looks at the best (highest).
            The update is calculated by shrinking the swarm around the index of the best value.
            It does not compare between iterations: that makes it robust to one-time outliers.
            It attributes weight only by order of y values in an iteration, not the value between iterations or the magnitude of differences between y's within an iteration

        Not designed to differentiate global vs. local maxima

        Args:
            evalPointFun (function): y=f(x) one argument, one return. The function that we want to find the peak of
            startBounds (list, ndarray): minimum and maximum x values that bracket the peak of interest
            nSwarm (int): number of evaluations per iteration. Use more if it's a narrow peak in a big bounding area
            xTol (float): if the swarm x's fall within this range, search returns successfully
            yTol (float): if the swarm y's fall within this range, search returns successfully
            livePlot (bool): for notebook plotting

        Returns:
            (float, float): best (x,y) point of the peak
    '''
    # Argument checking
    if xTol is None and yTol is None:
        raise ValueError('Must specify either xTol or yTol, ' +
                         'or peak search will never converge.')

    nSwarm += (nSwarm + 1) % 2
    tracker = MeasuredFunction([], [])

    def shrinkAround(arr, bestInd, shrinkage=.6):
        fulcrumVal = 2 * arr[bestInd] - np.mean(arr)
        return fulcrumVal + (arr - fulcrumVal) * shrinkage

    offsToMeasure = np.linspace(*startBounds, nSwarm)
    for iIter in range(20):  # pylint: disable=unused-variable
        # Take measurements of the points
        measuredVals = np.zeros(nSwarm)
        for iPt, offs in enumerate(offsToMeasure):
            meas = evalPointFun(offs)
            measuredVals[iPt] = meas
            tracker.addPoint((offs, meas))
            if livePlot:
                plotAfterPointMeasurement(tracker)

        # Move the lowest point closer
        bestInd = np.argmax(measuredVals)
        # print('iter =', iIter, '; offArr =', offsToMeasure, '; best =', np.max(measuredVals))
        worstInd = np.argmin(measuredVals)
        if measuredVals[bestInd] - measuredVals[worstInd] < yTol \
                or offsToMeasure[-1] - offsToMeasure[0] < xTol:
            # logger.debug('Converged on peak')
            break
        if worstInd == float(nSwarm - 1) / 2:
            logger.debug('Detected positive curvature')
            # break
        offsToMeasure = shrinkAround(offsToMeasure, bestInd)
    return (offsToMeasure[bestInd], measuredVals[bestInd])


def doesMFbracket(targetY, twoPointMF):
    yRange = twoPointMF.getRange()
    if targetY < yRange[0]:
        outOfRangeDirection = 'low'
    elif targetY > yRange[1]:
        outOfRangeDirection = 'high'
    else:
        outOfRangeDirection = 'in-range'
    return outOfRangeDirection


def bracketSearch(evalPointFun, targetY, startBounds, xTol, hardConstrain=False, livePlot=False):
    '''
        Searches outwards until it finds two X values
        whose Y values are above and below the targetY.

        Stop conditions
            * brackets it: returns new bracketing x values
            * step decreases until below xTol: raises RangeError
            * 30 iterations: raises RangeError

        Args:
            evalPointFun (function): y=f(x) one argument, one return. The function that we want to find the target Y value of
            startBounds (list, ndarray): x values that usually do not bracket the value of interest
            xTol (float): if *domain* shifts become less than this, raises RangeError
            hardConstrain (bool, list): If list, will stay within those
            livePlot (bool): for notebook plotting

        Returns:
            ([float, float]): the bracketing range
    '''
    startBounds = sorted(startBounds)
    if hardConstrain is True:
        constrainBounds = startBounds
    elif hardConstrain is False:
        constrainBounds = [-np.infty, np.infty]
    else:
        constrainBounds = hardConstrain

    tracker = MeasuredFunction([], [])

    def measureError(xVal):
        yVal = evalPointFun(xVal)
        tracker.addPoint((xVal, yVal))
        err = yVal - targetY
        if livePlot:
            plotAfterPointMeasurement(tracker, targetY)
        return err

    # First check out what happens at the edges
    for x in startBounds:
        measureError(x)
    isIncreasing = tracker.ordi[1] > tracker.ordi[0]

    # Did it start bracketed?
    outOfRangeDirection = doesMFbracket(targetY, tracker)
    if outOfRangeDirection == 'in-range':
        return startBounds

    # Which way to go? We know that tracker has 2 points in it right now
    if ((isIncreasing and outOfRangeDirection == 'high') or
            (not isIncreasing and outOfRangeDirection == 'low')):
        searchDirection = 1
    else:
        searchDirection = 0
    lastX = tracker.absc[-searchDirection - 1]
    twoAgoX = lastX
    lastErr = tracker.ordi[-searchDirection - 1] - targetY
    twoAgoErr = lastErr
    absStep = np.diff(startBounds)[0] / 2  # this is tricky
    signedStep = absStep * (1 if (searchDirection == 1) else -1)
    newX = lastX + signedStep

    # Feel out in that direction
    constraintViolation = None
    for iIter in range(100):  # pylint: disable=unused-variable
        # Case -2: went outside of constraints, fail
        if newX < constrainBounds[0]:
            constraintViolation = 'low' if isIncreasing else 'high'
        elif newX > constrainBounds[1]:
            constraintViolation = 'high' if isIncreasing else 'low'
        if constraintViolation is not None:
            raise SearchRangeError('Violated domain constraints',
                                   constraintViolation, lastX)
        # Case -1: step is too small, fail
        if abs(signedStep) < xTol:
            raise SearchRangeError('Target value out of range! ' +
                                   'This is the best guess.',
                                   outOfRangeDirection, newX)

        # ### Do the actual measurement ####
        newErr = measureError(newX)
        # Case 0: definitely bracketed it
        if np.sign(lastErr * newErr) < 0:
            return [twoAgoX, newX]

        # Case 1: climbing up a peak
        # Case 2: skipped over a peak, didn't bracket it,
        #   but it looks like still going up
        elif abs(newErr) < abs(lastErr):
            # Shift everything back into the past
            twoAgoX = lastX
            twoAgoErr = lastErr
            lastX = newX
            lastErr = newErr
        # Case 3: skipped over a peak and started going down
        else:
            # Drop back to the past and reduce the step
            lastX = twoAgoX
            lastErr = twoAgoErr
            signedStep /= 2
        newX = lastX + signedStep
    raise Exception('Bracket search did 100 iterations and still did not converge')


def binarySearch(evalPointFun, targetY, startBounds, hardConstrain=False, xTol=0, yTol=0, livePlot=False):
    '''
        Gives the x where ``evalPointFun(x) == targetY``, approximately.
        The final call to evalPointFun will be of this value,
        so no need to call it again, if your goal is to set to the target.

        xTol and yTol are OR-ed conditions.
        If one is satisfied, it will terminate successfully.
        You must specify at least one.

        Assumes that the function is monotonic in any direction
        It often works when there is a peak inside the ``startBounds``,
        although not always.

        Args:
            evalPointFun (function): y=f(x) one argument, one return. The function that we want to find the target Y value of
            startBounds (list, ndarray): minimum and maximum x values that bracket the peak of interest
            hardConstrain (bool, list): if not True, will do a bracketSearch. If list, will stay within those
            xTol (float): if *domain* shifts become less than this, terminates successfully
            yTol (float): if *range* shifts become less than this, terminates successfully
            livePlot (bool): for notebook plotting

        Returns:
            (float): the optimal X value
    '''
    # Argument checking
    if xTol is None and yTol is None:
        raise ValueError('Must specify either xTol or yTol, ' +
                         'or binary search will never converge.')

    startBounds = sorted(startBounds)
    tracker = MeasuredFunction([], [])

    def measureError(xVal):
        yVal = evalPointFun(xVal)
        tracker.addPoint((xVal, yVal))
        err = yVal - targetY
        if livePlot:
            plotAfterPointMeasurement(tracker, targetY)
        return err

    # First check out what happens at the edges
    for x in startBounds:
        measureError(x)
    isIncreasing = tracker.ordi[1] > tracker.ordi[0]

    outOfRangeDirection = doesMFbracket(targetY, tracker)
    if outOfRangeDirection != 'in-range':
        # Case 1: we won't tolerate it
        if hardConstrain is True:
            if outOfRangeDirection == 'high':
                bestGuess = tracker.absc[np.argmax(tracker.ordi)]
            else:
                bestGuess = tracker.absc[np.argmin(tracker.ordi)]
            raise SearchRangeError('binarySearch function value ' +
                                   'outside of hard constraints! ' +
                                   'Results invalid.',
                                   outOfRangeDirection, bestGuess)
        # Case 2: try to get it in range
        else:
            try:
                newStartBounds = bracketSearch(evalPointFun=evalPointFun,
                                               targetY=targetY,
                                               startBounds=startBounds,
                                               xTol=xTol,
                                               hardConstrain=hardConstrain,
                                               livePlot=livePlot)
            except SearchRangeError as err:
                logger.debug('Failed to bracket targetY=%s. Returning best guess', targetY)
                return err.args[2]
            try:
                return binarySearch(evalPointFun=evalPointFun,
                                    targetY=targetY,
                                    startBounds=newStartBounds,  # important change
                                    xTol=xTol, yTol=yTol,
                                    hardConstrain=True,  # important change
                                    livePlot=livePlot)
            except SearchRangeError as err:
                raise SearchRangeError('It was in range and then not, ' +
                                       'so probably noise.',
                                       err.args[1], err.args[2])

    # By now we are certain that the target is bounded by the start points
    thisX = np.mean(startBounds)
    absStep = np.diff(startBounds)[0] / 4
    for _ in range(30):
        newErr = measureError(thisX)
        # Case 1: converged within tolerance
        if abs(newErr) < yTol or absStep < xTol:

            return thisX

        # Case 2: guess new point and reduce step by factor of 2
        if isIncreasing:
            thisX -= np.sign(newErr) * absStep
        else:
            thisX += np.sign(newErr) * absStep
        absStep /= 2
    raise Exception('Binary search did 30 iterations and still did not converge')
