import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from typing import Union, List, Tuple
F_MAX = 1 
K_A = 0.01  # default absorption rate constant (1/min)
LAG_TIME = 0.0  # default lag time (minutes)

def fractional_absorption(time: Union[float, np.ndarray], 
                         k_a: float = K_A, 
                         f_max: float = F_MAX, 
                         lag_time: float = LAG_TIME) -> Union[float, np.ndarray]:
    """
    Calculate fractional absorption using first-order absorption kinetics.
    
    Mathematical model: f(t) = F_max * (1 - exp(-k_a * (t - t_lag)))
    
    Parameters:
    -----------
    time : float or array-like
        Time in minutes
    k_a : float, default=0.01
        Absorption rate constant (1/min)
    f_max : float, default=0.9
        Maximum fraction absorbed (asymptotic value)
    lag_time : float, default=0.0
        Lag time before absorption begins (minutes)
        
    Returns:
    --------
    float or numpy.ndarray
        1-fractional absorption at specified time(s), i.e. carbs on board which are not absorbed into blood glucose
    """
    
    t = np.asarray(time)
    
    # Apply lag time - no absorption before lag time
    effective_time = np.maximum(t - lag_time, 0)
    
    # First-order absorption equation
    # f(t) = F_max * (1 - exp(-k_a * t)) for t >= t_lag
    fraction = f_max * (1 - np.exp(-k_a * effective_time))
    
    # Ensure no absorption before lag time
    fraction = np.where(t < lag_time, 0, fraction)
    
    # Return scalar if input was scalar
    if np.isscalar(time):
        return float(fraction)
    else:
        return fraction

def carbs_on_board(time: Union[float, np.ndarray], 
                  total_carbs: float, 
                  k_a: float = K_A, 
                  f_max: float = F_MAX, 
                  lag_time: float = LAG_TIME) -> Union[float, np.ndarray]:
    """
    Calculate carbs on board (unabsorbed carbs) at given time after ingestion.
    
    Parameters:
    -----------
    time : float or array-like
        Time in hours
    total_carbs : float
        Total carbs ingested (grams)
    k_a : float, default=0.01
        Absorption rate constant (1/min)
    f_max : float, default=0.9
        Maximum fraction absorbed (asymptotic value)
    lag_time : float, default=0.0
        Lag time before absorption begins (minutes)
        
    Returns:
    --------
    float or numpy.ndarray
        Carbs on board (grams) at specified time(s)
    """
    if time == 0:
        return 0
    fraction_unabsorbed = f_max - fractional_absorption(time * 60, k_a, f_max, lag_time)
    cob = total_carbs * fraction_unabsorbed
    
    return cob  
