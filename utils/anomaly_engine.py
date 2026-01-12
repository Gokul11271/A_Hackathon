
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from scipy.stats import zscore, chisquare
from scipy.spatial.distance import jensenshannon

class AnomalyEngine:
    def __init__(self, data):
        self.df = data.copy()
        
    def detect_volume_anomalies(self, region_type='District'):
        """
        Detects volume-based anomalies using Isolation Forest and Z-Score.
        Returns a DataFrame with 'Anomaly_Score' and 'Anomaly_Type'.
        """
        # Group by Region
        grouped = self.df.groupby(region_type)[['Enrolment', 'Updates']].sum().reset_index()
        
        # 1. Isolation Forest (Multivariate Outlier Detection)
        iso = IsolationForest(contamination=0.05, random_state=42)
        grouped['Iso_Score'] = iso.fit_predict(grouped[['Enrolment', 'Updates']])
        
        # 2. Z-Score (Univariate Extreme Values)
        grouped['Z_Enrolment'] = zscore(grouped['Enrolment'])
        grouped['Z_Updates'] = zscore(grouped['Updates'])
        
        # Flagging
        # Iso_Score = -1 means anomaly
        anomalies = grouped[
            (grouped['Iso_Score'] == -1) | 
            (abs(grouped['Z_Enrolment']) > 2.5) | 
            (abs(grouped['Z_Updates']) > 2.5)
        ].copy()
        
        anomalies['Reason'] = np.where(
            anomalies['Z_Enrolment'] > 2.5, "Extreme High Enrolment",
            np.where(anomalies['Z_Enrolment'] < -2.5, "Extreme Low Enrolment",
            np.where(anomalies['Z_Updates'] > 2.5, "Extreme High Updates",
            "Complex Pattern Anomaly"))
        )
        return anomalies

    def detect_age_structure_anomalies(self, region_type='District', min_volume=100):
        """
        Detects anomalies in age distribution using Jensen-Shannon Divergence 
        from the dataset average.
        """
        if 'age_0_5' not in self.df.columns:
            return pd.DataFrame()

        # Group and filter low volume
        grouped = self.df.groupby(region_type)[['age_0_5', 'age_5_17', 'age_18_greater']].sum().reset_index()
        grouped['Total'] = grouped[['age_0_5', 'age_5_17', 'age_18_greater']].sum(axis=1)
        grouped = grouped[grouped['Total'] > min_volume].copy()
        
        # Calculate Proportions
        cols = ['age_0_5', 'age_5_17', 'age_18_greater']
        probs = grouped[cols].div(grouped['Total'], axis=0).fillna(0)
        
        # Calculate "Average" distribution of the entire dataset
        avg_dist = self.df[cols].sum() / self.df[cols].sum().sum()
        avg_prob = avg_dist.values
        
        # Calculate Distance (JS Divergence or simple Chi-Sq like distance)
        # Using simple Sum of Squared Differences for speed and interpretability or JS
        # JS is better for probability distributions
        
        def calculate_js(row):
            return jensenshannon(row.values, avg_prob)

        grouped['Structure_Divergence'] = probs.apply(calculate_js, axis=1)
        
        # Top 5% most divergent
        threshold = grouped['Structure_Divergence'].quantile(0.95)
        anomalies = grouped[grouped['Structure_Divergence'] > threshold].sort_values('Structure_Divergence', ascending=False)
        
        anomalies['Reason'] = "Abnormal Age Distribution"
        return anomalies

    def detect_spatial_anomalies(self, state_col='State', district_col='District'):
        """
        Detects districts that behave significantly differently from their state peers.
        Uses Modified Z-score relative to State Average.
        """
        stats = []
        
        # Iterate per state to find local outliers
        for state in self.df[state_col].unique():
            state_data = self.df[self.df[state_col] == state]
            dist_data = state_data.groupby(district_col)[['Enrolment', 'Updates']].sum().reset_index()
            
            if len(dist_data) < 3:
                continue # Need at least 3 districts to find an outlier
                
            median_enrol = dist_data['Enrolment'].median()
            # MAD (Median Absolute Deviation)
            mad_enrol = (dist_data['Enrolment'] - median_enrol).abs().median()
            
            if mad_enrol == 0:
                continue
                
            # Modified Z-Score: 0.6745 * (x - median) / MAD
            dist_data['Mod_Z_Enrol'] = 0.6745 * (dist_data['Enrolment'] - median_enrol) / mad_enrol
            
            # Anomaly Threshold > 3.5
            outliers = dist_data[dist_data['Mod_Z_Enrol'].abs() > 3.5].copy()
            if not outliers.empty:
                outliers['State'] = state
                outliers['Reason'] = "Spatial Outlier (vs State Peers)"
                stats.append(outliers)
                
        if stats:
            return pd.concat(stats)
        return pd.DataFrame()
