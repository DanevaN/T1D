import math
import numpy as np
import matplotlib.pyplot as plt
from typing import Union, List
K_ABS_NOVORAPID = 3.0  # absorption rate constant (1/hr)
K_ELIM_NOVORAPID = 0.8  # elimination rate constant (1/hr)  
K_ABS_TRESIBA = 0.3   # very slow absorption rate constant (1/hr)
K_ELIM_TRESIBA = 0.03 # very slow elimination rate constant (1

def active_insulin(t,type='novorapid'):
    """
    NovoRapid (insulin aspart) action profile for 1 unit
    Based on pharmacokinetic data:
    - Onset: ~10-20 minutes
    - Peak: ~1-3 hours  
    - Duration: ~3-5 hours
    Using bi-exponential model
    
    Tresiba (insulin degludec) action profile for 1 unit
    Based on pharmacokinetic data:
    - Onset: ~1-3 hours (slow start)
    - Peak: ~12-24 hours (very flat peak)
    - Duration: ~42+ hours (ultra-long acting)
    Using modified exponential model for depot formation
    
    t: time in hours since dose administration
    type: type of insulin, 'novorapid' or 'tresiba'
    Returns: instantanious active insulin per unit injected at t=0
    """
    if type=='novorapid':
        k_abs = K_ABS_NOVORAPID
        k_elim = K_ELIM_NOVORAPID   
    elif type=='tresiba':
        k_abs = K_ABS_TRESIBA
        k_elim = K_ELIM_TRESIBA
    else:
        raise ValueError("Type must be 'novorapid' or 'tresiba'")
    if t <= 0:
        return 0
    
        # Bi-exponential model: absorption - elimination
    active_insulin = k_elim * k_abs * (np.exp(-k_elim * t) - np.exp(-k_abs * t)) / (k_abs - k_elim)
    
       
    return max(0, active_insulin)


def insulin_on_board(t,type='novorapid'):
    """
    NovoRapid (insulin aspart) action profile for 1 unit
    Based on pharmacokinetic data:
    - Onset: ~10-20 minutes
    - Peak: ~1-3 hours  
    - Duration: ~3-5 hours
    Using bi-exponential model
    
    Tresiba (insulin degludec) action profile for 1 unit
    Based on pharmacokinetic data:
    - Onset: ~1-3 hours (slow start)
    - Peak: ~12-24 hours (very flat peak)
    - Duration: ~42+ hours (ultra-long acting)
    Using modified exponential model for depot formation
    
    t: time in hours since dose administration
    type: type of insulin, 'novorapid' or 'tresiba'
    returns fraction of insulin remaining active (IOB) at time t after injection
    0 <= IOB <= 1 
    1 unit injected at t=0           
    """
    if type=='novorapid':
        k_abs = K_ABS_NOVORAPID
        k_elim = K_ELIM_NOVORAPID   
    elif type=='tresiba':
        k_abs = K_ABS_TRESIBA
        k_elim = K_ELIM_TRESIBA
    else:
        raise ValueError("Type must be 'novorapid' or 'tresiba'")
    if t <= 0:
        return 0
    
        # Bi-exponential model: absorption - elimination
    insulin_on_board = ( k_abs  * np.exp(-k_elim * t) - k_elim * np.exp(-k_abs * t)) / (k_abs - k_elim)
    
       
    return max(0, insulin_on_board)


