''' Timing is pretty important. These functions monitor behavior in various ways with timing considered.
    Included is strobeTest which sweeps the delay between actuate and sense, and monitorVariable for drift
'''

import matplotlib.pyplot as plt
from cycler import cycler
import numpy as np
import time
from IPython import display

from .data import FunctionBundle


def strobeTest(fActuate, fSense, fReset=None, nPts=10, maxDelay=1, visualize=True):  # pylint: disable=W0613
    ''' Looks at a sense variable at different delays after calling an actuate function.
        Good for determining the time needed to wait for settling.
        Calls each function once per delay point to construct a picture like the strobe experiment, or a sampling scope

        Args:
            fActuate (function): no arguments, no return. Called first.
            fSense (function): no arguments, returns a scalar or np.array. Called after a given delay
            fReset (function): no arguments, no return. Called after the trial unless None. Usually of the same form as fActuate

        Returns:
            (FunctionBundle): fSense values vs. delay
    '''
    fi, ax = plt.subplots(figsize=(12, 7))
    delays = np.linspace(0, maxDelay, nPts)

    # Figure out if sense is scalar or array; wrap accordingly
    testV = fSense()
    if np.isscalar(testV):
        w = 1
    else:
        w = len(testV)
    fWrapped = lambda: np.reshape(np.array(fSense()), (1, w))

    t = np.zeros((nPts, 1))
    v = np.zeros((nPts, w))
    for it, d in enumerate(delays):
        t[it] = d
        if fReset is not None:
            fReset()
            time.sleep(maxDelay)
        fActuate()
        time.sleep(d)
        v[it, :] = fWrapped()
        display.clear_output(wait=True)
        ax.cla()
        ax.plot(t[:it + 1], v[:it + 1])
        display.display(fi)
        bund = FunctionBundle()
        bund.absc = t
        bund.ordiMat = v
    return bund


def sweptStrobe(varSwp, resetArg, nPts=10, maxDelay=1):
    ''' Takes in a NdSweeper and looks at the effect of delaying between actuation from measurement. Does the gathering.

        Starts by taking start and end baselines, for ease of visualization.

        Args:
            varSwp (NdSweeper): the original, with 1-d actuation, any measurements, any parsers
            resetArg (scalar): argument passed to varSwp's actuate procedure to reset and equilibrate
            nPts (int): number of strobe points
            maxDelay (float): in seconds, delay of strobe. Also the time to soak on reset

        Returns:
            (NdSweeper): the strobe sweep, with accessible data. It can be regathered if needed.

        Todo:
            It would be nice to provide timeconstant analysis, perhaps by looking at 50%, or by fitting an exponential
    '''
    if len(varSwp.actuate) > 1:
        raise NotImplementedError(
            'Since sweeper does not do well with >2 dimensions, you can only strobe a 1-D sweep')
    aKey, actu = list(varSwp.actuate.items())[0]
    varFun = actu.function
    varDom = actu.domain
    measParseKeys = list(varSwp.measure.keys()) + list(varSwp.parse.keys())

    # soakFun wraps the existing actuator with a long delay afterwards to ensure equilibration
    def soakFun(actuArg):
        varFun(actuArg)
        time.sleep(maxDelay)

    def resetSoakAndActu(actuArg):
        soakFun(resetArg)
        varFun(actuArg)

    strobeSwp = varSwp.copy()
    strobeSwp.reinitActuation()

    # Another actuate/measure combo. Instead of sweeping actuation, it just resets, then soaks. There is only one sweep point.
    # Store the results in data for later normalization
    startValSwp = varSwp.copy()
    startValSwp.setMonitorOptions(livePlot=False)
    startValSwp.reinitActuation()
    startValSwp.addActuation(aKey, soakFun, [resetArg])
    startValSwp.gather()
    startValData = {}
    for mpKey in measParseKeys:
        startValData[mpKey + '-start'] = startValSwp.data[mpKey][0]
    for sdKey, sdVal in startValData.items():
        strobeSwp.addStaticData(sdKey, sdVal)

    strobeSwp.addActuation(aKey, resetSoakAndActu, varDom, doOnEveryPoint=True)

    # Begin by doing a standard 1-d sweep, but with significant delay to get equilibrium end values of every measurement/parser
    # Store the results in data for later normalization
    endValSwp = varSwp.copy()
    endValSwp.setMonitorOptions(livePlot=False)
    endValSwp.reinitActuation()
    endValSwp.addActuation(aKey, soakFun, varDom)
    endValSwp.gather()
    endValData = {}
    for mpKey in measParseKeys:
        endValData[mpKey + '-end'] = endValSwp.data[mpKey]
    for edKey, edVal in endValData.items():
        strobeSwp.addStaticData(edKey, edVal)

    # Adding actuation following reset: the default actuation, then a delay
    # associated with the strobe
    strobeSwp.addActuation('strobeDelay', time.sleep, np.linspace(0, maxDelay, nPts))

    # Provides normalized parsers for plotting
    strobeSwp.plotOptions['xKey'] = ('strobeDelay')
    strobeSwp.plotOptions['yKey'] = ()
    for mpKey in measParseKeys:
        strobeSwp.addParser(mpKey + '-normalized',
                            lambda dat: (dat[mpKey] - dat[mpKey + '-start']) / (dat[mpKey + '-end'] - dat[mpKey + '-start']))
        strobeSwp.plotOptions['yKey'] += (mpKey + '-normalized', )

    return strobeSwp


def monitorVariable(fValue, sleepSec=0, nReps=100, plotEvery=1):
    ''' Monitors some process over time. Good for observing drift.

        Args:
            valueFun (function): called at each timestep with no arguments. Must return a scalar or a 1-D np.array
            sleepSec (scalar): time in seconds to sleep between calls
    '''
    curves = None

    testV = fValue()
    if np.isscalar(testV):
        w = 1
    else:
        w = len(testV)
    fWrapped = lambda: np.reshape(np.array(fValue()), (1, w))
    t0 = time.time()
    timeFun = lambda: time.time() - t0

    _, ax = plt.subplots(figsize=(12, 7))
    cycleDefault = plt.rcParams['axes.prop_cycle'].by_key()['color']
    cycleContrained = cycleDefault[:w]
    ax.set_prop_cycle(cycler('color', cycleContrained))

    t = np.zeros((nReps, 1))
    v = np.zeros((nReps, w))
    for it in range(nReps):
        t[it] = timeFun()
        v[it, :] = fWrapped()
        if (it + 1) % plotEvery == 0:
            if curves is not None:
                try:
                    [c.remove() for c in curves]  # pylint: disable=not-an-iterable
                except ValueError:
                    # it was probably an old one
                    pass
            curves = ax.plot(t[:it + 1], v[:it + 1])
            display.clear_output(wait=True)
            display.display(plt.gcf())
        time.sleep(sleepSec)
