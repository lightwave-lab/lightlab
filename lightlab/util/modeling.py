''' Useful functions and Classes for modeling.
'''

from enum import Enum
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Constants
kOSASpacing = 0.0008 # 0.8pm
kOSAPwr  = 0.1 # mW
kOSAMin = 1e-9 # mW
kOSANoise = 5e-9


# Classes and Functions
class MrrOut(Enum):
    kThru = 0
    kDrop = 1

    @classmethod
    def fromNumber(cls, num):
        if num == 0:
            return cls.kThru
        elif num == 1:
            return cls.kDrop
        else:
            return None

class CurrentUnit(Enum):
    V  = 1
    mA = 2
    mW = 3

    @staticmethod
    def v2iCoef():
        return 4.0 # current (milliamps) = v2iCoef * voltage (volts)

    @staticmethod
    def convert(val, uFrom, uTo):
        return CurrentUnit.voltTo(CurrentUnit.toVolt(val, uFrom), uTo)

    @staticmethod
    def toVolt(val, uFrom):
        if uFrom.__class__ is not CurrentUnit:
            raise Exception("Did not provide proper Current Unit.")
    	# Convert from mW/kOhm
        if uFrom == CurrentUnit.mW:
            val = np.sqrt(val*1000) / CurrentUnit.v2iCoef()
        # Convert from mA
        elif uFrom == CurrentUnit.mA:
            val /= CurrentUnit.v2iCoef()
        # Else keep voltage the same
        return val


    @staticmethod
    def voltTo(val, uTo):
        if uTo.__class__ is not CurrentUnit:
            raise Exception("Did not provide proper Current Unit.")

        # Convert to mW/kOhm
        if uTo == CurrentUnit.mW:
            val = np.power(val*CurrentUnit.v2iCoef(), 2.0) / 1000
        # Convert to mA
        elif uTo == CurrentUnit.mA:
            val *= CurrentUnit.v2iCoef()
        # Else keep voltage the same
        return val

def voss(nrows, ncols=16):
    '''Generates pink noise using the Voss-McCartney algorithm.
    
    nrows: number of values to generate
    rcols: number of random sources to add
    
    returns: NumPy array
    '''
    array = np.empty((nrows, ncols))
    array.fill(np.nan)
    array[0, :] = np.random.random(ncols)
    array[:, 0] = np.random.random(nrows)
    
    # the total number of changes is nrows
    n = nrows
    cols = np.random.geometric(0.5, n)
    cols[cols >= ncols] = 0
    rows = np.random.randint(nrows, size=n)
    array[rows, cols] = np.random.random(n)

    df = pd.DataFrame(array)
    df.fillna(method='ffill', axis=0, inplace=True)
    total = df.sum(axis=1)

    vals = total.values

    # Zero Mean
    vals = np.subtract(vals, np.mean(vals))

    return vals

def lin2dbm(lin):
    ''' mW to dBm
    '''
    return 10 * np.log10(lin)

def dbm2lin(dbm):
    ''' dBm to mW
    '''
    return np.power(10, np.divide(dbm, 10))

def wlRange2nm(wlRange):
    ''' Linearly move wlRange to nm vector
    '''
    numSamps = int(np.round((wlRange[1] - wlRange[0]) / kOSASpacing))
    return np.linspace(wlRange[0], wlRange[1], numSamps)

def lorentz(wlRange, center, fwhm, atten=1.0):
    ''' Creates Lorentzian in linear regime.
    '''
    hwhm = np.divide(fwhm, 2.0)
    nm = wlRange2nm(wlRange)
    gamma = hwhm * hwhm
    lin = np.multiply(np.divide(gamma, np.power(np.subtract(nm, center), 2) + gamma), atten)
    return nm, lin

def addNoise(linmW):
    ''' Adds noise to linear mW spectrum.
    '''
    #noise = np.random.normal(0, kOSANoiseStd, len(linmW))
    noise = np.multiply(np.add(kOSANoise * np.ones(len(linmW)), 0.05 * linmW), voss(len(linmW)))
    return np.clip(np.add(noise, linmW), kOSAMin, kOSAPwr)
    #return linmW