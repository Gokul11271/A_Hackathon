import pandas as pd
try:
    import pgeocode
    print("pgeocode imported successfully.")
    nomi = pgeocode.Nominatim('in')
    res = nomi.query_postal_code("110001")
    print(f"Result for 110001: {res.to_dict()}")
except ImportError:
    print("pgeocode NOT found.")
except Exception as e:
    print(f"Error: {e}")
