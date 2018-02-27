import matplotlib.pyplot as plt
import numpy as np
import time
import itertools
from IPython import display
from enum import Enum
import matplotlib.cm
from collections import OrderedDict

from ..util import data as dUtil
from ..util import plot as pUtil
from ..util import io

def GramSchmidt3D(initial_weights, vec_first=None, vec_second=None, orthogonal_first=False, orthogonal_second=False):
    ''' Perform 3D Gram-Schmidt orthogonalization 

        Args:
            initial_weights(array): weight vectors to be orthogonalized
            vec_first/second(vector): provide the first/second vector
            orthogonal_first(boolean): True if looking to orthogonalize initial_weights to the vec_first
            orthogonal_second(boolean): True if looking to orthogonalize initial_weights to the vec_second

        Returns:
            (array): orthogonalized and normalized weight vectors
    '''
    orthogonal_weight_first = np.zeros((4,3))
    orthogonal_weight_second = np.zeros((4,3))
    for i in range(4):
        initial_weights[i] -= np.dot(np.dot(initial_weights[i],vec_first),vec_first)
        orthogonal_weight_first[i] = initial_weights[i] / np.linalg.norm(initial_weights[i])
    if orthogonal_first:
        return orthogonal_weight_first
    for j in range(4):
        initial_weights[j] -= np.dot(np.dot(initial_weights[j],vec_second),vec_first)
        orthogonal_weight_second[j] = initial_weights[j] / np.linalg.norm(initial_weights[j])
    if orthogonal_second:
        return orthogonal_weight_second
    
def GramSchmidt(initial_weights, vec):
    shape1 = np.shape(initial_weights)
    shape2 = np.shape(vec)
    orthogonal_weights = np.zeros((shape1[0],shape1[1]))
    for i in range(shape1[0]):
        for j in range(shape2[0]):
            initial_weights[i] -= np.dot(np.dot(initial_weights[i],vec[j]),vec[j])
        orthogonal_weights[i] = initial_weights[i] / np.linalg.norm(initial_weights[i])
    return orthogonal_weights

def GramSchmidt1Dvec(initial_weights, vec):
    shape1 = np.shape(initial_weights)
    shape2 = np.shape(vec)
    orthogonal_weights = np.zeros((shape1[0],shape1[1]))
    for i in range(shape1[0]):
        initial_weights[i] -= np.dot(np.dot(initial_weights[i],vec),vec)
        orthogonal_weights[i] = initial_weights[i] / np.linalg.norm(initial_weights[i])
    return orthogonal_weights

def GramSchmidt1Dini(initial_weights, vec):
    shape1 = np.shape(initial_weights)
    shape2 = np.shape(vec)
    orthogonal_weights = np.zeros(shape1[0])
    for j in range(shape2[0]):
        initial_weights -= np.dot(np.dot(initial_weights,vec[j]),vec[j])
        orthogonal_weights = initial_weights / np.linalg.norm(initial_weights)
    return orthogonal_weights