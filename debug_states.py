import requests
import json

def list_problem_states():
    target_states = [
        "Andhra Pradesh", "Assam", "Delhi", "Haryana", "Himachal Pradesh", 
        "Jammu and Kashmir", "Jharkhand", "Lakshadweep", "Manipur", "Sikkim",
        "Tripura", "Uttar Pradesh", "Uttaranchal"
    ]
    
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        data = requests.get(url).json()
        state_dists = {k: [] for k in target_states}
        
        for f in data['features']:
            p = f['properties']
            # Normalization
            s_name = p.get('NAME_1') or p.get('st_nm')
            if s_name in target_states:
                d_name = p.get('NAME_2') or p.get('district')
                state_dists[s_name].append(d_name)
        
        with open("debug_states_out.txt", "w", encoding="utf-8") as f:
            for s in target_states:
                f.write(f"\n--- {s} ---\n")
                f.write(str(sorted(state_dists[s])) + "\n")
        print("Done writing to debug_states_out.txt")
            
    except Exception as e:
        print(e)

if __name__ == "__main__":
    list_problem_states()
