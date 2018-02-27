Measured functions
==============================================

.. contents:: In this section
    :local:

:py:class:`~lightlab.util.data.MeasuredFunction` is the datatype workhorse. Most data can be formulated as one variable vs. another, the ordinate and abscissa. What we measure is discrete, but we can assume it represents something continuous. That means interpolation and math are supported with appropriate processing of abscissa basis.

Basic manipulation is supported, such as splicing, deleting segments, adding points, etc. Math is also supported with a scalar and a measured function and two measured functions (with appropriate abscissa basis handling.)

Child classes include ``Spectrum``, meant for cases where the abscissa is frequency or wavelength and the ordinate is power or transmission. It has extra methods for conversion from linear to decibel power units. Also ``Waveform`` is meant for cases where abscissa is time.

Peak finding
------------
The data module is particularly good with peaks. A very basic classless peak finder comes with :py:func:`~lightlab.util.data.findPeaks`. The arguments are arrays and indeces. It is more useful to do peakfinding in an object-oriented way with :py:meth:`~lightlab.util.data.MeasuredFunction.findResonanceFeatures`. The :py:class:`~lightlab.util.data.ResonanceFeature` class stores information on the position, width, and height of peaks, in addition to more powerful aspects like refining position based on convolution with a known peak shape.

Much of this functionality is handled within the :py:class:`~lightlab.equipment.measprocessing.SpectrumMeasurementAssistant`, good for when you are looking at real spectra of a single device over and over again. Makes assumptions such as background not changing and filter shape not changing. The notebook doesn't really show the full potential of SpectrumMeasurementAssistant.

Descent-based function inversion
--------------------------------
Inverting a measured function is desirable for evoking a particular response that was measured. For example, finding the proper wavelength shift needed to set a given transmission value, based on a known MeasuredFunction of transmission vs. wavelength. Descent functions use linear interpolation. Descent only works on monotonically increasing (decreasing) sections. When the entire object is monotonic, use the :py:meth:`MeasuredFunction.invert <lightlab.util.data.MeasuredFunction.invert>` method. When the function is peak-like, it is possible to specify a direction to start the descent until either the target value is reached, or the function changes slope.

.. toctree::
    :maxdepth: 2
    :caption: Demo

    /ipynbs/TestPeakAssistant.ipynb

.. seealso::

    Here, we were talking about performing calculations with objects in code that have presumably been measured from some real-life process. There are equivalents for peak finding and inversion while interacting with a real measurement-actuation system. These are found in util.characterize i think.

FunctionBundle and FunctionalBasis
----------------------------------
Often there are two abscissas. The "third dimension" could be a continuous variable (as in `MeasuredSurface`) or a discrete variable (as in `FunctionBundle`). They each have different implications and operations and subclasses. `Spectrogram` inherits `MeasuredSurface` with continuous time as the second abscissa. `FunctionalBasis` is basically a bundle with increased attention paid to linear algebra and function order for the sake of decomposing, synthesizing, and projecting weighted additions of other functions.

.. autofunction:: lightlab.util.data.FunctionBundle
    :noindex:

.. toctree::
    :maxdepth: 2
    :caption: Demo

    /ipynbs/TestFunctionalBasis.ipynb


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
