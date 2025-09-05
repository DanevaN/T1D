import pandas as pd
import numpy as np
def analyze_hypoglycemia_treatment(data):
        
    # Analyze hypoglycemia episodes and subsequent carb treatments
    print("HYPOGLYCEMIA TREATMENT ANALYSIS")
    print("="*50)

    # Find all hypoglycemic episodes
    hypoglycemia_threshold = 4.5
    hypo_episodes = []

    # Sort data by datetime to ensure proper sequence
    data_sorted = data.sort_values('DateTime_rounded').reset_index(drop=True)

    # Find hypoglycemic episodes
    for i, row in data_sorted.iterrows():
        if row['glucose'] < hypoglycemia_threshold:
            # Look ahead at following rows (next 2 hours or 24 readings)
            max_lookhead = min(i + 24, len(data_sorted))  # Look ahead up to 24 readings (~2 hours)
            following_data = data_sorted.iloc[i+1:max_lookhead].copy()
            
            # check if there is IOB at start if yes ignore this hypo episode
            if row['IOB_novorapid'] > 0.1:
                continue
            
            if len(following_data) > 0:
                # Check if there's no bolus in the following period
                no_bolus = (
                    (following_data['carb_bolus'].fillna(0) == 0).all() and
                    (following_data['correction_bolus'].fillna(0) == 0).all() and
                    (following_data['extended_bolus'].fillna(0) == 0).all()
                )
                
                # Check if there are carbs in the following period
                #carbs_given = following_data['carbs'].fillna(0).sum()
                COB_start = following_data.iloc[0]['COB']
                COB_end = following_data.iloc[-1]['COB']
                carbs_given = following_data['carbs'].fillna(0).sum() 
                has_carbs = carbs_given > 0
                
                if no_bolus and has_carbs:
                    # Find max glucose in following period
                    valid_glucose = following_data['glucose'].dropna()
                    if len(valid_glucose) > 0:
                        max_glucose_after = valid_glucose.max()
                        max_glucose_time = following_data.loc[following_data['glucose'] == max_glucose_after, 'DateTime_rounded'].iloc[0]
                        
                        # Calculate glucose difference
                        glucose_difference = max_glucose_after - row['glucose']
                        
                        # Find when carbs were given
                        carb_amount = following_data['carbs'].fillna(0).sum() + COB_start - COB_end

                        hypo_episodes.append({
                            'hypo_datetime': row['DateTime_rounded'],
                            'hypo_glucose': row['glucose'],
                            'period_of_day': row['period_of_day'],
                            'carbs_given': carbs_given,
                            'AoC': carb_amount,
                            'max_glucose_after': max_glucose_after,
                            'max_glucose_time': max_glucose_time,
                            'glucose_difference': glucose_difference,
                            'time_to_peak': (max_glucose_time - row['DateTime_rounded']).total_seconds() / 60,  # minutes
                            'recovery_ratio': glucose_difference / carb_amount if carb_amount > 0 else 0  # glucose rise per gram of carbs
                        })

    # Create DataFrame
    df_hypo_treatment = pd.DataFrame(hypo_episodes)

    print(f"Found {len(df_hypo_treatment)} hypoglycemic episodes with carb treatment (no bolus):")
    print("="*70)

    if len(df_hypo_treatment) > 0:
        # Display the results
        print(df_hypo_treatment[['hypo_datetime', 'hypo_glucose', 'period_of_day', 'carbs_given', 
                                'max_glucose_after', 'glucose_difference', 'time_to_peak', 'recovery_ratio']].round(2))
        
        print(f"\nSUMMARY STATISTICS:")
        print("="*30)
        print(f"Average carbs given: {df_hypo_treatment['carbs_given'].mean():.1f}g")
        print(f"Average glucose at hypo: {df_hypo_treatment['hypo_glucose'].mean():.1f} mmol/L")
        print(f"Average max glucose after: {df_hypo_treatment['max_glucose_after'].mean():.1f} mmol/L")
        print(f"Average glucose rise: {df_hypo_treatment['glucose_difference'].mean():.1f} mmol/L")
        print(f"Average time to peak: {df_hypo_treatment['time_to_peak'].mean():.0f} minutes")
        print(f"Average recovery ratio: {df_hypo_treatment['recovery_ratio'].mean():.3f} mmol/L per gram")
        
        print(f"\nTREATMENT EFFECTIVENESS:")
        print("="*30)
        
        # Analyze by carb amount ranges
        df_hypo_treatment['carb_range'] = pd.cut(df_hypo_treatment['carbs_given'], 
                                            bins=[0, 15, 30, 100], 
                                            labels=['Low (≤15g)', 'Medium (15-30g)', 'High (>30g)'])
        
        if not df_hypo_treatment['carb_range'].isna().all():
            treatment_analysis = df_hypo_treatment.groupby('carb_range').agg({
                'glucose_difference': 'mean',
                'time_to_peak': 'mean',
                'recovery_ratio': 'mean',
                'hypo_glucose': 'count'
            }).round(2)
            treatment_analysis.columns = ['Avg_Glucose_Rise', 'Avg_Time_to_Peak', 'Recovery_Ratio', 'Count']
            print(treatment_analysis)
        
        # Analyze by period of day
        print(f"\nBY PERIOD OF DAY:")
        print("="*20)
        period_analysis = df_hypo_treatment.groupby('period_of_day').agg({
            'carbs_given': 'mean',
            'glucose_difference': 'mean',
            'recovery_ratio': 'mean',
            'hypo_glucose': 'count'
        }).round(2)
        period_analysis.columns = ['Avg_Carbs', 'Avg_Glucose_Rise', 'Recovery_Ratio', 'Count']
        print(period_analysis)
        
        # Show detailed examples
        print(f"\nDETAILED EXAMPLES (first 5 episodes):")
        print("="*40)
        for idx, episode in df_hypo_treatment.head().iterrows():
            print(f"\nEpisode {idx + 1}:")
            print(f"  Time: {episode['hypo_datetime']}")
            print(f"  Period: {episode['period_of_day']}")
            print(f"  Hypo glucose: {episode['hypo_glucose']:.1f} mmol/L")
            print(f"  Carbs given: {episode['carbs_given']:.1f}g")
            print(f"  Max glucose reached: {episode['max_glucose_after']:.1f} mmol/L")
            print(f"  Glucose rise: {episode['glucose_difference']:.1f} mmol/L")
            print(f"  Time to peak: {episode['time_to_peak']:.0f} minutes")
            print(f"  Recovery efficiency: {episode['recovery_ratio']:.3f} mmol/L per gram")

    else:
        print("No hypoglycemic episodes found with carb treatment (no bolus) in the following 2 hours.")

    # Save the DataFrame for further analysis
    print(f"\nDataFrame 'df_hypo_treatment' created with {len(df_hypo_treatment)} episodes")
    return {'df_hypo_treatment': df_hypo_treatment, 'period_analysis': period_analysis if len(df_hypo_treatment) > 0 else pd.DataFrame()}