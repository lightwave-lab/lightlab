Generating signals
==================

.. contents:: In this section
    :local:

.. todo:: This section could probably be expanded beyond just PPG

With a pulse pattern generator (PPG)
------------------------------------
The technique of using Markov patterns to generate partial correlations was developed in :cite:`Tait:15`.

Experimental setups
*******************
Supposing you want to generate N-dimensional analog signals, but you only have one pulse pattern generator (PPG) that only outputs binary signals. One way to make multiple signals from one is by splitting and delaying. Then, how do you control the relationships between these signals? By using Markov patterns that have programmable autocorrelations between bits, the time delay turns this into correlations between the N-D signals. The techniques here allow one to create signals that are partially correlated. When that correlation is zero, signals are approximately orthogonal. When correlation is one, they are identical, even though they are delayed.

.. figure:: markovGenerator.pdf
    :alt: Basic experimental setup
    :align: center

    Generic experimental setup. 1) Binary signal from PPG. 2) Copies of signal. 3) Skewed versions. 4) Analog sum or weighted sum.

This procedure was developed particularly for optical fiber setups based on addition involving multiple wavelength channels hitting a single photodetector. Signals carried by different wavelengths are multiplexed, weighted by a photonic weight bank, and detected as a sum. While generating signals, all weights should be set to +1 (maximum transmission).

In one approach, each channel gets a modulator, and delays can occur either in the electrical domain or the optical domain: between the modulators and multiplexer.

.. figure:: 2chOpticalMarkov.pdf
    :alt: Two channel
    :align: center

    Two channel fiber signal generator.

The first approach is hardware intensive. Each channel needs a modulator and must be delayed by a specific amount using tunable delay lines. Furthermore, each channel needs a polarization controller before and after modulation such that they all end up in a common polarization state. It is generally OK for two channels.

In another approach, multiple wavelengths can be modulated by the single PPG signal in a single modulator. Multiplexing can occur before modulation. Here, delays must occur after modulation in the optical domain. Wavelengths could be demultiplexed, delayed by fiber lengths, and remultiplexed; however, this requires a lot of hardware (demux, fibers, tunable delays, polarization controllers, mux). Instead, we can use a spectral skewing device that delays different wavelengths by different, evenly spaced amounts. A fiber with evenly spaced Bragg gratings can perform this function without demux, thereby locking polarization state and a mutual delay amount that is set by the fixed spacing of the gratings along the fiber.

.. figure:: fbgSkewer.pdf
    :alt: Basic experimental setup
    :align: center

    N-channel WDM generator using fiber Bragg grating (FBG) spectral skewers.


Code implementation
*******************
A big problem in this sort of setup is that the exact delay might be unknown. The code provides a special method for automatically finding that delay by changing around the clock frequency and test patterns. In order to evaluate if it worked, which is optional, you have to have a way to turn signals on and off (i.e. shutter them). Currently this is done with DFB channels via :py:class:`lightlab.equipment.conductor.WeightTuningManager`. Once the delay is found precisely, you can get binary patterns corresponding to desired correlations with a simple query.

.. autoclass:: lightlab.equipment.conductor.MarkovHandler
    :noindex:

Example usage

.. code-block:: python

    import lightlab.equipment.conductor.MarkovHandler
    markHand = MarkovHandler(2e9, 2, scopeChan=7)
    markHand.autoDelay(maxPossibleInterDelay=20e-9)
    markHand.evaluate(shutterChans=[8, 9], correlationVals=np.linspace(-.8, .8, 11))

    orthogonal = markHand.makePattern(0)
    identical = markHand.makePattern(1)
    partiallyCorrelated = markHand.makePattern(-0.5)

.. bibliography:: /lightwave-bibliography.bib

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
