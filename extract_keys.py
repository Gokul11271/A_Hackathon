
import requests
import pandas as pd
import sys

def main():
    try:
        # Load GeoJSON Names
        print("Loading GeoJSON...")
        geo_url = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
        geo_data = requests.get(geo_url).json()
        geo_names = sorted([f['properties']['ST_NM'] for f in geo_data['features']])
        
        # Load CSV Names
        print("Loading CSV...")
        df = pd.read_csv('combined_full_Q1_Jan_Apr.csv', low_memory=False)
        # Mimic the cleaning in data_loader
        df.rename(columns={'state': 'State'}, inplace=True)
        csv_names = sorted(df['State'].dropna().astype(str).unique().tolist())
        
        with open('debug_keys.txt', 'w', encoding='utf-8') as f:
            f.write("GEOJSON_KEYS:\n")
            for n in geo_names:
                f.write(f"{n}\n")
            f.write("\nCSV_KEYS:\n")
            for n in csv_names:
                f.write(f"{n}\n")
                
        print("Keys written to debug_keys.txt")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
