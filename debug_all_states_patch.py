import pandas as pd
import streamlit as st
import json
from utils.data_loader import load_data, load_district_geojson

# Mock st.cache_data
if not hasattr(st, 'cache_data'):
   def cache_data(func):
       return func
   st.cache_data = cache_data

def check_all_mismatches():
    print("Loading Data...")
    df = load_data("aadhaar_data.csv")
    geojson = load_district_geojson()
    
    if df.empty or not geojson:
        print("Data load failed.")
        return

    # Get all unique states from CSV
    states = sorted(df['State'].unique())
    
    results = {}
    
    print(f"Scanning {len(states)} states for mismatches...")
    
    for state in states:
        # Get CSV districts for this state
        csv_districts = set(df[df['State'] == state]['District'].dropna().unique())
        
        # Get GeoJSON districts for this state
        # We need to match the state name in GeoJSON
        # The data_loader maps CSV State -> GeoState. Let's use that if available, 
        # but here we are using the raw df returned by load_data which has 'GeoState'.
        geo_state_name = df[df['State'] == state]['GeoState'].iloc[0]
        
        geo_districts = set()
        for f in geojson['features']:
            p = f['properties']
            st_nm = p.get('st_nm') or p.get('NAME_1')
            
            # Simple match or check aliases if needed (but GeoState should match GeoJSON key)
            if st_nm == geo_state_name:
                dist = p.get('district') or p.get('NAME_2')
                if dist:
                    geo_districts.add(dist)
        
        if not geo_districts:
            print(f"WARNING: No GeoJSON districts found for state '{state}' (GeoState: '{geo_state_name}')")
            continue
            
        # Compare
        in_csv_not_geo = csv_districts - geo_districts
        
        if in_csv_not_geo:
            results[state] = list(in_csv_not_geo)
            
    # Write Report
    with open("all_states_mismatch_report.txt", "w", encoding="utf-8") as f:
        f.write("=== DISTRICT MISMATCH REPORT (CSV -> GeoJSON) ===\n")
        f.write("These districts exist in Data but NOT in Map (causing patches).\n\n")
        
        for state, mismatches in results.items():
            f.write(f"State: {state} ({len(mismatches)} mismatches)\n")
            for m in sorted(mismatches):
                f.write(f" - {m}\n")
            f.write("\n")
            
    print("Report generated: all_states_mismatch_report.txt")

if __name__ == "__main__":
    check_all_mismatches()
