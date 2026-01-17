
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
    Optimized for memory usage by avoiding excessive copies and full sorts.
    """
    recs = []
    
    # Filter data first - reduce columns immediately to what is needed
    needed_cols = [
        'State', 'District', 'PinCode', 'City', 
        'Enrolment', 'Updates', 
        'bio_age_5_17', 'bio_age_17_', 
        'age_0_5', 'demo_age_17_', 'age_18_greater'
    ]
    # Handle missing cols gracefully
    existing_cols = [c for c in needed_cols if c in df.columns]
    
    # Pre-filter
    if state_filter and state_filter != "All India":
        subset = df[df['State'] == state_filter][existing_cols].copy()
    elif district_filter:
        subset = df[df['District'] == district_filter][existing_cols].copy()
    else:
        # If All India, we might be hitting memory limits with full copy. 
        # Just use reference if possible or strict subset.
        subset = df[existing_cols].copy() 

    if subset.empty:
        return []

    # --- ANALYSIS 1: LOW BIOMETRIC COMPLIANCE (District Level) ---
    # Group by District to find underperforming areas
    dist_group = subset.groupby(['State', 'District'])[['Enrolment', 'Updates', 'bio_age_5_17', 'bio_age_17_']].sum().reset_index()

    dist_group['Total_Activity'] = dist_group['Enrolment'] + dist_group['Updates']
    dist_group['Bio_Rate'] = (dist_group['bio_age_5_17'] + dist_group['bio_age_17_']) / dist_group['Total_Activity']
    
    # Threshold: If Bio Rate is in bottom 15% and Activity is decent (>100 ops), flag it.
    valid_dists = dist_group[dist_group['Total_Activity'] > 100]
    if not valid_dists.empty:
        # Optimization: use nsmallest instead of full sort
        laggards = valid_dists.nsmallest(5, 'Bio_Rate')
        
        for _, row in laggards.iterrows():
            recs.append(Recommendation(
                title="Critical: Low Mandatory Biometric Updates",
                description=f"Biometric update rate is only {row['Bio_Rate']:.1%}, significantly below average. Children turning 5 or 15 may be missing mandatory updates.",
                district=row['District'],
                severity="High",
                metric_val=row['Bio_Rate'],
                action_item="Launch 'Aadhaar Camp' in schools targeting 5-15 year olds."
            ))

    # --- ANALYSIS 2: HIGH LOAD CENTRES (PinCode Level) ---
    if 'PinCode' in subset.columns:
        # Grouping by 4 columns can be expensive on large data.
        # Simplify: Group by PinCode first, then join metadata if needed or just take first.
        # Aggregation
        pin_group = subset.groupby(['PinCode'])[['Enrolment', 'Updates']].sum()
        
        # We need City and District for the report. 
        # Let's get mapping from original subset (drop duplicates to save memory)
        meta_map = subset[['PinCode', 'District', 'City']].drop_duplicates('PinCode').set_index('PinCode')
        
        pin_group = pin_group.join(meta_map)
        pin_group = pin_group.reset_index()

        pin_group['Load'] = pin_group['Enrolment'] + pin_group['Updates']
        
        # High Load Threshold -> Top 5 directly
        if not pin_group.empty:
            high_load_pins = pin_group.nlargest(5, 'Load')
            
            for _, row in high_load_pins.iterrows():
                recs.append(Recommendation(
                    title="Service Overload: High Traffic Zone",
                    description=f"PinCode {row['PinCode']} ({row['City']}) handled {int(row['Load'])} transactions. Existing centers may be overcrowded.",
                    district=row['District'],
                    pincode=row['PinCode'],
                    severity="Medium",
                    metric_val=int(row['Load']),
                    action_item="Deploy additional temporary processing terminals or mobile vans."
                ))

            # --- ANALYSIS 3: "GHOST" VILLAGES ---
            # Logic: Enrolment > 200, Updates = 0
            ghosts = pin_group[(pin_group['Enrolment'] > 200) & (pin_group['Updates'] == 0)]
            if not ghosts.empty:
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

            # --- ANALYSIS 4: INFANT ENROLMENT HUBS ---
            if 'age_0_5' in subset.columns:
                 # Re-grouping for age specific might be needed if not in pin_group
                 infant_group = subset.groupby('PinCode')['age_0_5'].sum().reset_index()
                 infant_group = infant_group.join(meta_map, on='PinCode')
                 
                 hubs = infant_group.nlargest(3, 'age_0_5')
                 
                 for _, row in hubs.iterrows():
                    recs.append(Recommendation(
                        title="High Infant Enrolment Zone (0-5 Years)",
                        description=f"Pin {row['PinCode']} shows high volume of new child enrolments ({int(row['age_0_5'])}). Likely a residential growth area or near major hospitals.",
                        district=row['District'],
                        pincode=row['PinCode'],
                        severity="Medium",
                        metric_val=int(row['age_0_5']),
                        action_item="Partner with local Maternity Hospitals for immediate birth-enrolment integration."
                    ))

    # --- ANALYSIS 5: WORKFORCE MIGRATION INDICATORS ---
    if 'demo_age_17_' in subset.columns and 'age_18_greater' in subset.columns:
        mig_group = subset.groupby(['PinCode'])[['demo_age_17_', 'age_18_greater']].sum()
        # Filter for significant volume
        mig_group = mig_group[mig_group['demo_age_17_'] > 50].copy()
        
        if not mig_group.empty:
            mig_group['Migration_Index'] = mig_group['demo_age_17_'] / (mig_group['age_18_greater'] + 1)
            mig_group = mig_group.join(meta_map)
            
            mig_hotspots = mig_group.nlargest(3, 'Migration_Index')
            
            for _, row in mig_hotspots.iterrows():
                 recs.append(Recommendation(
                    title="Potential Migration Hub Detected",
                    description=f"Demographic updates are {row['Migration_Index']:.1f}x higher than new adult enrolments in Pin {row.name}. Suggests heavy workforce migration/address changes.", # Index is PinCode
                    district=row['District'],
                    pincode=row.name,
                    severity="Medium",
                    metric_val=round(row['Migration_Index'], 2),
                    action_item="Setup special 'Address Update Camps' for migrant workers on weekends."
                ))

    # --- FALLBACK: GENERAL AWARENESS (Ensure Marquee is never empty) ---
    if len(recs) < 5:
        defaults = [
            Recommendation(
                title="Mandatory Biometric Update",
                description="Children attaining age 5 and 15 must update their biometrics to ensure Aadhaar validity.",
                district="All India",
                severity="High",
                action_item="Visit nearest Aadhaar Seva Kendra."
            ),
            Recommendation(
                title="Keep Mobile Updated",
                description="Link your active mobile number with Aadhaar for seamless OTP authentication and online services.",
                district="General",
                severity="Medium",
                action_item="Update mobile number at enrollment center."
            ),
            Recommendation(
                title="Prevent Fraud",
                description="Never share your Aadhaar OTP or stick biometrics on unauthorized forms. locking biometrics is recommended.",
                district="Security",
                severity="High",
                action_item="Use 'Lock Biometrics' feature in mAadhaar app."
            ),
             Recommendation(
                title="Document Update",
                description="Citizens who enrolled >10 years ago should update POI and POA documents.",
                district="Compliance",
                severity="Medium",
                action_item="Upload documents online at myAadhaar portal."
            )
        ]
        # Append defaults to fill the gap
        recs.extend(defaults[:5 - len(recs)])

    return recs


