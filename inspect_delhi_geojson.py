import requests
import json

if __name__ == "__main__":
    urls = [
        "https://raw.githubusercontent.com/udit-001/india-maps-data/master/india/delhi-districts.json",
        "https://raw.githubusercontent.com/udit-001/india-maps-data/master/districts/delhi.json",
        "https://raw.githubusercontent.com/Anujarya300/IndiaMaps/master/Districts/Delhi_Districts.json"
    ]
    
    for url in urls:
        print(f"Checking: {url}")
        try:
            r = requests.get(url)
            if r.status_code == 200:
                print("  SUCCESS!")
                try:
                    data = r.json()
                    print(f"  Feature Check: {len(data.get('features', []))} features")
                except:
                    print("  Failed to parse JSON")
            else:
                print(f"  Failed: {r.status_code}")
        except Exception as e:
            print(f"  Error: {e}")






