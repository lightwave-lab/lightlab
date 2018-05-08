''' Useful stuff having to do with data handling and processing.

    :class:`one_dim.MeasuredFunction` is the workhorse.

    The :class:`~one_dim.Spectrum` class is nice for working with dbm and linear units

    :func:`peaks.findPeaks` and :func:`function_inversion.descend` hold the low-level algorithms.
    Usually, users would interact with it via :class:`~one_dim.MeasuredFunction`.
'''
from .basic import (verifyListOfType, argFlatten, mangle,  # noqa
                    rms, minmax)  # noqa

from .function_inversion import interpInverse, descend  # noqa

from .peaks import ResonanceFeature, PeakFinderError, findPeaks  # noqa

from .one_dim import MeasuredFunction, Spectrum, Waveform  # noqa

from .two_dim import (FunctionBundle, FunctionalBasis,  # noqa
                      MeasuredSurface, Spectrogram, MeasuredErrorField)  # noqa
