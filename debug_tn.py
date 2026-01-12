import requests
import json

def list_tn_districts():
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        data = requests.get(url).json()
        tn_districts = []
        for f in data['features']:
            p = f['properties']
            if p.get('NAME_1') == "Tamil Nadu":
                tn_districts.append(p.get('NAME_2'))
        
        print(f"Found {len(tn_districts)} districts in Tamil Nadu:")
        for d in sorted(tn_districts):
            print(d)
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    list_tn_districts()
