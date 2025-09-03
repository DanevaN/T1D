import pandas as pd
import numpy as np
from .active_insulin import  insulin_on_board
from .fractional_absorption import carbs_on_board
from .individualized_constants import calculate_insulin_clearance, calculate_glucose_volume_distribution
BW =53 #body weight kg
HEIGHT_CM =170
AGE_YEARS =14
CONVERSION =18 # to convert mg/dL to mmol/L
GEZI = 0.01 #dL/kg/min glucose efectiveness at zero insulin

def calculate_active_insulin_and_carbs_timeseries(data_df):
    """
    Calculate active insulin by processing each bolus event sequentially.
    For each row with bolus > 0, take current active insulin + new bolus effect.
    
    Parameters:
    -----------
    data_df : pandas.DataFrame
        DataFrame with DateTime_rounded column and bolus columns (carb_bolus, correction_bolus, extended_bolus)
        as well as basal insulin column (basal) and carbs column (carbs)
    
    Returns:
    --------
    pandas.DataFrame
        Original DataFrame with added 'IOB_novorapid', 'IOB_tresiba', 'COB' columns
    """
    
    # Make a copy to avoid modifying original data
    df = data_df.copy()
    
    # Calculate total bolus for each row
    bolus_columns = ['carb_bolus', 'correction_bolus', 'extended_bolus']
    carb_columns = ['carbs']
    basal_columns = ['basal']
    df['total_bolus'] = df[bolus_columns].fillna(0).sum(axis=1)
    df['total_carbs'] = df[carb_columns].fillna(0).sum(axis=1)
    df['total_basal'] = df[basal_columns].fillna(0).sum(axis=1)

    # Sort by datetime to ensure chronological order
    df = df.sort_values('DateTime_rounded').reset_index(drop=True)
    
    # Initialize active insulin column
    df['IOB_novorapid'] = 0.0
    df['IOB_tresiba'] = 0.0
    df['COB'] = 0.0
    # Get rows with bolus events (non-zero boluses)
    bolus_rows = df[df['total_bolus'] > 0].copy()
    
    print(f"Processing {len(bolus_rows)} bolus events sequentially...")
    
    # Process each bolus row sequentially
    for bolus_idx, (df_idx, bolus_row) in enumerate(bolus_rows.iterrows()):
        current_time = bolus_row['DateTime_rounded']
        current_bolus = bolus_row['total_bolus']
        
        # Get current active insulin level at this time point
        current_active = df.loc[df_idx, 'IOB_novorapid']
        
        # Calculate new active insulin: current active + new bolus effect (at time 0)
        new_bolus_effect = insulin_on_board(0, 'novorapid') * current_bolus  # At injection time (t=0)
        new_active_total = current_active + new_bolus_effect
        
        # Write result back to this row
        df.loc[df_idx, 'IOB_novorapid'] = new_active_total
        
        # Now propagate this bolus effect to all future timepoints
        future_rows = df[df['DateTime_rounded'] > current_time].copy()
        
        for future_idx, future_row in future_rows.iterrows():
            future_time = future_row['DateTime_rounded']
            
            # Calculate time elapsed since this bolus (in hours)
            time_elapsed = (future_time - current_time).total_seconds() / 3600.0
            
            # Only apply if within insulin duration window (6 hours)
            if 0 < time_elapsed <= 6:
                # Calculate active insulin from this specific bolus at this future time
                bolus_effect_at_time = insulin_on_board(time_elapsed,'novorapid') * current_bolus
                
                # Add this effect to the future row's active insulin
                df.loc[future_idx, 'IOB_novorapid'] += bolus_effect_at_time
        
    print("Completed sequential bolus processing.")
    
    # Now process basal insulin similarly
    basal_rows = df[df['total_basal'] > 0].copy()

    # Process each basal row sequentially
    for basal_idx, (df_idx, basal_row) in enumerate(basal_rows.iterrows()):
        current_time = basal_row['DateTime_rounded']
        current_basal = basal_row['total_basal']
        
        # Get current active insulin level at this time point
        current_active = df.loc[df_idx, 'IOB_tresiba']
        
        # Calculate new active insulin: current active + new bolus effect (at time 0)
        new_basal_effect = insulin_on_board(0, 'tresiba') * current_basal  # At injection time (t=0)
        new_active_total = current_active + new_basal_effect

        # Write result back to this row
        df.loc[df_idx, 'IOB_tresiba'] = new_active_total
        
        # Now propagate this bolus effect to all future timepoints
        future_rows = df[df['DateTime_rounded'] > current_time].copy()
        
        for future_idx, future_row in future_rows.iterrows():
            future_time = future_row['DateTime_rounded']
            
            # Calculate time elapsed since this bolus (in hours)
            time_elapsed = (future_time - current_time).total_seconds() / 3600.0
            
            # Only apply if within insulin duration window (6 hours)
            if 0 < time_elapsed <= 96:
                # Calculate active insulin from this specific bolus at this future time
                bolus_effect_at_time = insulin_on_board(time_elapsed, 'tresiba') * current_basal

                # Add this effect to the future row's active insulin
                df.loc[future_idx, 'IOB_tresiba'] += bolus_effect_at_time
        
        df['total_active_insulin'] = df['IOB_novorapid'] + df['IOB_tresiba']
    
    print("Completed sequential basal processing.")

    # Now process carbs absorption
    carb_rows = df[df['total_carbs'] > 0].copy()
    
    for carb_idx, (df_idx, carb_row) in enumerate(carb_rows.iterrows()):
        current_time = carb_row['DateTime_rounded']
        current_carb = carb_row['total_carbs']

        # Get current carbs on board level at this time point
        current_COB = df.loc[df_idx, 'COB']
        
        # Calculate new active insulin: current active + new bolus effect (at time 0)
        new_carbs = carbs_on_board(0, current_carb)  # At injection time (t=0)
        new_COB = current_COB + new_carbs

        # Write result back to this row
        df.loc[df_idx, 'COB'] = new_COB

        # Now propagate this carb effect to all future timepoints
        future_rows = df[df['DateTime_rounded'] > current_time].copy()
        
        for future_idx, future_row in future_rows.iterrows():
            future_time = future_row['DateTime_rounded']
            
            # Calculate time elapsed since this bolus (in hours)
            time_elapsed = (future_time - current_time).total_seconds() / 3600.0

            df.loc[future_idx, 'COB'] += carbs_on_board(time_elapsed, current_carb)

    print("Completed sequential carb processing.")
    return df

def process_period(df_period, group_col ='DateTime_hour', 
                   use_period_start_glucose_as_basal = False, basal_glucose=5.6, 
                   time_interval = 5/60):
    """
    provide data for particular period to calculate aggregated statistics over
    
    Calculate:amount of carbohydrates: AoC = carbs eaten during period + COB_start - COB_end 
    area under the curve insulin: AUC_novorapid = total_boluses + IOB_novorapid_start -IOB_novorapid_end
    area under the curve basal insulin: AUC_tresiba = total_basal + IOB_tresiba_start - IOB_tresiba_end
    area under the curve abs glucose over basal = AUC_abs_delta_glucose = sum(abs(glucose - basal_glucose,0)) * time_interval (in hours)
    area under the curve glucose over basal = AUC_delta_glucose = sum(glucose - basal_glucose) * time_interval (in hours)
    """
    # Calculate total bolus (sum of all bolus types)
    V_g = calculate_glucose_volume_distribution(weight_kg=BW, height_cm=HEIGHT_CM, age_years=AGE_YEARS) 
    CL = calculate_insulin_clearance(weight_kg=BW, height_cm=HEIGHT_CM, age_years=AGE_YEARS)
    # in the pape volume distribution for glucose is VG = fixed to 1.45 dL/kg
    dataset = df_period.copy()
    dataset['total_bolus'] = dataset['carb_bolus'] + dataset['correction_bolus'] + dataset['extended_bolus']
    IOB_novorapid_start = dataset.iloc[0]['IOB_novorapid']
    IOB_novorapid_end = dataset.iloc[-1]['IOB_novorapid']
    IOB_tresiba_start = dataset.iloc[0]['IOB_tresiba']
    IOB_tresiba_end = dataset.iloc[-1]['IOB_tresiba']
    COB_start = dataset.iloc[0]['COB']
    COB_end = dataset.iloc[-1]['COB']
    glucose_start = dataset.iloc[0]['glucose']
    glucose_end = dataset.iloc[-1]['glucose']
    if use_period_start_glucose_as_basal:
        basal_glucose = glucose_start 

    dataset['glucose_over_basal'] = (dataset['glucose'] - basal_glucose) * dataset['time_interval']
    dataset['abs_glucose_over_basal'] = dataset['glucose_over_basal'].abs()
    # Group by Date and sum carbs and boluses
    grouped = dataset.groupby(group_col).agg({
        'total_carbs': 'sum',
        'total_bolus': 'sum',
        'total_basal': 'sum',
        'glucose_over_basal': 'sum',  # AUC glucose over basal
        'abs_glucose_over_basal': 'sum',
        'DateTime_rounded': ['min', 'max']
    }).round(4)
    # Flatten column names
    grouped.columns = ['total_carbs', 'total_bolus', 'total_basal', 'AUC_delta_glucose', 'AUC_abs_delta_glucose', 'first_reading', 'last_reading']
    
    # Reset index to make Date a column
    #CL is liters per min times 60 is liters per hour
    grouped = grouped.reset_index()
    grouped['period_length'] = ((grouped['last_reading']  - grouped['first_reading']).dt.total_seconds() +5*60)/ 3600  # in hours
    grouped['AoC'] = grouped['total_carbs'] + COB_start - COB_end
    grouped['AUC_novorapid'] = grouped['total_bolus'] + IOB_novorapid_start - IOB_novorapid_end
    grouped['AUC_tresiba'] = grouped['total_basal'] + IOB_tresiba_start - IOB_tresiba_end   
    grouped['insulin_sensitivity_article'] = (grouped['AoC']/BW \
                        -GEZI *60 * grouped['AUC_delta_glucose'] * CONVERSION/1000  \
                        - V_g / BW * (glucose_end - glucose_start) * CONVERSION/1000  ) \
                            / (1/(CL*60)*(grouped['AUC_novorapid'] + grouped['AUC_tresiba'])* grouped['AUC_abs_delta_glucose'] * CONVERSION /1000 / grouped['period_length'] )
    grouped['insulin_sensitivity_Nadia'] = (grouped['AoC']/BW \
                        -GEZI *60 * grouped['AUC_delta_glucose'] * CONVERSION /1000 \
                        - V_g / BW * (glucose_end - glucose_start) * CONVERSION /1000 ) \
                            / (1/CL*(grouped['AUC_novorapid'] )* grouped['AUC_abs_delta_glucose'] * CONVERSION / 1000/ grouped['period_length'] )
    return grouped

def get_period_of_day(hour):
    """
    Convert hour to period of day:
    7-9: morning
    9-11: before noon
    11-14: noon
    14-17: afternoon
    17-21: evening
    21-23: before bed
    23-7: night
    """
    if 7 <= hour < 11:
        return 'morning'
    elif 11 <= hour < 15:
        return 'noon'
    elif 15 <= hour < 19:
        return 'evening'
    elif 19 <= hour < 23:
        return 'before bed'
    else:  # 23-24 or 0-7
        return 'night'
    
def get_period_hours(period):
    """
    Get the number of hours for each period of day:
    morning (7-11): 4 hours
    noon (11-15): 4 hours
    evening (15-19): 4 hours
    before bed (19-23): 4 hours
    night (23-7): 8 hours
    """
    if period in ['morning', 'noon', 'evening', 'before bed']:
        return 4
    else:  # night
        return 8

def identify_glucose_events(df_data, glucose_threshold=12, lookback_hours=1, min_gap_hours=3, min_duration_hours=1):
    """
    Identify glucose excursion events with start and end points.
    
    Parameters:
    -----------
    df_data : pandas.DataFrame
        DataFrame with glucose data, insulin bolus data, and DateTime_rounded column
    glucose_threshold : float, default=12
        Glucose threshold (mmol/L) above which to look for events
    lookback_hours : int, default=1
        Hours to look back from high glucose to find preceding bolus
    min_gap_hours : int, default=3
        Minimum hours between event starts
    min_duration_hours : int, default=1
        Minimum duration (hours) before an event can end
    
    Returns:
    --------
    tuple: (df_modified, events_summary)
        df_modified: DataFrame with added 'event' column marking 'start' and 'end' events
        events_summary: DataFrame containing only the events for analysis
    """
    import pandas as pd
    
    print(f"Identifying high glucose events (>{glucose_threshold} mmol/L) and their preceding boluses...")
    
    # Make a copy and initialize the event column
    df_data_processed = df_data.copy()
    df_data_processed['event'] = None
    
    # Step 1: Find all moments where glucose is above threshold
    high_glucose_mask = df_data_processed['glucose'] > glucose_threshold
    high_glucose_moments = df_data_processed[high_glucose_mask].copy()
    
    print(f"Found {len(high_glucose_moments)} moments with glucose > {glucose_threshold} mmol/L")
    
    # Step 2: For each high glucose moment, find earliest bolus within lookback period
    # Ensure minimum gap between event starts
    events_found = 0
    last_event_start_time = None
    
    for idx, row in high_glucose_moments.iterrows():
        current_time = row['DateTime_rounded']
        time_window_start = current_time - pd.Timedelta(hours=lookback_hours)
        
        # Find bolus events in the lookback window
        time_window_mask = (
            (df_data_processed['DateTime_rounded'] >= time_window_start) & 
            (df_data_processed['DateTime_rounded'] < current_time)
        )
        
        bolus_mask = (
            (df_data_processed['carb_bolus'] > 0) | 
            (df_data_processed['correction_bolus'] > 0)
        )
        
        candidate_boluses = df_data_processed[time_window_mask & bolus_mask].copy()
        
        if len(candidate_boluses) > 0:
            earliest_bolus_idx = candidate_boluses['DateTime_rounded'].idxmin()
            earliest_bolus_time = df_data_processed.loc[earliest_bolus_idx, 'DateTime_rounded']
            
            # Check minimum gap between events
            if last_event_start_time is None or (earliest_bolus_time - last_event_start_time) >= pd.Timedelta(hours=min_gap_hours):
                df_data_processed.loc[earliest_bolus_idx, 'event'] = 'start'
                last_event_start_time = earliest_bolus_time
                events_found += 1
    
    print(f"Successfully identified {events_found} insulin bolus events preceding high glucose moments")
    
    # Step 3: For each start event, find when glucose returns to start level
    print("Identifying when glucose returns to start event glucose level...")
    
    start_events = df_data_processed[df_data_processed['event'] == 'start'].copy()
    start_times_and_glucose = [(row['DateTime_rounded'], row['glucose']) for _, row in start_events.iterrows()]
    start_times_and_glucose.sort()
    
    ends_found = 0
    
    for i, (start_time, start_glucose) in enumerate(start_times_and_glucose):
        # Determine the end of this event period (before next event or end of data)
        if i < len(start_times_and_glucose) - 1:
            period_end = start_times_and_glucose[i + 1][0]  # Next start time
        else:
            period_end = df_data_processed['DateTime_rounded'].max()
        
        # Get data for this event period (after minimum duration)
        minimum_end_time = start_time + pd.Timedelta(hours=min_duration_hours)
        
        period_mask = (
            (df_data_processed['DateTime_rounded'] >= minimum_end_time) & 
            (df_data_processed['DateTime_rounded'] < period_end) &
            (df_data_processed['glucose'].notna())
        )
        
        period_data = df_data_processed[period_mask].copy().sort_values('DateTime_rounded')
        
        if len(period_data) > 0:
            # Find first time glucose crosses back to or below start level
            crossing_mask = period_data['glucose'] <= start_glucose
            crossing_points = period_data[crossing_mask]
            
            if len(crossing_points) > 0:
                first_crossing_idx = crossing_points.index[0]
                df_data_processed.loc[first_crossing_idx, 'event'] = 'end'
                ends_found += 1
    
    print(f"Successfully identified {ends_found} end events")
    
    # Create events summary
    events_summary = df_data_processed[df_data_processed['event'].notna()].copy()
    
    if len(events_summary) > 0:
        print(f"\nEvent Summary:")
        print(f"Total events marked: {len(events_summary)}")
        print(f"Start events: {len(events_summary[events_summary['event'] == 'start'])}")
        print(f"End events: {len(events_summary[events_summary['event'] == 'end'])}")
        
        # Show event details
        display_columns = ['DateTime_rounded', 'glucose', 'carb_bolus', 'correction_bolus', 'event']
        print("\nFirst few events:")
        print(events_summary[display_columns].head(10).to_string(index=False))
    else:
        print("No events were marked - check if there are boluses within lookback period before high glucose moments")
    
    return df_data_processed, events_summary

