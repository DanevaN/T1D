def instantanious_AUC_I(CL, active_insulin, time_interval=5):
    """
    Calculate the instantaneous Area Under the Curve (AUC) for active insulin.
    
    Parameters:
    -----------
    CL : float
        Insulin clearance rate (L/min)
    active_insulin : float
        Active insulin amount (units)
    time_interval : float, default=5
        Time interval in minutes over which to calculate AUC
        
    Returns:
    --------
    float
        Instantaneous AUC value
    """
    # Convert time interval from minutes to hours for consistency
    time_interval_hr = time_interval / 60.0
    
    # Instantaneous AUC calculation
    auc = (active_insulin / CL) * time_interval_hr
    
    return auc

def instantanious_AUC_G(basal_glucose, glucose, time_interval=5):
    """
    Calculate the instantaneous Area Under the Curve (AUC) for glucose.
    
    Parameters:
    -----------
    basal_glucose : float 
        base to measure excess from (mmol/dL), e.g. 5.6
    glucose : float
        Blood glucose concentration (mmol/dL)
    time_interval : float, default=5
        Time interval in minutes over which to calculate AUC
        
    Returns:
    --------
    float
        Instantaneous AUC value
    """
    # Convert time interval from minutes to hours for consistency
    time_interval_hr = time_interval / 60.0
    
    # Instantaneous AUC calculation
    auc = (glucose - basal_glucose) * time_interval_hr
    
    return auc
def instantanious_AUC_C(carb_unabsorbed, time_interval=5):
    """
    Calculate the instantaneous Area Under the Curve (AUC) for carbohydrate absorption.
    
    Parameters:
    -----------
    
    carb_unabsorbed : float
        Amount of carbohydrates absorbed (g)
    time_interval : float, default=5
        Time interval in minutes over which to calculate AUC
        
    Returns:
    --------
    float
        Instantaneous AUC value
    """
    # Convert time interval from minutes to hours for consistency
    time_interval_hr = time_interval / 60.0

    # Instantaneous AUC calculation
    auc = (carb_unabsorbed) * time_interval_hr

    return auc

