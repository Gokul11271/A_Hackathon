import requests
import json

def check_geojson():
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        print("Fetching GeoJSON...")
        response = requests.get(url)
        data = response.json()
        print(f"Total features: {len(data['features'])}")
        
        # Check first feature properties
        if data['features']:
            print("Sample Properties:", data['features'][0]['properties'])
            
        # Find Karnataka features
        karnataka_districts = []
        state_key = None
        dist_key = None
        
        # Attempt to identify keys
        props = data['features'][0]['properties']
        keys = props.keys()
        print(f"Available keys: {keys}")
        
        for feature in data['features']:
            p = feature['properties']
            # Heuristic to find state key
            s_val = p.get('NAME_1') or p.get('st_nm') or p.get('STATE')
            d_val = p.get('NAME_2') or p.get('district') or p.get('DISTRICT')
            
            if s_val == "Karnataka":
                karnataka_districts.append(d_val)
                
        print(f"\nFound {len(karnataka_districts)} districts in Karnataka:")
        print(karnataka_districts[:20])
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_geojson()
