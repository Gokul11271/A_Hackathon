"""
Analytics Engine for Dashboard Insights
Provides trend analysis, growth calculations, and auto-generated insights
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class AnalyticsEngine:
    def __init__(self, df):
        self.df = df
        
    def calculate_trends(self, metric_df, metric='Enrolment'):
        """
        Calculate trend indicators for KPI cards
        Returns: dict with current value, previous value, change %, trend direction
        """
        if 'datestamp' not in metric_df.columns or metric_df.empty:
            return None
            
        # Sort by date
        sorted_df = metric_df.sort_values('datestamp')
        
        # Get unique dates
        dates = sorted_df['datestamp'].unique()
        if len(dates) < 2:
            return None
            
        # Split into current and previous period
        mid_point = len(dates) // 2
        current_dates = dates[mid_point:]
        previous_dates = dates[:mid_point]
        
        current_value = sorted_df[sorted_df['datestamp'].isin(current_dates)][metric].sum()
        previous_value = sorted_df[sorted_df['datestamp'].isin(previous_dates)][metric].sum()
        
        if previous_value == 0:
            change_pct = 0
        else:
            change_pct = ((current_value - previous_value) / previous_value) * 100
            
        return {
            'current': current_value,
            'previous': previous_value,
            'change_pct': change_pct,
            'trend': 'up' if change_pct > 0 else 'down' if change_pct < 0 else 'stable',
            'sparkline_data': sorted_df.groupby('datestamp')[metric].sum().values
        }
    
    def calculate_growth_rates(self, df, group_by='State'):
        """
        Calculate growth rates for regions
        """
        if 'datestamp' not in df.columns:
            return pd.DataFrame()
            
        # Group by region and date
        grouped = df.groupby([group_by, 'datestamp'])[['Enrolment', 'Updates']].sum().reset_index()
        
        # Calculate growth for each region
        growth_data = []
        for region in grouped[group_by].unique():
            region_data = grouped[grouped[group_by] == region].sort_values('datestamp')
            
            if len(region_data) < 2:
                continue
                
            first_val = region_data['Enrolment'].iloc[0]
            last_val = region_data['Enrolment'].iloc[-1]
            
            if first_val > 0:
                growth_rate = ((last_val - first_val) / first_val) * 100
            else:
                growth_rate = 0
                
            growth_data.append({
                group_by: region,
                'Growth_Rate': growth_rate,
                'First_Value': first_val,
                'Last_Value': last_val
            })
            
        return pd.DataFrame(growth_data)
    
    def generate_insights(self, df, location='All India'):
        """
        Auto-generate insights from data patterns
        """
        insights = []
        
        # 1. Top performer
        state_totals = df.groupby('State')['Enrolment'].sum().sort_values(ascending=False)
        if not state_totals.empty:
            top_state = state_totals.index[0]
            top_value = state_totals.iloc[0]
            insights.append({
                'type': 'success',
                'title': '🏆 Top Performer',
                'message': f"{top_state} leads with {top_value:,.0f} enrolments",
                'priority': 1
            })
        
        # 2. Growth trend
        if 'datestamp' in df.columns:
            growth_df = self.calculate_growth_rates(df)
            if not growth_df.empty:
                fastest_growing = growth_df.nlargest(1, 'Growth_Rate').iloc[0]
                if fastest_growing['Growth_Rate'] > 0:
                    insights.append({
                        'type': 'info',
                        'title': '📈 Fastest Growth',
                        'message': f"{fastest_growing['State']} grew by {fastest_growing['Growth_Rate']:.1f}%",
                        'priority': 2
                    })
        
        # 3. Update compliance
        total_enrol = df['Enrolment'].sum()
        total_updates = df['Updates'].sum()
        if total_enrol > 0:
            update_rate = (total_updates / total_enrol) * 100
            if update_rate < 20:
                insights.append({
                    'type': 'warning',
                    'title': '⚠️ Low Update Rate',
                    'message': f"Only {update_rate:.1f}% update compliance - consider awareness campaigns",
                    'priority': 3
                })
            else:
                insights.append({
                    'type': 'success',
                    'title': '✅ Good Compliance',
                    'message': f"{update_rate:.1f}% update rate across {location}",
                    'priority': 3
                })
        
        # 4. Demographic insights
        age_0_5 = df['age_0_5'].sum()
        age_5_17 = df['age_5_17'].sum()
        age_18_plus = df['age_18_greater'].sum()
        total_age = age_0_5 + age_5_17 + age_18_plus
        
        if total_age > 0:
            child_pct = ((age_0_5 + age_5_17) / total_age) * 100
            if child_pct > 40:
                insights.append({
                    'type': 'info',
                    'title': '👶 Young Population',
                    'message': f"{child_pct:.1f}% are children (0-17) - plan for future demand",
                    'priority': 4
                })
        
        # 5. Biometric update gap
        bio_updates = (df['bio_age_5_17'] + df['bio_age_17_']).sum()
        demo_updates = (df['demo_age_5_17'] + df['demo_age_17_']).sum()
        
        if demo_updates > 0 and bio_updates < demo_updates * 0.5:
            insights.append({
                'type': 'warning',
                'title': '🔐 Biometric Gap',
                'message': f"Biometric updates lag behind demographic updates - security concern",
                'priority': 2
            })
        
        # Sort by priority
        insights.sort(key=lambda x: x['priority'])
        
        return insights[:5]  # Return top 5 insights
    
    def get_time_series_data(self, df, metric='Enrolment', group_by=None):
        """
        Prepare time-series data for trend charts
        """
        if 'datestamp' not in df.columns:
            return pd.DataFrame()
            
        if group_by:
            ts_data = df.groupby(['datestamp', group_by])[metric].sum().reset_index()
        else:
            ts_data = df.groupby('datestamp')[metric].sum().reset_index()
            
        return ts_data.sort_values('datestamp')
    
    def calculate_benchmarks(self, df, region, metric='Enrolment'):
        """
        Calculate how a region compares to national average
        """
        national_avg = df.groupby('State')[metric].sum().mean()
        region_value = df[df['State'] == region][metric].sum()
        
        if national_avg > 0:
            percentile = (region_value / national_avg) * 100
        else:
            percentile = 0
            
        return {
            'region_value': region_value,
            'national_avg': national_avg,
            'percentile': percentile,
            'status': 'above' if percentile > 100 else 'below'
        }
