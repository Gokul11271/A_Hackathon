
import pandas as pd
from utils.data_loader import load_data
from utils.analysis_engine import get_recommendations

try:
    print("Loading data...")
    df = load_data("d:/AadharHackathon/aadhaar_data.csv")
    print(f"Data loaded. Shape: {df.shape}")
    
    print("Generating recommendations for 'All India'...")
    recs = get_recommendations(df, state_filter="All India")
    
    print(f"Number of recommendations: {len(recs)}")
    for r in recs:
        print(f" - {r.title} ({r.severity})")
        
except Exception as e:
    print(f"Error: {e}")
