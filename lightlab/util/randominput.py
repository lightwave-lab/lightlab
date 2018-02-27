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

def RandomInput(dim, vec_num):
    '''
    return random array containing 'm' normalized weight vectors that are 'n' dimension
    '''
    val = np.random.rand(vec_num,dim)
    sign = np.random.randint(2, size=(vec_num, dim))*2-1
    vec = np.multiply(val,sign)
    for i in range(vec_num):
        vec[i] = vec[i] / np.linalg.norm(vec[i])
    return vec

def VicinityRandom(orthoVec, scale):
    '''
    return random array in the vicinity of orthoVec
    '''
    shape = np.shape(orthoVec)
    dim = shape[0]
    vec_num = dim + 1
    vec = RandomInput(dim, vec_num)/scale
    for i in range(vec_num):
        vec[i] = np.add(orthoVec, vec[i])
        vec[i] /= np.linalg.norm(vec[i])
    return vec 