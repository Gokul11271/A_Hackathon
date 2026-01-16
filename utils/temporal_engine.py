
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

class TemporalEngine:
    METRO_DISTRICTS = [
        # Delhi NCR
        "New Delhi", "Central", "North", "South", "East", "West", "North West", "South West", "North East", "Shahdara", "South East",
        "Gurgaon", "Gurugram", "Faridabad", "Noida", "Gautam Buddha Nagar", "Ghaziabad",
        
        # Mumbai Region
        "Mumbai", "Mumbai Suburban", "Greater Bombay", "Thane", "Palghar", "Raigad",
        
        # Bangalore
        "Bangalore Urban", "Bengaluru Urban", "Bangalore Rural", "Bengaluru Rural",
        
        # Chennai
        "Chennai", "Kancheepuram", "Chengalpattu", "Tiruvallur",
        
        # Hyderabad
        "Hyderabad", "Rangareddy", "Medchal Malkajgiri", "Sangareddy",
        
        # Kolkata
        "Kolkata", "Howrah", "North 24 Parganas", "South 24 Parganas", "Hooghly",
        
        # Others (Tier 1)
        "Pune", "Ahmedabad", "Surat", "Jaipur", "Lucknow", "Kanpur", "Nagpur", "Indore", "Patna", "Bhopal"
    ]

    def __init__(self, df):
        self.df = df.copy()
        
    def get_metro_trends(self):
        """
        Analyzes trends specifically for major Metros vs Non-Metros.
        Returns a DataFrame aggregated by Month for visualization.
        """
        # Flag rows
        self.df['Region_Type'] = np.where(self.df['District'].isin(self.METRO_DISTRICTS), 'Metro', 'Non-Metro')
        
        if 'MonthOrder' not in self.df.columns or 'Month' not in self.df.columns:
            return pd.DataFrame() # Cannot analyze without time info
            
        # Group by Month and Region Type
        # We use MonthOrder to sort correctly, but display Month name
        grouped = self.df.groupby(['Region_Type', 'Month', 'MonthOrder'])[['Updates', 'Enrolment']].sum().reset_index()
        grouped = grouped.sort_values('MonthOrder')
        
        return grouped

    def detect_peak_periods(self, metro_trend_df):
        """
        Identifies peak demand months for Metros.
        Returns a list of dicts describing peaks.
        """
        if metro_trend_df.empty:
            return []
            
        metro_only = metro_trend_df[metro_trend_df['Region_Type'] == 'Metro'].copy()
        
        # Calculate Threshold (e.g., 90th percentile of monthly volume)
        threshold = metro_only['Updates'].quantile(0.90)
        
        peaks = metro_only[metro_only['Updates'] >= threshold]
        
        peak_info = []
        for _, row in peaks.iterrows():
            peak_info.append({
                "Month": row['Month'],
                "Volume": row['Updates'],
                "Type": "Update Surge",
                "Recommendation": f"Scale infrastructure by 20% in {row['Month']} to handle peak demand."
            })
            
        return peak_info

    def plot_metro_comparison(self, trend_df):
        """
        Generates a Plotly chart comparing Metro vs Non-Metro trends.
        """
        if trend_df.empty:
            return None
            
        fig = px.line(
            trend_df, 
            x="Month", 
            y="Updates", 
            color="Region_Type", 
            markers=True,
            title="Monthly Update Trends: Metro vs Non-Metro",
            color_discrete_map={"Metro": "#FF5733", "Non-Metro": "#33C1FF"},
            labels={"Updates": "Volume of Updates"}
        )
        fig.update_layout(xaxis=dict(tickmode='linear'), hovermode="x unified")
        return fig
