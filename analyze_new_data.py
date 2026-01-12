import pandas as pd
import numpy as np

def analyze():
    print("Loading combined_full_Q1_Jan_Apr.csv...")
    # Load only necessary columns to identify rows
    df = pd.read_csv("combined_full_Q1_Jan_Apr.csv", low_memory=False)
    
    print("Columns:", df.columns.tolist())
    print("\nTotal Rows:", len(df))
    
    # Check header rows or dirty data
    print("\nSample State values:", df['state'].unique()[:20])
    print("Sample District values:", df['district'].unique()[:20])
    
    # Check if '100000' is common
    invalid_rows = df[df['state'].astype(str).str.isnumeric()]
    print(f"\nRows with numeric State: {len(invalid_rows)}")
    if not invalid_rows.empty:
        print(invalid_rows.head())

    # Check for NaN in measure columns
    measure_cols = ['age_0_5', 'age_5_17', 'age_18_greater', 'bio_age_5_17', 'bio_age_17_', 'demo_age_5_17', 'demo_age_17_']
    print("\nNull counts:")
    print(df[measure_cols].isnull().sum())

if __name__ == "__main__":
    analyze()
