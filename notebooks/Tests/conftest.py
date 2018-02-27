'''
    Combining ipy notebooks with pytest
    Configured for the nbval package (see its documentation)

    Outputs are compared at the string and byte level. That (might) include PNG images.

    Hints:

        Floating point values are represented slightly differently on different machines.
        If the value in question is an ipython output, use the magic command
            %precision 8
        If the value is coming from a print call in __main__, use string formatting
            BAD:  print('Long float', np.pi)
            GOOD: print('Long float {:.6f}'.format(np.pi))
        If the value is being printed from your code, you have to go change the code

        Many tests and even code modules contain randomness. That is ok. It all comes from numpy.
        After importing numpy, reset the seed using
            np.random.seed(0)
        The following behavior depends on having the *exact* same execution order

        If you pull while a kernel is running, the outputs will not update.
        Make sure to close the window and shutdown the kernel of the file of interest
    '''

def pytest_collectstart(collector):
    collector.skip_compare += 'text/html', 'application/javascript', 'stderr',
