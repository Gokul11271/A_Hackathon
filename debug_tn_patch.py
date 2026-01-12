import pandas as pd
import streamlit as st
import requests
from utils.data_loader import load_data, load_district_geojson

# Mock st.cache_data to run as script
if not hasattr(st, 'cache_data'):
   def cache_data(func):
       return func
   st.cache_data = cache_data

def check_tn_mismatches():
    # Load Data (using the logic in data_loader which already has some mappings)
    # We pass the filename directly to trigger the override logic if needed, 
    # but since load_data is hardcoded to switch to combined... let's just use it.
    print("Loading Data...")
    df = load_data("aadhaar_data.csv")
    
    # Filter for Tamil Nadu
    # Note: State name in CSV might be "Tamil Nadu" or "Tamilnadu" etc. 
    # The loader standardizes strict ones, but let's check unique states first.
    tn_variations = [s for s in df['State'].unique() if 'Tamil' in s]
    print(f"Tamil Nadu variations in data: {tn_variations}")
    
    if not tn_variations:
        print("No Tamil Nadu data found!")
        return

    tn_df = df[df['State'].isin(tn_variations)]
    csv_districts = set(tn_df['District'].unique())
    print(f"\nCSV Districts ({len(csv_districts)}):")
    print(sorted(list(csv_districts)))

    # Load GeoJSON
    print("\nLoading GeoJSON...")
    geojson = load_district_geojson()
    if not geojson:
        print("Failed to load GeoJSON")
        return

    # Extract TN districts from GeoJSON
    # The renderer uses 'st_nm' or 'NAME_1' for state matching.
    # In the provided map_renderer, it looks for properties.st_nm == geo_state_name
    
    # Let's find what the GeoJSON calls Tamil Nadu
    feature_states = set()
    for f in geojson['features']:
        p = f['properties']
        st = p.get('st_nm') or p.get('NAME_1')
        if st and 'Tamil' in st:
            feature_states.add(st)
    
    with open("debug_tn_results.txt", "w", encoding="utf-8") as f:
        f.write(f"GeoJSON State Name matching 'Tamil': {feature_states}\n")
        
        # Restore Logic
        geo_districts = set()
        for feature in geojson['features']:
            p = feature['properties']
            st_nm = p.get('st_nm') or p.get('NAME_1')
            if st_nm in feature_states:
                dist = p.get('district') or p.get('NAME_2')
                if dist:
                    geo_districts.add(dist)
                    
        f.write(f"\nGeoJSON Districts ({len(geo_districts)}):\n")
        f.write(str(sorted(list(geo_districts))) + "\n")

        # Mismatches
        f.write("\n--- MISMATCHES ---\n")
        in_csv_not_geo = csv_districts - geo_districts
        in_geo_not_csv = geo_districts - csv_districts
        
        f.write(f"In CSV but NOT in GeoJSON (Problematic for map): {len(in_csv_not_geo)}\n")
        for d in sorted(list(in_csv_not_geo)):
            f.write(f" - {d}\n")

        f.write(f"\nIn GeoJSON but NOT in CSV (Potential matches): {len(in_geo_not_csv)}\n")
        for d in sorted(list(in_geo_not_csv)):
            f.write(f" - {d}\n")
            
    print("Done writing to debug_tn_results.txt")

if __name__ == "__main__":
    check_tn_mismatches()
