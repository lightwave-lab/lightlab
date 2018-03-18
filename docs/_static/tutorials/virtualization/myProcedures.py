import numpy as np
import matplotlib.pyplot as plt
from lightlab.util.sweep import NdSweeper


def extractThreshold(source_meter_instr, vMax=3):
    ''' Get the data, analyze the data to find the threshold, plot
    '''
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
