import sqlite3
import os
import pandas as pd
import pytz
import requests
import time
from datetime import datetime

XDRIP_PATH = ['./xDrip/export20250831-192101/export20250831-192101.sqlite',
    '/xDrip/export20250903-113335/export20250903-113335.sqlite']
DIABETESM_PATH = './Diabetesm/DiabetesM_ENTRIES.csv'
# === NIGHTSCOUT CONFIGURATION ===
NIGHTSCOUT_URL = "https://samince.eu.nightscoutpro.com/"  # e.g. "https://mycgm.herokuapp.com"
API_SECRET = ""  # leave "" if not required
OUTPUT_DB = "nightscout_data.sqlite"

# === NIGHTSCOUT PARAMETERS ===
BATCH_SIZE = 1000000

def read_xDrip(table_name = 'BgReadings', xdrip_paths = XDRIP_PATH):
    ''' Reads a specified table from xDrip SQLite databases and returns it as a DataFrame. 
    Handles multiple database paths, resolves overlaps by prioritizing higher index paths.
    Tables found in database:
    -------------------------
    1. android_metadata
    2. DesertSync
    3. sqlite_sequence
    4. Libre2Sensors
    5. BloodTest
    6. ActiveBgAlert
    7. Sensors
    8. TransmitterData
    9. CalibrationSendQueue
    10. Prediction
    11. BgSendQueue
    12. ActiveBluetoothDevice
    13. PebbleMovement
    14. UserErrors
    15. Libre2RawValue2
    16. Notifications
    17. Reminder
    18. HeartRate
    19. CalibrationRequest
    20. PenData
    21. Treatments
    22. APStatus
    23. LibreBlock
    24. Accuracy
    25. SensorSendQueue
    26. Calibration
    27. LibreData
    28. AlertType
    29. BgReadings
    30. UploaderQueue'''
    
    all_dataframes = []
    
    # Read from each path in the list
    for i, xdrip_path in enumerate(xdrip_paths):
        if os.path.exists(xdrip_path):
            print(f"Reading from path {i}: {xdrip_path}")
            # Connect to the database
            conn = sqlite3.connect(xdrip_path)

            try:
                df_table = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                
                if table_name=='BgReadings':
                    df_table['Sensor Reading(mmol/L)'] = df_table['raw_data']/1000/18
                    # Convert timestamp to datetime (xDrip uses milliseconds since epoch)
                    df_table['datetime'] = pd.to_datetime(df_table['timestamp'], unit='ms', utc=True).dt.tz_convert(pytz.timezone('EET'))
                    
                    df_table = df_table.set_index('datetime').resample('5min').agg({
                            'Sensor Reading(mmol/L)': 'mean'  # Take average of glucose values in each 5-min window
                        }).dropna()
                    df_table = df_table.reset_index()
                    df_table['DateTime_rounded'] = df_table['datetime'].dt.floor('5min')
                    df_table = df_table[['DateTime_rounded', 'Sensor Reading(mmol/L)']]
                
                # Add source path index for overlap resolution
                df_table['source_index'] = i
                all_dataframes.append(df_table)
                print(f"  Successfully read {len(df_table)} records")

            except Exception as e:
                print(f"  Error reading table {table_name} from {xdrip_path}: {e}")
                continue

            finally:
                # Close connection
                conn.close()
        else:
            print(f"SQLite file not found: {xdrip_path}")
    
    # If no data was read from any path
    if not all_dataframes:
        print("No data could be read from any xDrip database!")
        return pd.DataFrame()
    
    # Combine all dataframes
    combined_df = pd.concat(all_dataframes, ignore_index=True)
    
    # Handle overlaps by keeping entries from higher index paths
    if table_name == 'BgReadings':
        # Sort by DateTime_rounded and source_index (higher index = higher priority)
        combined_df = combined_df.sort_values(['DateTime_rounded', 'source_index'])
        
        # Remove duplicates, keeping the last occurrence (highest source_index)
        combined_df = combined_df.drop_duplicates(subset=['DateTime_rounded'], keep='last')
        
        # Remove the helper column and sort by datetime
        combined_df = combined_df.drop('source_index', axis=1).sort_values('DateTime_rounded').reset_index(drop=True)
        
        print(f"Final combined dataset: {len(combined_df)} records after overlap resolution")
    else:
        # For non-BgReadings tables, just remove the source_index column
        combined_df = combined_df.drop('source_index', axis=1)
    
    return combined_df
    
def read_diabetesm(diabetesm_path = DIABETESM_PATH):
    ''' Reads DiabetesM CSV file and returns it as a DataFrame. '''
    if os.path.exists(diabetesm_path):
        try:
            df = pd.read_csv(diabetesm_path, skiprows=1)  # Skip first row with metadata
            df = df[~df['DateTimeFormatted'].astype(str).str.startswith('00')]
            df['DateTimeFormatted'] = pd.to_datetime(df['DateTimeFormatted']).dt.tz_localize(pytz.timezone('EET'))
            df['DateTime_rounded'] = df['DateTimeFormatted'].dt.round('5min')
            # we have garbage in the file before that and we need to use archived file before garbage import
            
            return df
        except Exception as e:
            print(f"  Error reading DiabetesM file: {e}")
            return pd.DataFrame()  # Return empty DataFrame on error
    else:
        print("DiabetesM CSV file not found!")
        return pd.DataFrame()  # Return empty DataFrame if file not found
    
def prepare_diabetesm():
    current_data = read_diabetesm()
    current_data = current_data[current_data['DateTime_rounded']>=pd.Timestamp('2025-08-25 08:45:00+03:00')]  # Filter for entries after Jan 1, 2023

    archived_data = read_diabetesm(r'c:/Users/nadia/Documents/Food/Diabetesm/DiabetesM_ENTRIES_to_20250825.csv')
    
    all_data = pd.concat([archived_data, current_data], ignore_index=True).sort_values('DateTime_rounded').reset_index(drop=True)
    return all_data



def download_nightscout_data(start_date=None):
    """
    Download Nightscout data.
    
    Args:
        start_date (datetime, optional): Start date for data download. If None, downloads all data.
    
    Returns:
        pd.DataFrame: DataFrame containing the downloaded entries
    """
    # Convert datetime to Unix milliseconds if provided
    start_date_ms = None
    if start_date:
        if isinstance(start_date, datetime):
            start_date_ms = int(start_date.timestamp() * 1000)
    
    headers = {}
    if API_SECRET:
        headers["API-SECRET"] = API_SECRET

    all_count = 0
    skip = 0
    done = False

    print("Starting Nightscout download...")
    df_output = pd.DataFrame()
    while not done:
        url = f"{NIGHTSCOUT_URL}/api/v1/entries.json?count={BATCH_SIZE}&skip={skip}"
        if start_date_ms:
            url += f"&find[date][$gte]={start_date_ms}"

        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text}")
            break

        entries = r.json()
        if not entries:
            print("No more data found.")
            break

        df_batch = pd.json_normalize(entries)
        df_batch['Sensor Reading(mmol/L)'] = df_batch['sgv']/18
        df_batch['datetime']= pd.to_datetime(df_batch['date'], unit='ms', utc=True).dt.tz_convert('EET')
        df_batch = df_batch.set_index('datetime').resample('5min').agg({
                            'Sensor Reading(mmol/L)': 'mean'  # Take average of glucose values in each 5-min window
                        }).dropna()
        df_batch = df_batch.reset_index()
        df_batch['DateTime_rounded'] = df_batch['datetime'].dt.floor('5min')
        df_batch = df_batch[['DateTime_rounded', 'Sensor Reading(mmol/L)']]
        df_output = pd.concat([df_output, df_batch], ignore_index=True)

        all_count += len(entries)
        skip += len(entries)

        print(f"Downloaded {len(entries)} entries, total {all_count}")

        # If fewer than batch size returned → end reached
        if len(entries) < BATCH_SIZE:
            done = True

        time.sleep(0.2)  # be nice to server
    return df_output

def create_nightscout_db(start_date=None):
    """
    Download Nightscout data and save to SQLite database.
    
    Args:
        start_date (datetime, optional): Start date for data download. If None, downloads all data.
    """
    # Convert datetime to Unix milliseconds if provided
    start_date_ms = None
    if start_date:
        if isinstance(start_date, datetime):
            start_date_ms = int(start_date.timestamp() * 1000)
        else:
            raise ValueError("start_date must be a datetime object")
    
    # Connect to SQLite
    conn = sqlite3.connect(OUTPUT_DB)
    cur = conn.cursor()

    # Create table for glucose entries
    cur.execute("""
    CREATE TABLE IF NOT EXISTS entries (
        _id TEXT PRIMARY KEY,
        device TEXT,
        date INTEGER,
        dateString TEXT,
        sgv INTEGER,
        direction TEXT,
        type TEXT,
        filtered REAL,
        unfiltered REAL,
        rssi INTEGER
    )
    """)
    conn.commit()

    headers = {}
    if API_SECRET:
        headers["API-SECRET"] = API_SECRET

    all_count = 0
    skip = 0
    done = False

    print("Starting Nightscout download...")

    while not done:
        url = f"{NIGHTSCOUT_URL}/api/v1/entries.json?count={BATCH_SIZE}&skip={skip}"
        if start_date_ms:
            url += f"&find[date][$gte]={start_date_ms}"

        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            print(f"Error {r.status_code}: {r.text}")
            break

        entries = r.json()
        if not entries:
            print("No more data found.")
            break

        # Insert batch into SQLite
        for e in entries:
            cur.execute("""
            INSERT OR IGNORE INTO entries
            (_id, device, date, dateString, sgv, direction, type, filtered, unfiltered, rssi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                e.get("_id"),
                e.get("device"),
                e.get("date"),
                e.get("dateString"),
                e.get("sgv"),
                e.get("direction"),
                e.get("type"),
                e.get("filtered"),
                e.get("unfiltered"),
                e.get("rssi")
            ))

        conn.commit()
        all_count += len(entries)
        skip += len(entries)

        print(f"Downloaded {len(entries)} entries, total {all_count}")

        # If fewer than batch size returned → end reached
        if len(entries) < BATCH_SIZE:
            done = True

        time.sleep(0.2)  # be nice to server

    print(f"/n✅ Finished! Total entries saved: {all_count}")
    print(f"SQLite database saved to: {OUTPUT_DB}")

    conn.close()