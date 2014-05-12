# -*- coding: utf-8 -*-
"""
Created on Thu Apr 24 18:05:41 2014

@author: thiolliere
"""

import os
import numpy as np

def generate_testitems(base, n, repeats=0, name='data.item'):
    #f = os.open("dataset_test", os.O_CREAT)
    res = np.empty((base**n*(repeats+1) +1, n+2), dtype='|S5')
    res[0,0] = '#item'
    res[0,1] = '#src'
    
    for j,_ in enumerate(res[0,2:]):
        res[0,j+2] = 'c' + str(j)
        
    for i,_ in enumerate(res[1:,0]):
        res[i+1,0] = 's' + str(i)
        
    for i,_ in enumerate(res[1:,1]):
        res[i+1,1] = 'i' + str(i)
        
    aux = res[1:,2:]
    for (i,j), _ in np.ndenumerate(aux):
        aux[i][j] = (i/(base**j) % base)

    np.savetxt(name,res,delimiter=' ',fmt='%s') 

generate_testitems(5,5)
