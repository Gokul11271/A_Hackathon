import pandas as pd
import requests
import json

def compare():
    # Load CSV
    df = pd.read_csv("d:/AadharHackathon/aadhaar_data.csv")
    csv_districts = sorted(df[df['State'] == "Tamil Nadu"]['District'].unique())
    
    # Load GeoJSON
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        resp = requests.get(url)
        data = resp.json()
    except Exception as e:
        print(f"GeoJSON Load Fail: {e}")
        return

    json_districts = []
    for f in data['features']:
        props = f['properties']
        s_name = props.get('NAME_1') or props.get('st_nm') or props.get('ST_NM')
        if s_name == "Tamil Nadu":
            # District key usually NAME_2 or district
            d_name = props.get('NAME_2') or props.get('district')
            if d_name:
                json_districts.append(d_name)
    
    json_districts = sorted(json_districts)
    
    print("\n--- CSV Districts (Tamil Nadu) ---")
    print(csv_districts)
    print(f"Count: {len(csv_districts)}")

    print("\n--- GeoJSON Districts (Tamil Nadu) ---")
    print(json_districts)
    print(f"Count: {len(json_districts)}")
    
    # Find mismatches
    missing_in_json = set(csv_districts) - set(json_districts)
    print("\n--- Missing in GeoJSON (Present in CSV) ---")
    print(missing_in_json)

if __name__ == "__main__":
    compare()
