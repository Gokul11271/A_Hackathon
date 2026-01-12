import requests
import json

def inspect():
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    print(f"Loading GeoJSON from {url}...")
    try:
        resp = requests.get(url)
        # Debug: Print first 100 chars
        print(f"First 100 chars: {resp.text[:100]}")
        data = resp.json()
    except Exception as e:
        print(f"Failed: {e}")
        return

    print(f"Total Features: {len(data['features'])}")
    
    # Check first feature keys
    if data['features']:
        print("Keys in properties:", data['features'][0]['properties'].keys())
    
    # Collect all state names
    all_states = set()
    for f in data['features']:
        props = f['properties']
        # Try common keys
        s = props.get('NAME_1') or props.get('st_nm') or props.get('ST_NM') or props.get('state_name')
        if s:
            all_states.add(s)
            
    print("\n--- All Unique State Names Found ---")
    for s in sorted(list(all_states)):
        print(s)

if __name__ == "__main__":
    inspect()
