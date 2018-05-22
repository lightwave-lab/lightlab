
from lightlab.laboratory.state import lab
# import lightlab.laboratory.state
# lab = lightlab.laboratory.state.LabState.loadState(filename='/home/jupyter/labstate-newdrivers.json')

from lightlab import log_to_screen, WARNING
log_to_screen(WARNING)

def start(instrumentName):
    instr = lab.instruments[instrumentName]
    if instr.isLive():
        print('It is alive')
    else:
        print('Not responding.')
    print(instr.driver.instrID())
    print('Here is what to test:')
    print('\n'.join(instr.essentialMethods + instr.essentialProperties + instr.implementedOptionals))
    return instr

