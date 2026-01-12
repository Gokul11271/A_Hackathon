import indiapins

def test_pincodes():
    test_pins = ['110001', '600028', '560001', '400001']
    
    print(f"Testing indiapins library...")
    try:
        for pin in test_pins:
            # help(indiapins) might be needed if docs are scarce, but let's guess simple API or print dir
            print(f"\n--- PIN: {pin} ---")
            # Based on library name, likely has a function like matching(pin) or find(pin)
            # The search result said "retrieve places... for specific Indian pincodes"
            # Let's try to inspect the module first
            pass
            
        print("\nModule attributes:")
        print(dir(indiapins))
        
        # Taking a guess at the API based on common patterns
        if hasattr(indiapins, 'matching'):
            print(f"Result for 110001: {indiapins.matching('110001')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pincodes()
