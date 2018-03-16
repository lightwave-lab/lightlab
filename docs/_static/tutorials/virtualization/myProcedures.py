import numpy as np
import matplotlib.pyplot as plt
from lightlab.util.sweep import NdSweeper, peakSearch


def extractThreshold_1(source_meter_instr, vMax=3):
    # get the data
    swp = NdSweeper()
    swp.addActuation('Voltage', source_meter_instr.setVoltage, np.linspace(0, vMax, 20))
    swp.addMeasurement('Current', source_meter_instr.measCurrent)
    swp.setMonitorOptions(livePlot=True, stdoutPrint=False)
    swp.gather()                # 5 lines to specify a killer sweep
    maxI = np.max(swp.data['Current'])

    # analyze the data
    curvature = np.diff(np.diff(swp.data['Current']))
    threshInd = np.argmax(curvature) + 1
    threshVolt = swp.data['Voltage'][threshInd]

    # just a plot
    swp.plot()
    plt.gca().annotate('foundThresh', xy=(threshVolt, 0),
                       xytext=(threshVolt - .2, maxI/2), ha='right',
                       arrowprops=dict(shrink=0.05))
    return threshVolt


def extractThreshold_2(source_meter_instr):
    def dither(centerVolt):
        dvArr = np.linspace(-1, 1, 3) * .2
        diArr = np.zeros(len(dvArr))
        for iDv, dv in enumerate(dvArr):
            source_meter_instr.setVoltage(centerVolt + dv)
            diArr[iDv] = source_meter_instr.measCurrent()
        d2idv2 = diArr[0] - 2 * diArr[1] + diArr[2]
        return d2idv2

    foundThresh, _ = peakSearch(dither, [-1, 3], livePlot=True, nSwarm=5)
    return foundThresh
