import requests
import time
import os
import pandas as pd
from datetime import datetime

# =====================================================
# 1. CONFIGURATION
# =====================================================
MB_BASE_URL = "https://mb.givadiva.co"
MB_USERNAME = "pramatheshray.ray@giva.co"
MB_PASSWORD = os.getenv("MB_PASSWORD")  # Pulled safely from GitHub Secrets
MB_CARD_ID = 22947

# Automatically grab today's date 
START_DATE = datetime.now().strftime("%d%b%y")

CT_ACCOUNT_ID = "R78-Z5K-847Z"
CT_PASSCODE = os.getenv("CT_PASSCODE")  # Pulled safely from GitHub Secrets
CT_REGION = "in1"
CT_ADMIN_EMAIL = "shah.neil@giva.co"
CT_CREATOR_NAME = "Pramathesh Ray"
CT_REPLACE_EXISTING = False

FILTERS_TO_PROCESS = [
    # P1 Filters

    # "A1-P1-New", "B1-P1-New", "A1-P1-<M4", "D2-P1-Dormant", "A2-P1-<M4", 
    # "A3-P1-<M4", "D1-P1-M7-12", "A2-P1-M4-6", "A1-P1-M4-6", "A3-P1-M4-6", 
    # "B3-P1-<M4", "B2-P1-<M4", "C1-P1-<M4", "B3-P1-M4-6", "B2-P1-M4-6",
    # # P2 Filters
    # "D3-P2-New", "D3-P2-<M4", "B1-P2-<M4", "A1-P2-New", "B1-P2-New", 
    # "A2-P2-Dormant", "A2-P2-M7-12", "D3-P2-M4-6", "B1-P2-M4-6", "A1-P2-<M4", 
    # "C1-P2-<M4", "B1-P2-Dormant", "A1-P2-M4-6", "A3-P2-Dormant", "A3-P2-M7-12", 
    # "A3-P2-<M4", "B3-P2-M7-12", "A1-P2-M7-12", "B2-P2-M7-12", "B2-P2-Dormant", 
    # "A1-P2-Dormant", "B3-P2-Dormant", "B2-P2-<M4", "A2-P2-<M4", "B3-P2-<M4", 
    # "A3-P2-M4-6", "B2-P2-M4-6", "A2-P2-M4-6", "B3-P2-M4-6",
    # # P3 Filters
    # "B1-P3-New", "A1-P3-New", "B1-P3-<M4", "D3-P3-<M4", "D3-P3-New", 
    # "B1-P3-Dormant", "B1-P3-M7-12", "B1-P3-M4-6", "D3-P3-M4-6", "A1-P3-<M4", 
    # "A3-P3-M7-12", "A1-P3-M4-6", "A1-P3-M7-12", "A1-P3-Dormant", "A2-P3-M7-12", 
    # "B2-P3-M7-12", "B3-P3-M7-12", "B3-P3-Dormant", "B2-P3-Dormant", "A2-P3-Dormant"

'B2-P2-M7-12',
'B3-P2-M7-12'
]

# =====================================================
# 2. CORE FUNCTIONS
# =====================================================
def mb_authenticate():
    resp = requests.post(
        f"{MB_BASE_URL}/api/session",
        json={"username": MB_USERNAME, "password": MB_PASSWORD},
        timeout=60,
    )
    resp.raise_for_status()
    return {"X-Metabase-Session": resp.json()["id"]}

def fetch_metabase_csv(headers, filter_val, output_file):
    if "-P1-" in filter_val:
        tag = "P1_Execution_Cohort"
    elif "-P2-" in filter_val:
        tag = "P2_Execution_Cohort"
    elif "-P3-" in filter_val:
        tag = "P3_Execution_Cohort"
    else:
        raise ValueError(f"Unknown tag for: {filter_val}")

    parameters = [
        {"type": "date/single", "target": ["variable", ["template-tag", "Start_date"]], "value": START_DATE},
        {"type": "category", "target": ["variable", ["template-tag", tag]], "value": [filter_val]}
    ]
    
    url = f"{MB_BASE_URL}/api/card/{MB_CARD_ID}/query/csv"
    resp = requests.post(url, headers=headers, json={"parameters": parameters}, stream=True, timeout=900)
    
    if resp.status_code != 200:
        raise RuntimeError(f"Query failed ({resp.status_code}): {resp.text[:500]}")

    with open(output_file, "wb") as f:
        for chunk in resp.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)

def transform_csv_for_clevertap(file_path):
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            return 0
            
        df = df.dropna(subset=['Customer_Phone'])
        df['type'] = 'i'
        df['identity'] = '+91' + df['Customer_Phone'].astype(str).str.replace('\.0$', '', regex=True)
        
        df_final = df[['type', 'identity']]
        df_final.to_csv(file_path, index=False)
        return len(df_final)
    except Exception as e:
        print(f"    ❌ Error transforming CSV: {e}")
        return -1

def upload_to_clevertap(file_path, segment_name):
    filename = os.path.basename(file_path)
    base_url = f"https://{CT_REGION}.api.clevertap.com"
    ct_headers = {
        'Content-Type': 'application/json',
        'X-CleverTap-Account-Id': CT_ACCOUNT_ID,
        'X-CleverTap-Passcode': CT_PASSCODE
    }

    res1 = requests.post(f"{base_url}/get_custom_list_segment_url", headers=ct_headers)
    if res1.status_code != 200 or res1.json().get("status") != "success":
        print(f"    ❌ CT Step 1 Failed: {res1.text}")
        return False
    presigned_url = res1.json().get("presignedS3URL")

    with open(file_path, 'rb') as file_data:
        res2 = requests.put(presigned_url, data=file_data)
    if res2.status_code != 200:
        print(f"    ❌ CT Step 2 Failed: {res2.text}")
        return False

    payload = {
        "name": segment_name,
        "email": CT_ADMIN_EMAIL,
        "filename": filename,
        "creator": CT_CREATOR_NAME,
        "url": presigned_url,
        "replace": CT_REPLACE_EXISTING
    }
    res3 = requests.post(f"{base_url}/upload_custom_list_segment_completed", json=payload, headers=ct_headers)
    
    if res3.status_code == 200 and res3.json().get("status") == "success":
        print(f"    ✅ Segment '{segment_name}' created (ID: {res3.json().get('Segment ID')})")
        return True
    else:
        print(f"    ❌ CT Step 3 Failed: {res3.text}")
        return False

# =====================================================
# 3. MAIN LOOP
# =====================================================
# =====================================================
# 3. MAIN LOOP
# =====================================================
def run_pipeline():
    print("🔐 Authenticating with Metabase...")
    try:
        mb_headers = mb_authenticate()
    except Exception as e:
        print(f"❌ Metabase authentication failed: {e}")
        return
        
    print(f"🚀 Starting Pipeline for {len(FILTERS_TO_PROCESS)} cohorts. As-of Date: {START_DATE}\n")
    
    for filter_val in FILTERS_TO_PROCESS:
        print(f"--------------------------------------------------")
        print(f"⚙️ Processing Cohort: {filter_val}")
        segment_name = f"{START_DATE}_{filter_val}"
        temp_csv = f"{filter_val}_temp.csv"
        
        try:
            print("    ⬇️ Fetching data from Metabase...")
            fetch_metabase_csv(mb_headers, filter_val, temp_csv)
            
            print("    🧹 Reformatting CSV for CleverTap...")
            row_count = transform_csv_for_clevertap(temp_csv)
            
            if row_count > 0:
                print(f"    📤 Uploading {row_count:,} rows to CleverTap...")
                upload_to_clevertap(temp_csv, segment_name)
            elif row_count == 0:
                print("    ⚠️ 0 rows returned. Skipping upload.")
        except Exception as e:
            print(f"    ❌ Pipeline failed for {filter_val}: {e}")
            
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
            
        print("    ⏸️ Sleeping for 5 seconds...")
        time.sleep(5)
        
    print("\n🎉 Pipeline Complete!")

if __name__ == "__main__":
    run_pipeline()

if __name__ == "__main__":
    run_pipeline()
