
import pandas as pd
import numpy as np

class Recommendation:
    def __init__(self, title, description, district, pincode=None, severity="Medium", metric_val=0, action_item=""):
        self.title = title
        self.description = description
        self.district = district
        self.pincode = pincode
        self.severity = severity  # High, Medium, Low
        self.metric_val = metric_val
        self.action_item = action_item

    def to_dict(self):
        return {
            "Title": self.title,
            "Description": self.description,
            "District": self.district,
            "PinCode": self.pincode if self.pincode else "District-Wide",
            "Severity": self.severity,
            "Metric": self.metric_val,
            "Action By User": self.action_item
        }

def calculate_compliance_metrics(df):
    """
    Calculates Update Compliance Ratios.
    Ratio = (Biometric Updates) / (Total Activity)
    Lower ratio suggests residents are not coming back for mandatory updates.
    """
    # Avoid division by zero
    df['Total_Activity'] = df['Enrolment'] + df['Updates']
    
    # Mandatory Update Ratio (Focus on 5-17 age group updates vs total activity)
    # This is a proxy: If a district has lots of enrollment but zero bio updates, it's a red flag.
    df['Bio_Update_Compliance'] = np.where(
        df['Total_Activity'] > 0,
        (df['bio_age_5_17'] + df['bio_age_17_']) / df['Total_Activity'],
        0
    )
    return df

def get_recommendations(df, state_filter=None, district_filter=None):
    """
    Generates a list of Recommendation objects based on analysis.
    """
    recs = []
    
    # Filter data first
    subset = df.copy()
    if state_filter and state_filter != "All India":
        subset = subset[subset['State'] == state_filter]
    if district_filter:
        subset = subset[subset['District'] == district_filter]

    if subset.empty:
        return []

    # --- ANALYSIS 1: LOW BIOMETRIC COMPLIANCE (District Level) ---
    # Group by District to find underperforming areas
    dist_group = subset.groupby(['State', 'District']).agg({
        'Enrolment': 'sum',
        'Updates': 'sum',
        'bio_age_5_17': 'sum',
        'bio_age_17_': 'sum'
    }).reset_index()

    dist_group['Total_Activity'] = dist_group['Enrolment'] + dist_group['Updates']
    dist_group['Bio_Rate'] = (dist_group['bio_age_5_17'] + dist_group['bio_age_17_']) / dist_group['Total_Activity']
    
    # Threshold: If Bio Rate is in bottom 15% and Activity is decent (>100 ops), flag it.
    valid_dists = dist_group[dist_group['Total_Activity'] > 100]
    if not valid_dists.empty:
        threshold = valid_dists['Bio_Rate'].quantile(0.15)
        
        laggards = valid_dists[valid_dists['Bio_Rate'] <= threshold].sort_values('Bio_Rate')
        
        for _, row in laggards.head(5).iterrows():
            recs.append(Recommendation(
                title="Critical: Low Mandatory Biometric Updates",
                description=f"Biometric update rate is only {row['Bio_Rate']:.1%}, significantly below average. Children turning 5 or 15 may be missing mandatory updates.",
                district=row['District'],
                severity="High",
                metric_val=row['Bio_Rate'],
                action_item="Launch 'Aadhaar Camp' in schools targeting 5-15 year olds."
            ))

    # --- ANALYSIS 2: HIGH LOAD CENTRES (PinCode Level) ---
    # Identify PinCodes with massive enrolment volume but potentially outdated infrastructure (inferred)
    # or simply requiring more support.
    
    # We look for PinCodes contributing to top 10% of volume in their State
    if 'PinCode' in subset.columns:
        pin_group = subset.groupby(['State', 'District', 'PinCode', 'City'])[['Enrolment', 'Updates']].sum().reset_index()
        pin_group['Load'] = pin_group['Enrolment'] + pin_group['Updates']
        
        # High Load Threshold
        load_threshold = pin_group['Load'].quantile(0.95)
        high_load_pins = pin_group[pin_group['Load'] > load_threshold].sort_values('Load', ascending=False)
        
        for _, row in high_load_pins.head(5).iterrows():
            recs.append(Recommendation(
                title="Service Overload: High Traffic Zone",
                description=f"PinCode {row['PinCode']} ({row['City']}) handled {int(row['Load'])} transactions. Existing centers may be overcrowded.",
                district=row['District'],
                pincode=row['PinCode'],
                severity="Medium",
                metric_val=int(row['Load']),
                action_item="Deploy additional temporary processing terminals or mobile vans."
            ))

    # --- ANALYSIS 3: "GHOST" VILLAGES (High Enrolment, Zero Updates) ---
    # Places where people enrolled initially but never came back. 
    # Logic: Enrolment > 50, Updates = 0
    ghosts = pin_group[(pin_group['Enrolment'] > 200) & (pin_group['Updates'] == 0)]
    for _, row in ghosts.head(3).iterrows():
        recs.append(Recommendation(
            title="Engagement Gap: 'Ghost' Activity",
            description=f"Significant enrolments ({row['Enrolment']}) but ZERO subsequent updates in Pin {row['PinCode']}.",
            district=row['District'],
            pincode=row['PinCode'],
            severity="High",
            metric_val=0,
            action_item="Conduct door-to-door survey or local awareness drive regarding data correction."
        ))

    # --- ANALYSIS 4: INFANT ENROLMENT HUBS (Social Impact / Integration) ---
    # Identify areas with high birth-registration activity (Age 0-5).
    # Recommendation: Integrate with Maternity Hospitals.
    if 'age_0_5' in subset.columns and 'PinCode' in subset.columns:
        # Group by PinCode
        infant_group = subset.groupby(['District', 'PinCode', 'City'])['age_0_5'].sum().reset_index()
        infant_threshold = infant_group['age_0_5'].quantile(0.95) # Top 5%
        
        hubs = infant_group[infant_group['age_0_5'] > infant_threshold].sort_values('age_0_5', ascending=False)
        
        for _, row in hubs.head(3).iterrows():
            recs.append(Recommendation(
                title="High Infant Enrolment Zone (0-5 Years)",
                description=f"Pin {row['PinCode']} shows high volume of new child enrolments ({int(row['age_0_5'])}). Likely a residential growth area or near major hospitals.",
                district=row['District'],
                pincode=row['PinCode'],
                severity="Medium",
                metric_val=int(row['age_0_5']),
                action_item="Partner with local Maternity Hospitals for immediate birth-enrolment integration."
            ))

    # --- ANALYSIS 5: WORKFORCE MIGRATION INDICATORS (Originality) ---
    # Logic: High Demographic Updates (Address changes) vs Low New Enrolments (Adults).
    # If Demo Updates > 2 * New Enrolment (18+), it suggests population shift, not natural growth.
    if 'demo_age_17_' in subset.columns and 'age_18_greater' in subset.columns:
        mig_group = subset.groupby(['District', 'PinCode', 'City']).agg({
            'demo_age_17_': 'sum',
            'age_18_greater': 'sum'
        }).reset_index()
        
        # Filter for significant volume
        mig_group = mig_group[mig_group['demo_age_17_'] > 50]
        
        # Calculate Ratio
        mig_group['Migration_Index'] = mig_group['demo_age_17_'] / (mig_group['age_18_greater'] + 1)
        
        # If Ratio > 3 (3x more updates than new adults), it's a migration hotspot
        mig_hotspots = mig_group[mig_group['Migration_Index'] > 3.0].sort_values('Migration_Index', ascending=False)
        
        for _, row in mig_hotspots.head(3).iterrows():
             recs.append(Recommendation(
                title="Potential Migration Hub Detected",
                description=f"Demographic updates are {row['Migration_Index']:.1f}x higher than new adult enrolments in Pin {row['PinCode']}. Suggests heavy workforce migration/address changes.",
                district=row['District'],
                pincode=row['PinCode'],
                severity="Medium",
                metric_val=round(row['Migration_Index'], 2),
                action_item="Setup special 'Address Update Camps' for migrant workers on weekends."
            ))

    return recs
