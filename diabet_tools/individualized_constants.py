import numpy as np
import matplotlib.pyplot as plt
from typing import Union, List, Optional

UNIT_CONVERSION = 0.0555  # Convert mg/dL to mmol/L (1 mg/dL = 0.0555 mmol/L)

def calculate_insulin_clearance(height_cm: float = 170, 
                              weight_kg: Optional[float] = 53,
                              age_years: Optional[float] = 10,
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


def calculate_glucose_volume_distribution(height_cm: float = 170,
                                        weight_kg: Optional[float] = 53,
                                        age_years: Optional[float] = 10,
                                        sex: str = 'male',
                                        method: str = 'tbw_based') -> float:
    """
    Calculate glucose volume of distribution (Vd) in liters based on patient characteristics.
    
    Glucose distributes in extracellular fluid space (~20% of body weight) plus
    intracellular accessible space. Multiple methods available:
    1. Total Body Water (TBW) based (primary method)
    2. Body Surface Area (BSA) based
    3. Simple weight-based
    
    Parameters:
    -----------
    height_cm : float
        Patient height in centimeters
    weight_kg : float, optional
        Patient weight in kilograms (required for TBW and weight methods)
    age_years : float, optional
        Patient age in years (affects body water composition)
    sex : str, default='male'
        Patient sex ('male' or 'female') - affects body water percentage
    method : str, default='tbw_based'
        Volume calculation method: 'tbw_based', 'bsa_based', 'weight_based'
        
    Returns:
    --------
    float
        Glucose volume of distribution in liters
        
    References:
    -----------
    - Glucose Vd ≈ 0.16-0.25 L/kg (extracellular + accessible intracellular)
    - TBW: Males ~60% body weight, Females ~50% body weight
    - Glucose space ≈ 40-50% of TBW
    - Age effects: TBW decreases ~1% per decade after age 30
    """
    
    if method == 'tbw_based':
        if weight_kg is None:
            raise ValueError("Weight required for TBW-based volume calculation")
        
        # Calculate Total Body Water percentage by sex and age
        if sex.lower() == 'male':
            tbw_percent = 0.60  # 60% for adult males
        else:
            tbw_percent = 0.50  # 50% for adult females
        
        # Age adjustment - TBW decreases with age
        if age_years is not None and age_years > 30:
            age_factor = 1 - 0.01 * (age_years - 30) / 10  # 1% per decade
            tbw_percent *= max(age_factor, 0.85)  # Minimum 85% of adult TBW
        
        # Total Body Water in liters
        tbw = weight_kg * tbw_percent
        
        # Glucose distributes in ~45% of TBW (extracellular + accessible intracellular)
        glucose_space_fraction = 0.45
        volume = tbw * glucose_space_fraction
        
    elif method == 'bsa_based':
        if weight_kg is None:
            raise ValueError("Weight required for BSA-based volume calculation")
        
        # Calculate Body Surface Area using Dubois formula
        bsa = 0.007184 * (weight_kg**0.425) * (height_cm**0.725)
        
        # Glucose Vd ≈ 12-15 L/m² BSA
        volume = 13.5 * bsa  # L/m² BSA
        
    elif method == 'weight_based':
        if weight_kg is None:
            raise ValueError("Weight required for weight-based volume calculation")
        
        # Simple weight-based method: Glucose Vd ≈ 0.20 L/kg
        base_volume_per_kg = 0.20  # L/kg
        
        # Sex adjustment (females typically lower)
        if sex.lower() == 'female':
            base_volume_per_kg *= 0.90
        
        volume = weight_kg * base_volume_per_kg
        
    else:
        raise ValueError("Method must be 'tbw_based', 'bsa_based', or 'weight_based'")
    
    # Height-based fine adjustment (taller individuals have slightly higher Vd)
    height_factor = height_cm / 170.0
    volume *= height_factor**0.15
    
    # Age adjustment for pediatric/elderly (affects distribution)
    if age_years is not None:
        if age_years < 18:
            # Pediatric adjustment - higher Vd/kg in children
            age_factor = 1 + 0.02 * (18 - age_years)
            volume *= min(age_factor, 1.3)  # Max 30% increase
        elif age_years > 65:
            # Elderly adjustment - slightly reduced distribution
            age_factor = 1 - 0.005 * (age_years - 65)
            volume *= max(age_factor, 0.85)  # Min 85% of adult volume
    
    # Ensure reasonable physiological bounds
    volume = np.clip(volume, 5.0, 25.0)  # Reasonable range in liters
    
    return volume


def carb_sensitivity_factor(
                            glucose_volume_distribution: Optional[float] = None,
                            height_cm: float = 170,
                            weight_kg: Optional[float] = 53,
                            age_years: Optional[float] = 10,
                            sex: str = 'female') -> float:
    """
    Calculate the carbohydrate sensitivity factor based on individual characteristics.
    1mg = 1000
    1L=10dL
    Vd in L
    weight kg
    glucose (mg/dL) *10 = glucose mg / L
    glucose (mg/dL) *10 * Vd = carbs mg
    glucose (mg/dL) *10 * Vd /1000 = carbs g

    CSF = glucose rise /carbs = 100/(Vd) in mg/dL per gram of carbohydrate
    To convert to mmol/L per gram of carbohydrate, multiply by 0.0555

    Parameters:
    -----------
    glucose_volume_distribution : float, optional
        Glucose volume of distribution in liters
    height_cm : float
        Height of the individual in centimeters
    weight_kg : float, optional
        Weight of the individual in kilograms
    age_years : float, optional
        Age of the individual in years
    sex : str, default='female'
        Sex of the individual ('male' or 'female')

    Returns:
    --------
    float
        Carbohydrate sensitivity factor (mmol/dL per gram of carbohydrate)
    """
    if glucose_volume_distribution is None:
        glucose_volume_distribution = calculate_glucose_volume_distribution(
            height_cm=height_cm,
            weight_kg=weight_kg,
            age_years=age_years,
            sex=sex
        )

    # Calculate the carbohydrate sensitivity factor
    carb_sensitivity =  100 / glucose_volume_distribution * UNIT_CONVERSION

    return carb_sensitivity

def insulin_sensitivity(carb_sensitivity, CIR):
    """
    Calculate insulin sensitivity factor (ISF) based on carbohydrate sensitivity and carbohydrate-to-insulin ratio (CIR).
    
    Parameters:
    -----------
    carb_sensitivity : float
        Carbohydrate sensitivity factor (mmol/dL per gram of carbohydrate)
    CIR : float
        Carbohydrate-to-insulin ratio (grams of carbohydrate per unit of insulin)
        
    Returns:
    --------
    float
        Insulin sensitivity factor (mmol/dL per unit of insulin)
        
    Formula:
    --------
    ISF = carb_sensitivity * CIR
    """
    return carb_sensitivity * CIR