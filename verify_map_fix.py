import requests
import json

def verify():
    print("Loading District GeoJSON...")
    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        response = requests.get(url)
        response.raise_for_status()
        district_geojson = response.json()
    except Exception as e:
        print(f"Failed to load GeoJSON: {e}")
        return

    test_cases = [
        "Andaman & Nicobar",
        "Odisha",
        "Jammu & Kashmir",
        "Uttarakhand",
        "Dadra and Nagar Haveli and Daman and Diu",
        "Maharashtra" # Control case
    ]

    state_name_mapping = {
        "Andaman & Nicobar": "Andaman and Nicobar",
        "Jammu & Kashmir": "Jammu and Kashmir",
        "Odisha": "Orissa",
        "Uttarakhand": "Uttaranchal",
        "Dadra and Nagar Haveli and Daman and Diu": ["Dadra and Nagar Haveli", "Daman and Diu"]
    }

    print("\n--- Verification Results ---")
    all_passed = True
    for geo_state_name in test_cases:
        target_names = state_name_mapping.get(geo_state_name, geo_state_name)
        if not isinstance(target_names, list):
            target_names = [target_names]
            
        filtered_features = [
            f for f in district_geojson['features'] 
            if (f['properties'].get('st_nm') in target_names or f['properties'].get('NAME_1') in target_names)
        ]
        
        count = len(filtered_features)
        status = "PASS" if count > 0 else "FAIL"
        if count == 0: all_passed = False
        print(f"State: '{geo_state_name}' -> Targets: {target_names} | Features Found: {count} [{status}]")

    if all_passed:
        print("\nSUCCESS: All test cases found matching features.")
    else:
        print("\nFAILURE: Some states did not match.")

if __name__ == "__main__":
    verify()
