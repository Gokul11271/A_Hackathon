import requests

def check_state_geojson():
    url = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
    data = requests.get(url).json()
    states = sorted([f['properties']['ST_NM'] for f in data['features']])
    print("States in India GeoJSON:")
    for s in states:
        print(s)

if __name__ == "__main__":
    check_state_geojson()
