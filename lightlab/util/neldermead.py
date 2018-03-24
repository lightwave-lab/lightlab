import matplotlib.pyplot as plt
import numpy as np
from IPython import display

from .data import MeasuredFunction

def NelderMead1D(evalPointFun, startBounds, nVertices=2, xTol=0., yTol=0., alpha=0.2, beta=1.25, gamma=0.5, theta=0.5, livePlot=False, quiet=False):
    ''' Perform similar functionality as peakSearch, but employ Nelder-Mead algorithm

        Args:
            evalPointFun (function): y=f(x) one argument, one return. The function that we want to find the peak of
            startBounds (list, ndarray): minimum and maximum x values that bracket the peak of interest
            nVertices (int): number of evaluations per simplex. Use more if it's a narrow peak in a big bounding area
            xTol (float): if the swarm x's fall within this range, search returns successfully
            yTol (float): if the swarm y's fall within this range, search returns successfully
            alpha/beta/gamma/theta: tunable parameters
            livePlot (bool): for notebook plotting

        Returns:
            (float, float): best (x,y) point of the peak
    '''

    tracker = MeasuredFunction([], [])
    offsToMeasure = np.linspace(*startBounds, nVertices)
    measuredVals = np.zeros(nVertices)
    for iIter in range(20):
        # Take measurements of the points
        for iPt, offs in enumerate(offsToMeasure):
            meas = evalPointFun(offs)
            measuredVals[iPt] = meas
            tracker.addPoint((offs, meas))
        if livePlot:
            display.clear_output(wait=True)
            plt.cla()
            tracker.simplePlot('.-')
            display.display(plt.gcf())
        # compute the centroid
        meanoffsToMeasure = np.mean(offsToMeasure)
        # find the highest & lowest point
        bestInd = np.argmax(measuredVals)
        worstInd = np.argmin(measuredVals)
        # termination
        if abs(measuredVals[bestInd] - measuredVals[worstInd]) < yTol \
            or abs(offsToMeasure[bestInd] - offsToMeasure[worstInd]) < xTol:
            if not quiet:
                print('Converged on peak')
            break
        # reflection
        ref = meanoffsToMeasure + (meanoffsToMeasure - offsToMeasure[worstInd]) * alpha
        measref = evalPointFun(ref)
        if measref > measuredVals[worstInd] and measref < measuredVals[bestInd]:
            offsToMeasure[worstInd] = ref
        # expansion
        elif measref >= measuredVals[bestInd]:
            exp = meanoffsToMeasure + (ref - meanoffsToMeasure) * beta
            measexp = evalPointFun(exp)
            if measexp > measref:
                offsToMeasure[worstInd] = exp
            else:
                offsToMeasure[worstInd] = ref
        # contraction
        elif measref <= measuredVals[worstInd]:
            con = meanoffsToMeasure + (offsToMeasure[worstInd] - meanoffsToMeasure) * gamma
            meascon = evalPointFun(con)
            if meascon > measref:
                offsToMeasure[worstInd] = con
            else:
                for offs in range(len(offsToMeasure)):
                    offsToMeasure[offs] = offsToMeasure[bestInd] + (offsToMeasure[offs] - offsToMeasure[bestInd]) * theta
    return (offsToMeasure[bestInd], measuredVals[bestInd])

def NelderMead2D(bTest, weiQuery, nVertices=3, iteration=10, order=2, relativeGauss=False, Tol=0., alpha=0., beta=0., gamma=0., theta=0., quiet=False):
    ''' Perform modified 2D NelderMead

        Args:
            nVertices (int): number of evaluations per simplex. Use more for higher dimensions
            Tol (float): if the second order moment falls within this range, search returns successfully
            alpha/beta/gamma/theta: tunable parameters

        Returns:
            (float, float): principle component vector and associated principle component
    '''
    #weiQuery = np.array([[1.,0.],[0.,1.],[1.*np.cos(np.pi/4),-1.*np.sin(np.pi/4)]])
    #weiQuery = np.array([[-1.,0.],[0.,1.],[0.,-1.]])
    momMeas = np.zeros(nVertices)
    for iIter in range(iteration):
        momMeas = bTest.getMoment(weiQuery, order, relativeGauss)
        # compute the centroid
        meanweiQuery = np.mean(weiQuery, axis=0)
        normalmeanweiQuery = meanweiQuery / np.linalg.norm(meanweiQuery)
        # find the best & worst direction
        bestInd = np.argmax(momMeas)
        worstInd = np.argmin(momMeas)
        # termination
        if abs(momMeas[bestInd] - momMeas[worstInd]) < Tol:
            if not quiet:
                print('Convergence!')
            break
        # reflection
        ref = normalmeanweiQuery + (normalmeanweiQuery - weiQuery[worstInd]) * alpha
        normalref = np.array([ref / np.linalg.norm(ref)])
        momMeasref = bTest.getMoment(normalref, order, relativeGauss)
        if momMeasref > momMeas[worstInd] and momMeasref < momMeas[bestInd]:
            weiQuery[worstInd] = normalref
        # expansion
        elif momMeasref >= momMeas[bestInd]:
            exp = normalmeanweiQuery + (ref - normalmeanweiQuery) * beta
            normalexp = np.array([exp / np.linalg.norm(exp)])
            momMeasexp = bTest.getMoment(normalexp, order, relativeGauss)
            if momMeasexp > momMeasref:
                weiQuery[worstInd] = normalexp
            else:
                weiQuery[worstInd] = normalref
        # contraction
        elif momMeasref <= momMeas[worstInd]:
            con = normalmeanweiQuery + (weiQuery[worstInd] - normalmeanweiQuery) * gamma
            normalcon = np.array([con / np.linalg.norm(con)])
            momMeascon = bTest.getMoment(normalcon, order, relativeGauss)
            if momMeascon > momMeasref:
                weiQuery[worstInd] = normalcon
            else:
                for offs in range(len(weiQuery)):
                    weiQuery[offs] = weiQuery[bestInd] + (weiQuery[offs] - weiQuery[bestInd]) * theta
                    weiQuery[offs] = np.array([weiQuery[offs] / np.linalg.norm(weiQuery[offs])])
                    #print(weiQuery[offs])
        print(weiQuery[bestInd], momMeas[bestInd])
    return (weiQuery[bestInd], momMeas[bestInd])

def NelderMead3D(bTest, weiQuery, nVertices=4, iteration=10, order=2, relativeGauss=False, Tol=0., alpha=0., beta=0., gamma=0., theta=0., quiet=False):
    ''' Perform modified 3D NelderMead

        Args:
            nVertices (int): number of evaluations per simplex. Use more for higher dimensions
            Tol (float): if the second order moment falls within this range, search returns successfully
            alpha/beta/gamma/theta: tunable parameters

        Returns:
            (float, float): principle component vector and associated principle component
    '''
    #weiQuery = np.array([[1.,0.],[0.,1.],[1.*np.cos(np.pi/4),-1.*np.sin(np.pi/4)]])
    #weiQuery = np.array([[-1.,0.],[0.,1.],[0.,-1.]])
    momMeas = np.zeros(nVertices)
    for iIter in range(iteration):
        momMeas = bTest.getMoment(weiQuery, order, relativeGauss)
        # compute the centroid
        meanweiQuery = np.mean(weiQuery, axis=0)
        normalmeanweiQuery = meanweiQuery / np.linalg.norm(meanweiQuery)
        # find the best & worst direction
        bestInd = np.argmax(momMeas)
        worstInd = np.argmin(momMeas)
        # termination
        if abs(momMeas[bestInd] - momMeas[worstInd]) < Tol:
            if not quiet:
                print('Convergence!')
            break
        # reflection
        ref = normalmeanweiQuery + (normalmeanweiQuery - weiQuery[worstInd]) * alpha
        normalref = np.array([ref / np.linalg.norm(ref)])
        momMeasref = bTest.getMoment(normalref, order, relativeGauss)
        if momMeasref > momMeas[worstInd] and momMeasref < momMeas[bestInd]:
            weiQuery[worstInd] = normalref
        # expansion
        elif momMeasref >= momMeas[bestInd]:
            exp = normalmeanweiQuery + (ref - normalmeanweiQuery) * beta
            normalexp = np.array([exp / np.linalg.norm(exp)])
            momMeasexp = bTest.getMoment(normalexp, order, relativeGauss)
            if momMeasexp > momMeasref:
                weiQuery[worstInd] = normalexp
            else:
                weiQuery[worstInd] = normalref
        # contraction
        elif momMeasref <= momMeas[worstInd]:
            con = normalmeanweiQuery + (weiQuery[worstInd] - normalmeanweiQuery) * gamma
            normalcon = np.array([con / np.linalg.norm(con)])
            momMeascon = bTest.getMoment(normalcon, order, relativeGauss)
            if momMeascon > momMeasref:
                weiQuery[worstInd] = normalcon
            else:
                for offs in range(len(weiQuery)):
                    weiQuery[offs] = weiQuery[bestInd] + (weiQuery[offs] - weiQuery[bestInd]) * theta
                    weiQuery[offs] = np.array([weiQuery[offs] / np.linalg.norm(weiQuery[offs])])
                    #print(weiQuery[offs])
        print(weiQuery[bestInd], momMeas[bestInd])
    return (weiQuery[bestInd], momMeas[bestInd])

def NelderMead(bTest, weiQuery, iteration=10, order=2, relativeGauss=False, Tol=0., alpha=0., beta=0., gamma=0., theta=0., quiet=False):
    ''' Perform modified 3D NelderMead

        Args:
            nVertices (int): number of evaluations per simplex. Use more for higher dimensions
            Tol (float): if the second order moment falls within this range, search returns successfully
            alpha/beta/gamma/theta: tunable parameters

        Returns:
            (float, float): principle component vector and associated principle component
    '''
    shape = np.shape(weiQuery)
    nVertices = shape[0]
    momMeas = np.zeros(nVertices)
    for iIter in range(iteration):
        momMeas = bTest.getMoment(weiQuery, order, relativeGauss)
        # compute the centroid
        meanweiQuery = np.mean(weiQuery, axis=0)
        normalmeanweiQuery = meanweiQuery / np.linalg.norm(meanweiQuery)
        # find the best & worst direction
        bestInd = np.argmax(momMeas)
        worstInd = np.argmin(momMeas)
        # termination
        if abs(momMeas[bestInd] - momMeas[worstInd]) < Tol:
            if not quiet:
                print('Convergence!')
            break
        # reflection
        ref = normalmeanweiQuery + (normalmeanweiQuery - weiQuery[worstInd]) * alpha
        normalref = np.array([ref / np.linalg.norm(ref)])
        momMeasref = bTest.getMoment(normalref, order, relativeGauss)
        if momMeasref > momMeas[worstInd] and momMeasref < momMeas[bestInd]:
            weiQuery[worstInd] = normalref
        # expansion
        elif momMeasref >= momMeas[bestInd]:
            exp = normalmeanweiQuery + (ref - normalmeanweiQuery) * beta
            normalexp = np.array([exp / np.linalg.norm(exp)])
            momMeasexp = bTest.getMoment(normalexp, order, relativeGauss)
            if momMeasexp > momMeasref:
                weiQuery[worstInd] = normalexp
            else:
                weiQuery[worstInd] = normalref
        # contraction
        elif momMeasref <= momMeas[worstInd]:
            con = normalmeanweiQuery + (weiQuery[worstInd] - normalmeanweiQuery) * gamma
            normalcon = np.array([con / np.linalg.norm(con)])
            momMeascon = bTest.getMoment(normalcon, order, relativeGauss)
            if momMeascon > momMeasref:
                weiQuery[worstInd] = normalcon
            else:
                for offs in range(len(weiQuery)):
                    weiQuery[offs] = weiQuery[bestInd] + (weiQuery[offs] - weiQuery[bestInd]) * theta
                    weiQuery[offs] = np.array([weiQuery[offs] / np.linalg.norm(weiQuery[offs])])
                    #print(weiQuery[offs])
        #print(weiQuery[bestInd], momMeas[bestInd])
    return (weiQuery[bestInd], momMeas[bestInd])

def NelderMeadSweepAlpha(bTest, weiQueryInitial, iteration=10, order=2, relativeGauss=False, Tol=0., sweep_num = 21, beta=0., gamma=0., theta=0.):
    alpha = np.linspace(0., 2., sweep_num)
    momOpti = np.zeros(sweep_num)
    weiQuery = np.tile(weiQueryInitial,(sweep_num,1))
    for i in range(sweep_num):
        weight, momOpti[i] = NelderMead(bTest, np.array([weiQuery[i]]), iteration=iteration, order=order, relativeGauss=relativeGauss, Tol=Tol, alpha=alpha[i], beta=beta, gamma=gamma, theta=theta)
        print(alpha[i], momOpti[i])
    plt.plot(alpha,momOpti)
    plt.xlabel('alpha')
    plt.ylabel('2nd moment')

def NelderMeadSweepBeta(bTest, weiQueryInitial, iteration=10, order=2, relativeGauss=False, Tol=0., sweep_num = 21, alpha=0., gamma=0., theta=0.):
    beta = np.linspace(1., 3., sweep_num)
    momOpti = np.zeros(sweep_num)
    weiQuery = np.tile(weiQueryInitial,(sweep_num,1))
    for i in range(sweep_num):
        weight, momOpti[i] = NelderMead(bTest, np.array([weiQuery[i]]), iteration=iteration, order=order, relativeGauss=relativeGauss, Tol=Tol, alpha=alpha, beta=beta[i], gamma=gamma, theta=theta)
        print(beta[i], momOpti[i])
    plt.plot(beta,momOpti)
    plt.xlabel('beta')
    plt.ylabel('2nd moment')

def NelderMeadSweepGamma(bTest, weiQueryInitial, iteration=10, order=2, relativeGauss=False, Tol=0., sweep_num = 21, alpha=0., beta=0., theta=0.):
    gamma = np.linspace(0., 2., sweep_num)
    momOpti = np.zeros(sweep_num)
    weiQuery = np.tile(weiQueryInitial,(sweep_num,1))
    for i in range(sweep_num):
        weight, momOpti[i] = NelderMead(bTest, np.array([weiQuery[i]]), iteration=iteration, order=order, relativeGauss=relativeGauss, Tol=Tol, alpha=alpha, beta=beta, gamma=gamma[i], theta=theta)
        print(gamma[i], momOpti[i])
    plt.plot(gamma,momOpti)
    plt.xlabel('gamma')
    plt.ylabel('2nd moment')

def NelderMeadSweepTheta(bTest, weiQueryInitial, iteration=10, order=2, relativeGauss=False, Tol=0., sweep_num = 21, alpha=0., beta=0., gamma=0.):
    theta = np.linspace(0., 2., sweep_num)
    momOpti = np.zeros(sweep_num)
    weiQuery = np.tile(weiQueryInitial,(sweep_num,1))
    for i in range(sweep_num):
        weight, momOpti[i] = NelderMead(bTest, np.array([weiQuery[i]]), iteration=iteration, order=order, relativeGauss=relativeGauss, Tol=Tol, alpha=alpha, beta=beta, gamma=gamma, theta=theta[i])
        print(theta[i], momOpti[i])
    plt.plot(theta,momOpti)
    plt.xlabel('theta')
    plt.ylabel('2nd moment')
