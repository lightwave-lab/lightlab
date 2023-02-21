import matplotlib.pyplot as plt
import matplotlib.figure as fig
import numpy as np
plt.ion()


class DynamicLine(object):
    ''' A line that can refresh when called
    '''

    def __init__(self, formatStr='b-', existing=None, geometry=[(0, 0), (4, 4)]):  # pylint: disable=dangerous-default-value
        '''
            Args:
                formatStr (str): plotting line format
                existing (Figure/DynamicLine): reference to an existing plot to which this DynamicLine instance will be added
                geometry (list[Tuple,Tuple]): a 2-element list of 2-tuples of bottom-left (pixels) and width-height (inches)
        '''
        # Set up plot
        if existing is None:
            self.figure = plt.figure(figsize=geometry[1])
            self.ax = self.figure.add_subplot(111)
        else:
            if type(existing) is fig.Figure:
                self.figure = existing
            elif type(existing) is DynamicLine:
                self.figure = existing.figure
            self.ax = self.figure.axes[0]
            # Geometry is ignored here
        self.lines, = self.ax.plot([], [], formatStr)
        plt.get_current_fig_manager().window.wm_geometry(
            '+' + str(geometry[0][0]) + '+' + str(geometry[0][1]))
        # Autoscale on unknown axis and known lims on the other
        self.ax.set_autoscaley_on(True)
        # Other stuff
        # self.ax.grid()
        self.figure.canvas.manager.window.attributes('-topmost', 1)

    def refresh(self, xdata, ydata):
        ''' Refresh the data displayed in the plot

            Args:
                xdata (array): X data
                ydata (array): Y data
        '''
        if not plt.fignum_exists(self.figure.number):
            raise Exception('The figure of this DynamicLine object has been closed')
        # Update data (with the new _and_ the old points)
        self.lines.set_xdata(xdata)
        self.lines.set_ydata(ydata)
        # Need both of these in order to rescale
        self.ax.relim()
        self.ax.autoscale_view()
        # We need to draw *and* flush
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def close(self):
        ''' Close the figure window.

            Further calls to :meth:`refresh` will cause an error
        '''
        plt.close(self.figure)


def plotCovEllipse(cov, pos, volume=.5, ax=None, **kwargs):
    '''
    Plots an ellipse enclosing *volume* based on the specified covariance
    matrix (*cov*) and location (*pos*). Additional keyword arguments are passed on to the
    ellipse patch artist.

    Args:
        cov : The 2x2 covariance matrix to base the ellipse on
        pos : The location of the center of the ellipse. Expects a 2-element
            sequence of [x0, y0].
        volume : The volume inside the ellipse; defaults to 0.5
        ax : The axis that the ellipse will be plotted on. Defaults to the
            current axis.
        kwargs : passed to Ellipse plotter
    '''

    from scipy.stats import chi2
    from matplotlib.patches import Ellipse

    if ax is None:
        ax = plt.gca()

    # Eigenvector decomposition, sorted by decreasing eigenvalue
    eigVals, eigVecs = np.linalg.eigh(cov)
    order = eigVals.argsort()[::-1]
    eigVals = eigVals[order]
    eigVecs = eigVecs[:, order]

    theta = np.degrees(np.arctan2(*eigVecs[:, 0][::-1]))

    # Width and height are "full" widths, not radius
    width, height = 2 * np.sqrt(chi2.ppf(volume, 2)) * np.sqrt(eigVals)
    ellip = Ellipse(xy=pos, width=width, height=height, angle=theta, **kwargs)

    return ax.add_artist(ellip)
