''' Useful stuff having to do with data handling and processing.

    :py:class:`MeasuredFunction` is the workhorse.

    The :py:class:`Spectrum` class is nice for working with dbm and linear units, and also for interpolating at any value.

    :py:func:`findPeaks` and :py:func:`descend` hold the low-level algorithms.
    Usually, users would interact with it via ``MeasuredFunction``.
'''
from .basic import (verifyListOfType, argFlatten, mangle,  # noqa
                    rms, minmax)  # noqa

from .function_inversion import interpInverse, descend  # noqa

from .peaks import ResonanceFeature, PeakFinderError, findPeaks  # noqa

from .one_dim import MeasuredFunction, Spectrum, Waveform  # noqa

from .two_dim import (FunctionBundle, FunctionalBasis,  # noqa
                      MeasuredSurface, Spectrogram, MeasuredErrorField)  # noqa
