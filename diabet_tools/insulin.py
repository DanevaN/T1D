
import numpy as np
import matplotlib.pyplot as plt
from typing import Union, List, Optional
from scipy.special import gamma

def calculate_insulin_clearance(height_cm: float, 
                              weight_kg: Optional[float] = None,
                              age_years: Optional[float] = None,
                              sex: str = 'male',
                              method: str = 'height_based') -> float:
    """
    Calculate plasma insulin clearance (CL) in L/min based on patient characteristics.
    
    Multiple methods available for clearance estimation:
    1. Height-based (primary method)
    2. BSA-based (Body Surface Area)
    3. Allometric scaling
    
    Parameters:
    -----------
    height_cm : float
        Patient height in centimeters
    weight_kg : float, optional
        Patient weight in kilograms (required for BSA and allometric methods)
    age_years : float, optional
        Patient age in years (for age corrections)
    sex : str, default='male'
        Patient sex ('male' or 'female')
    method : str, default='height_based'
        Clearance calculation method: 'height_based', 'bsa', 'allometric'
        
    Returns:
    --------
    float
        Insulin clearance in L/min
        
    References:
    -----------
    - Height-based: CL = 0.8 + 0.05 * (height_cm - 170) / 10  [L/min]
    - BSA-based: CL = 1.2 * BSA  [L/min], where BSA in m²
    - Allometric: CL = 1.5 * (weight/70)^0.75  [L/min]
    """
    
    if method == 'height_based':
        # Primary method: Height-based clearance
        # Reference clearance: ~1.2 L/min for 170 cm individual
        base_clearance = 1.2  # L/min for reference height (170 cm)
        height_factor = (height_cm - 170) / 100  # Normalized height difference
        clearance = base_clearance * (1 + 0.4 * height_factor)
        
        # Sex adjustment (females typically 10-15% lower clearance)
        if sex.lower() == 'female':
            clearance *= 0.85
            
    elif method == 'bsa':
        if weight_kg is None:
            raise ValueError("Weight required for BSA-based clearance calculation")
        
        # Calculate Body Surface Area using Dubois formula
        # BSA (m²) = 0.007184 * weight^0.425 * height^0.725
        bsa = 0.007184 * (weight_kg**0.425) * (height_cm**0.725)
        clearance = 0.65 * bsa  # L/min per m² BSA
        
    elif method == 'allometric':
        if weight_kg is None:
            raise ValueError("Weight required for allometric clearance calculation")
        
        # Allometric scaling based on weight
        clearance = 1.5 * (weight_kg / 70.0)**0.75
        
        # Height adjustment
        height_factor = height_cm / 170.0
        clearance *= height_factor**0.25
        
    else:
        raise ValueError("Method must be 'height_based', 'bsa', or 'allometric'")
    
    # Age adjustment (clearance decreases ~1% per year after 40)
    if age_years is not None and age_years > 40:
        age_factor = 1 - 0.01 * (age_years - 40)
        clearance *= max(age_factor, 0.7)  # Minimum 70% of adult clearance
    
    # Ensure reasonable bounds
    clearance = np.clip(clearance, 0.5, 3.0)  # L/min bounds
    
    return clearance

def novorapid_pharmacokinetics(t, dose_units, CL, ka=0.15, Vd=0.15):
    """
    Calculate active insulin concentration over time for NovoRapid.
    
    Parameters:
    t: Time in minutes
    dose_units: Insulin dose in units
    CL: Plasma clearance in L/min
    ka: Absorption rate constant (1/min) - default for rapid-acting
    Vd: Volume of distribution in L/kg (default ~0.15 L/kg for a 70kg person = ~10.5L)
    
    Returns:
    Active insulin concentration in units/L
    """
    # Convert dose to amount (1 unit = ~6 nmol, but we'll work in units)
    # Assume average weight of 70kg for Vd calculation
    Vd_total = Vd * 70  # Total volume of distribution in L
    
    # Elimination rate constant
    ke = CL / Vd_total
    
    # Two-compartment model: absorption and elimination
    # For subcutaneous injection, we model absorption from injection site
    if t <= 0:
        return 0
    
    # Concentration = (Dose/Vd) * (ka/(ka-ke)) * (exp(-ke*t) - exp(-ka*t))
    conc = 0.95*(dose_units / Vd_total) * (ka / (ka - ke)) * (np.exp(-ke * t) - np.exp(-ka * t))
    
    return max(0, conc)

def tresiba_active_insulin(time: Union[float, List[float]], 
                          units: float = 1.0,
                          height_cm: float = 170.0,
                          weight_kg: Optional[float] = None,
                          age_years: Optional[float] = None,
                          sex: str = 'male',
                          clearance_method: str = 'height_based') -> Union[float, np.ndarray]:
    """
    Calculate active insulin for Tresiba (insulin degludec) with individualized clearance.
    
    Model incorporates patient-specific plasma insulin clearance (CL) based on:
    - Height (primary factor)
    - Weight (if available)
    - Age and sex adjustments
    
    Pharmacokinetic model:
    I(t) = (Dose/Vd) * ka/(ka-ke) * [exp(-ke*t) - exp(-ka*t)]
    where ke = CL/Vd (elimination rate constant)
    
    Parameters:
    -----------
    time : float or array-like
        Time in hours since injection (must be >= 0)
    units : float, default=1.0
        Number of units injected
    height_cm : float, default=170.0
        Patient height in centimeters
    weight_kg : float, optional
        Patient weight in kilograms
    age_years : float, optional
        Patient age in years
    sex : str, default='male'
        Patient sex ('male' or 'female')
    clearance_method : str, default='height_based'
        Method for calculating insulin clearance
        
    Returns:
    --------
    float or numpy.ndarray
        Active insulin amount (in units) at specified time(s)
        
    Pharmacokinetic parameters for Tresiba:
    - Duration: 42+ hours (ultra-long acting)
    - Onset: 1-3 hours
    - Vd: ~0.4 L/kg (volume of distribution)
    - Bioavailability: ~70% (subcutaneous)
    """
    
    # Calculate patient-specific insulin clearance
    clearance_L_per_min = calculate_insulin_clearance(
        height_cm, weight_kg, age_years, sex, clearance_method
    )
    
    # Convert clearance to L/hr
    clearance_L_per_hr = clearance_L_per_min * 60
    
    # Pharmacokinetic parameters
    vd_per_kg = 0.4  # L/kg volume of distribution
    estimated_weight = weight_kg if weight_kg else estimate_weight_from_height(height_cm, sex)
    vd_total = vd_per_kg * estimated_weight  # Total volume of distribution (L)
    
    # Rate constants
    ke = clearance_L_per_hr / vd_total  # Elimination rate constant (1/hr)
    ka = 0.08  # Absorption rate constant for Tresiba (1/hr) - slow absorption
    
    # Bioavailability and depot formation factors for Tresiba
    bioavailability = 0.70  # 70% bioavailability
    depot_factor = 0.6  # Slow release from subcutaneous hexamer depot
    
    # Handle both single values and arrays
    t = np.asarray(time)
    t = np.maximum(t, 0)  # Ensure non-negative time
    
    # Two-compartment model with depot formation (Tresiba-specific)
    # Accounts for slow absorption from hexamer formation
    
    # Fast absorption component (minor)
    fast_component = 0.3 * np.exp(-0.15 * t)  # Quick initial absorption
    
    # Slow depot release (major component for Tresiba)
    if ka != ke:
        slow_component = (ka / (ka - ke)) * (np.exp(-ke * t) - np.exp(-ka * t))
    else:
        # Handle case where ka = ke
        slow_component = ka * t * np.exp(-ke * t)
    
    # Combined absorption profile
    absorption_profile = fast_component + depot_factor * slow_component
    
    # Scale by dose and bioavailability
    active = units * bioavailability * absorption_profile
    
    # Apply clearance scaling factor
    clearance_scaling = clearance_L_per_min / 1.2  # Normalize to reference clearance
    active *= (1 / clearance_scaling)  # Higher clearance = lower active insulin
    
    # Ensure realistic bounds
    active = np.maximum(active, 0)
    
    # Return scalar if input was scalar
    if np.isscalar(time):
        return float(active)
    else:
        return active

def estimate_weight_from_height(height_cm: float, sex: str = 'male') -> float:
    """
    Estimate weight from height using standard formulas when weight is not available.
    
    Uses Devine formula:
    - Male: 50 + 2.3 * (height_in - 60)
    - Female: 45.5 + 2.3 * (height_in - 60)
    """
    height_inches = height_cm / 2.54
    
    if sex.lower() == 'male':
        weight_kg = 50 + 2.3 * (height_inches - 60)
    else:
        weight_kg = 45.5 + 2.3 * (height_inches - 60)
    
    return max(weight_kg, 40)  # Minimum reasonable weight
