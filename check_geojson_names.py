import requests
import json

def check_url(url, name):
    print(f"--- Checking {name} ---")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        st_nm_values = set()
        name_1_values = set()
        
        for feature in data['features']:
            props = feature['properties']
            # Different GeoJSONs use different keys
            if 'ST_NM' in props: st_nm_values.add(props['ST_NM'])
            if 'st_nm' in props: st_nm_values.add(props['st_nm'])
            if 'NAME_1' in props: name_1_values.add(props['NAME_1'])
                
        if st_nm_values:
            print("Unique ST_NM/st_nm values:")
            for n in sorted(list(st_nm_values)):
                print(f"  '{n}'")
        if name_1_values:
            print("Unique NAME_1 values:")
            for n in sorted(list(name_1_values)):
                print(f"  '{n}'")
            
    except Exception as e:
        print(f"Error: {e}")

url_dist = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
url_state = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"

check_url(url_dist, "DISTRICT GEOJSON")
check_url(url_state, "STATE GEOJSON")
