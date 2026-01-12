import pandas as pd
import requests
import json

def check_all_districts():
    print("Loading Real Data (combined_full_Q1_Jan_Apr.csv)...")
    try:
        df = pd.read_csv("combined_full_Q1_Jan_Apr.csv", low_memory=False)
        # Apply same cleaning as data_loader
        df.rename(columns={'state': 'State', 'district': 'District'}, inplace=True)
        df = df[~df['State'].astype(str).str.isnumeric()]
        df['State'] = df['State'].astype(str).str.title()
        df['District'] = df['District'].astype(str).str.title()
        
        # State Mappings
        replace_map = {
            "Odisha": "Orissa", 
            "Uttarakhand": "Uttaranchal",
            "Delhi": "NCT of Delhi",
            "Andaman And Nicobar Islands": "Andaman & Nicobar Islands",
            "Jammu And Kashmir": "Jammu & Kashmir",
            "Dadra And Nagar Haveli And Daman And Diu": "Daman & Diu"
        }
        df['State'] = df['State'].replace(replace_map)
        
    except FileNotFoundError:
        print("CSV not found.")
        return

    print("Loading GeoJSON...")
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        geo_data = requests.get(url).json()
    except Exception as e:
        print(f"Failed to load GeoJSON: {e}")
        return

    # Build a dictionary of State -> Set of Districts from GeoJSON
    geojson_map = {}
    for feature in geo_data['features']:
        props = feature['properties']
        state = props.get('NAME_1') or props.get('st_nm') or props.get('state_name')
        dist = props.get('NAME_2') or props.get('district')
        
        if state and dist:
            # Normalize state name for matching (e.g. mismatch in spacing or case)
            # We'll use the CSV states as the 'source of truth' for the loop, 
            # but we need to match them to GeoJSON states.
            if state not in geojson_map:
                geojson_map[state] = set()
            geojson_map[state].add(dist)

    # Check differences
    csv_states = sorted(df['State'].unique())
    
    with open("final_mismatch_report.txt", "w", encoding="utf-8") as f:
        f.write("--- Mismatch Report ---\n")
        
        for state in csv_states:
            # Try to find matching state in GeoJSON
            # Exact match first
            geo_state = state
            if state not in geojson_map:
                # Try simple fuzzy or known aliases
                if state == "Andaman and Nicobar Islands": geo_state = "Andaman & Nicobar Islands"
                elif state == "Delhi": geo_state = "NCT of Delhi"
                elif state == "Jammu and Kashmir": geo_state = "Jammu & Kashmir"
                elif state == "Dadra and Nagar Haveli and Daman and Diu": geo_state = "Daman & Diu" # GeoJSON might look diff
                elif state == "Uttarakhand": geo_state = "Uttaranchal"
                else:
                    # Try finding case insensitive
                    for k in geojson_map.keys():
                        if k.lower() == state.lower():
                            geo_state = k
                            break
            
            if geo_state not in geojson_map:
                f.write(f"!! State '{state}' NOT FOUND in GeoJSON !!\n")
                continue
                
            csv_dists = set(df[df['State'] == state]['District'].unique())
            geo_dists = geojson_map[geo_state]
            
            # Check for districts in CSV but NOT in GeoJSON (these will show as gray/blank on map)
            missing = csv_dists - geo_dists
            if missing:
                f.write(f"\nState: {state} (GeoJSON match: {geo_state})\n")
                f.write(f"  Missing IDs (In CSV but not Map): {sorted(list(missing))}\n")
                # f.write(f"  Available in Map (Sample): {list(geo_dists)[:5]}\n")

    print("Checking Complete. See final_mismatch_report.txt")

if __name__ == "__main__":
    check_all_districts()
