import pgeocode
import pandas as pd

def check_pincodes():
    nomi = pgeocode.Nominatim('in')
    
    test_pins = ['110001', '600028', '560001', '400001']
    print(f"Querying: {test_pins}")
    
    # query_postal_code returns a Series for single, or DataFrame for list
    results = nomi.query_postal_code(test_pins)
    
    print("\nResults Columns:")
    print(results.columns.tolist())
    
    print("\nData:")
    print(results[['postal_code', 'place_name', 'state_name', 'county_name', 'community_name']])

if __name__ == "__main__":
    check_pincodes()
