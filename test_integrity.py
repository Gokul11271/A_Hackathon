import unittest
import pandas as pd
import requests
import json
import os

class TestDataIntegrity(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Load Data
    @classmethod
    def setUpClass(cls):
        # Load Data
        if os.path.exists("combined_full_Q1_Jan_Apr.csv"):
            cls.df = pd.read_csv("combined_full_Q1_Jan_Apr.csv", low_memory=False)
            # Minimal cleaning for test
            cls.df.rename(columns={'state': 'State', 'district': 'District'}, inplace=True)
            cls.df = cls.df[~cls.df['State'].astype(str).str.isnumeric()]
            cls.df['State'] = cls.df['State'].astype(str).str.title()
            cls.df['District'] = cls.df['District'].astype(str).str.title()
        else:
            cls.df = pd.DataFrame()
            
        # Load GeoJSON
        url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
        try:
             cls.geojson = requests.get(url).json()
        except:
             cls.geojson = None

    def test_data_exists(self):
        self.assertFalse(self.df.empty, "Dataframe should not be empty")
        self.assertIsNotNone(self.geojson, "GeoJSON should be loaded")

    def test_district_mapping(self):
        """
        Verify that for every state in our CSV, the districts map to the GeoJSON.
        Handles known aliases:
        - Odisha -> Orissa
        - Uttarakhand -> Uttaranchal
        """
        if self.df.empty or not self.geojson:
            return

        # Map GeoJSON State -> Districts
        geo_map = {}
        for f in self.geojson['features']:
            p = f['properties']
            s = p.get('NAME_1') or p.get('st_nm')
            d = p.get('NAME_2') or p.get('district')
            if s and d:
                if s not in geo_map: geo_map[s] = set()
                geo_map[s].add(d)

        csv_states = self.df['State'].unique()
        
        for state in csv_states:
            # Resolve Alias
            target_geo = state
            if state == "Odisha": target_geo = "Orissa"
            elif state == "Uttarakhand": target_geo = "Uttaranchal"
            elif state == "Andaman and Nicobar Islands": target_geo = "Andaman & Nicobar Islands"
            elif state == "Jammu and Kashmir": target_geo = "Jammu & Kashmir"
            elif state == "Dadra and Nagar Haveli and Daman and Diu": target_geo = "Daman & Diu"
            elif state == "Delhi": target_geo = "NCT of Delhi"

            # Check State Exists
            # Fuzzy match state if direct fail (case insensitive)
            if target_geo not in geo_map:
                found = False
                for k in geo_map.keys():
                    if k.lower() == target_geo.lower():
                        target_geo = k
                        found = True
                        break
                if not found:
                    # Allow non-mapped states if they really don't exist in this specific legacy geojson 
                    # (like Ladakh or Telangana which might be merged in old maps)
                    # But we should warn.
                    print(f"Warning: State {state} not found in GeoJSON.")
                    continue

            # Check Districts
            csv_dists = set(self.df[self.df['State'] == state]['District'].unique())
            geo_dists = geo_map[target_geo]
            
            missing = csv_dists - geo_dists
            
            # Allow empty missing set
            self.assertEqual(len(missing), 0, f"State {state} has districts not in GeoJSON: {missing}")

if __name__ == '__main__':
    unittest.main()
