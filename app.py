
import streamlit as st
import pandas as pd
from utils.data_loader import load_data, load_geojson, load_district_geojson
from utils.map_renderer import render_india_map
import plotly.express as px
import plotly.graph_objects as go
from utils.analysis_engine import get_recommendations
from utils.anomaly_engine import AnomalyEngine
from utils.temporal_engine import TemporalEngine
from utils.ui_components import render_marquee, handle_marquee_click
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aadhaar Insights Dashboard",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)



# --- LOAD CSS ---
with open('styles/main.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# --- SESSION STATE INIT ---
if 'view_mode' not in st.session_state:
    st.session_state['view_mode'] = 'India' # Options: 'India', 'State'
if 'selected_state' not in st.session_state:
    st.session_state['selected_state'] = 'All India'
if 'selected_district' not in st.session_state:
    st.session_state['selected_district'] = 'All Districts'

# --- DATA LOADING ---
DATA_PATH = "d:/AadharHackathon/aadhaar_data.csv"
df = load_data(DATA_PATH)
state_geojson = load_geojson()
district_geojson = load_district_geojson()

if df.empty or not state_geojson:
    st.error("Data loading failed. Please check data files.")
    st.stop()




# --- TOP NAVBAR ---
with st.container():
   col_logo, col_title, col_state, col_dist, col_search = st.columns([1, 4, 3, 3, 3])
   
   with col_logo:
        st.image("https://upload.wikimedia.org/wikipedia/en/thumb/c/cf/Aadhaar_Logo.svg/1200px-Aadhaar_Logo.svg.png", use_container_width=True)
   
   with col_title:
       st.title("Aadhaar Insights")
       st.caption("National Enrolment & Update Intelligence")

   # Logic for State/District Selection
   def on_state_change():
        new_state = st.session_state['state_selector_nav']
        st.session_state['selected_state'] = new_state
        if new_state == "All India":
            st.session_state['view_mode'] = 'India'
            st.session_state['selected_district'] = 'All Districts'
        else:
            st.session_state['view_mode'] = 'State'

   state_list = ["All India"] + sorted(df['State'].unique().tolist())
   try:
       default_ix = state_list.index(st.session_state['selected_state'])
   except ValueError:
       default_ix = 0
   
   with col_state:
       selected_state = st.selectbox(
           "Select Region", 
           state_list, 
           index=default_ix, 
           key='state_selector_nav', 
           on_change=on_state_change
       )

   # District Logic
   districts_list = ["All Districts"]
   if selected_state != "All India":
       districts = sorted(df[df['State'] == selected_state]['District'].unique().tolist())
       districts_list += districts
   
   with col_dist:
       selected_district = st.selectbox(
           "Select District", 
           districts_list,
           key='district_selector_nav'
       )
   st.session_state['selected_district'] = selected_district
   
   # Recommendations / Search
   with col_search:
       if st.session_state['view_mode'] == 'India':
            search_items = sorted(df['State'].unique().tolist())
            search_label = "Search State"
       elif st.session_state['selected_district'] == 'All Districts':
            search_items = sorted(df[df['State'] == selected_state]['District'].unique().tolist())
            search_label = "Search District"
       else:
            dist_df_search = df[df['District'] == selected_district]
            search_items = sorted(dist_df_search['PinCode'].unique().astype(str).tolist())
            search_label = "Search Pincode"
            
       st.multiselect(search_label, search_items, key="navbar_search")

# --- MARQUEE RECOMMENDATION SYSTEM (Contextual) ---
# Fetch recommendations based on current selection
mq_state_filter = selected_state
mq_dist_filter = None if selected_district == "All Districts" else selected_district

marquee_recs = get_recommendations(df, state_filter=mq_state_filter, district_filter=mq_dist_filter)
handle_marquee_click(marquee_recs)
render_marquee(marquee_recs)

# --- DATA FILTERING ---
selected_year = df['Year'].max()

if selected_state == "All India":
    filtered_df = df[df['Year'] == selected_year]
    display_location = "All India"
else:
    filtered_df = df[(df['State'] == selected_state) & (df['Year'] == selected_year)]
    display_location = selected_state

metric_df = filtered_df.copy()
if selected_district != "All Districts":
    metric_df = filtered_df[filtered_df['District'] == selected_district]
    display_location = f"{selected_district}, {selected_state}"


st.markdown("---")

# --- MAIN TABS ---
tab1, tab2, tab4, tab5 = st.tabs(["National Dashboard", "Smart Recommendations", "Anomaly Detection", "Temporal Analysis"])

# ================= TAB 1: DASHBOARD =================
with tab1:
    # --- LIVE DATA METRICS ---
    st.subheader(f"Live Data Overview: {display_location}")

    total_enrol = metric_df['Enrolment'].sum()
    total_updates = metric_df['Updates'].sum()

    demo_updates = (metric_df['demo_age_5_17'] + metric_df['demo_age_17_']).sum()
    bio_updates = (metric_df['bio_age_5_17'] + metric_df['bio_age_17_']).sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Enrolment", f"{total_enrol:,.0f}", delta="New")
    m2.metric("Total Updates", f"{total_updates:,.0f}")
    m3.metric("Demographic Updates", f"{demo_updates:,.0f}", help="Name, Address, DOB, etc.")
    m4.metric("Biometric Updates", f"{bio_updates:,.0f}", help="Fingerprint, Iris, Photo")

    st.markdown("---")

    # --- MAP SECTION ---
    st.subheader("Geospatial Analysis")
    map_metric = st.radio("Map Layer:", ["Enrolment", "Updates"], horizontal=True)

    fig = render_india_map(
        df, 
        state_geojson, 
        district_geojson, 
        map_metric, 
        selected_year, 
        st.session_state['selected_state']
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- STATE RANKING CHART ---
    st.subheader("Regional Performance Ranking")

    if st.session_state['view_mode'] == 'India':
        rank_df = filtered_df.groupby('State')[['Enrolment', 'Updates', 'Demographic Updates', 'Biometric Updates']].sum().reset_index()
        rank_df = rank_df.sort_values('Enrolment', ascending=False)
        y_col = 'Enrolment'
        x_col = 'State' 
        title_chart = "State-wise Enrolment Ranking (High to Low)"
    else:
        rank_df = metric_df.groupby('District')[['Enrolment', 'Updates', 'Demographic Updates', 'Biometric Updates']].sum().reset_index()
        rank_df = rank_df.sort_values('Enrolment', ascending=False)
        y_col = 'Enrolment'
        x_col = 'District'
        title_chart = "District-wise Enrolment Ranking"

    fig_rank = px.bar(
        rank_df,
        x=x_col,
        y=y_col,
        color=y_col,
        title=title_chart,
        color_continuous_scale='Viridis'
    )
    st.plotly_chart(fig_rank, use_container_width=True)


    # --- REGIONAL BREAKDOWN (Table) ---
    st.subheader("Detailed Regional Breakdown")
    st.dataframe(
        rank_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Enrolment": st.column_config.ProgressColumn("Enrolment", format="%d", min_value=0, max_value=int(rank_df['Enrolment'].max())),
            "Updates": st.column_config.NumberColumn("Overall Updates", format="%d"),
            "Demographic Updates": st.column_config.NumberColumn("Demographic Updates", format="%d"),
            "Biometric Updates": st.column_config.NumberColumn("Biometric Updates", format="%d"),
        }
    )

    st.markdown("---")

    # --- QUARTERLY ANALYSIS ---
    if 'Quarter' in metric_df.columns:
        st.subheader("Quarterly Analysis (2025) - Trend Overview")
        
        # Prepare Data: Use Daily aggregation for granular "Trends"
        # Ensure we have datestamp
        if 'datestamp' in metric_df.columns:
            trend_df = metric_df.groupby('datestamp')[['Enrolment', 'Updates']].sum().reset_index()
            trend_df = trend_df.sort_values('datestamp')
            x_axis_col = 'datestamp'
        else:
            # Fallback if datestamp missing
            trend_df = metric_df.groupby(['Month', 'MonthOrder'])[['Enrolment', 'Updates']].sum().reset_index()
            trend_df = trend_df.sort_values('MonthOrder')
            x_axis_col = 'Month'
        
        if not trend_df.empty:
            c1, c2 = st.columns(2)
            
            # --- HELPER TO CREATE STOCK-LIKE AREA CHART ---
            def create_area_chart(data, x_col, y_col, title, color_hex, fill_color_rgba):
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=data[x_col],
                    y=data[y_col],
                    mode='lines',  # Remove markers for cleaner daily view
                    fill='tozeroy',
                    line=dict(color=color_hex, width=2),
                    # marker=dict(size=10), # specific markers too noisy for daily
                    fillcolor=fill_color_rgba,
                    name=title
                ))
                
                # Determine Tick Format based on granularity
                if x_col == 'datestamp':
                    tick_fmt = "%d %b" # e.g. 01 Jan
                    tick_mode = 'auto'
                    tick_vals = None
                else:
                    tick_fmt = None
                    tick_mode = 'array'
                    tick_vals = data[x_col]

                fig.update_layout(
                    title=dict(text=title, font=dict(color='white', size=14)),
                    xaxis=dict(
                        showgrid=False, 
                        showticklabels=True, 
                        tickfont=dict(color='white'),
                        title=None,
                        tickformat=tick_fmt,
                        tickmode=tick_mode,
                        tickvals=tick_vals
                    ),
                    yaxis=dict(
                        showgrid=True, 
                        gridcolor='rgba(128,128,128,0.2)', 
                        tickfont=dict(color='white'),
                        title=None
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=40, l=10, r=10, b=40),
                    showlegend=False,
                    hovermode="x unified"
                )
                return fig

            # 1. Enrolment Chart (Greenish like the image)
            with c1:
                fig_enrol = create_area_chart(
                    trend_df, x_axis_col, 'Enrolment', 
                    "Enrolment Trend (Daily)", 
                    "#00A389", # Strong Green
                    "rgba(0, 163, 137, 0.2)" # Transparent Green fill
                )
                st.plotly_chart(fig_enrol, use_container_width=True)
                
            # 2. Updates Chart (Blueish/Orange to contrast)
            with c2:
                fig_update = create_area_chart(
                    trend_df, x_axis_col, 'Updates', 
                    "Updates Trend (Daily)", 
                    "#3B82F6", # Bright Blue
                    "rgba(59, 130, 246, 0.2)" # Transparent Blue fill
                )
                st.plotly_chart(fig_update, use_container_width=True)

        else:
            st.info("No trend data available.")
            
    else:
        st.info("Quarterly data attribute missing. Please check data loader.")

    st.markdown("---")

    # ================= DETAILED INSIGHTS SECTION =================
    st.subheader("🔍 Detailed Insights & Demographics")

    # Row 1: Pie Chart (Demographics) & Line Chart (Update Types Trend)
    row1_c1, row1_c2 = st.columns(2)

    with row1_c1:
        st.markdown("#### 🥧 Demographic Share (Age Groups)")
        # Calculate Age Sums
        age_0_5 = metric_df['age_0_5'].sum()
        age_5_17 = metric_df['age_5_17'].sum()
        age_18_plus = metric_df['age_18_greater'].sum()
        
        pie_data = pd.DataFrame({
            'Age Group': ['0-5 Years', '5-17 Years', '18+ Years'],
            'Count': [age_0_5, age_5_17, age_18_plus]
        })
        
        fig_pie = px.pie(
            pie_data, 
            names='Age Group', 
            values='Count', 
            color='Age Group',
            color_discrete_map={'0-5 Years':'#636EFA', '5-17 Years':'#EF553B', '18+ Years':'#00CC96'},
            hole=0.4
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

    with row1_c2:
        st.markdown("#### 📈 Update Type Trends (Demo vs Bio)")
        if 'datestamp' in metric_df.columns:
            # Group by date for Demo vs Bio
            update_trend = metric_df.groupby('datestamp')[['Demographic Updates', 'Biometric Updates']].sum().reset_index()
            update_trend = update_trend.sort_values('datestamp')
            
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=update_trend['datestamp'], y=update_trend['Demographic Updates'], mode='lines', name='Demographic', line=dict(color='#FFA15A')))
            fig_line.add_trace(go.Scatter(x=update_trend['datestamp'], y=update_trend['Biometric Updates'], mode='lines', name='Biometric', line=dict(color='#AB63FA')))
            
            fig_line.update_layout(
                xaxis_title="Date", 
                yaxis_title="Updates Count",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.warning("Trend data unavailable.")

    # Row 2: Bar Chart (District Comparison - Grouped)
    st.markdown("#### 📊 Regional Comparison: Enrolment vs Updates")
    
    if st.session_state['view_mode'] == 'India':
        comp_group = 'State'
        limit = 10 # Top 10 States
    else:
        comp_group = 'District'
        limit = 15 # Top 15 Districts
        
    # Prepare Data
    comp_df = metric_df.groupby(comp_group)[['Enrolment', 'Updates']].sum().reset_index()
    # Sort by Enrolment and take top N
    comp_df = comp_df.sort_values('Enrolment', ascending=False).head(limit)
    
    # Melt for Grouped Bar
    comp_df_melt = comp_df.melt(id_vars=comp_group, value_vars=['Enrolment', 'Updates'], var_name='Metric', value_name='Count')
    
    fig_bar_group = px.bar(
        comp_df_melt, 
        x=comp_group, 
        y='Count', 
        color='Metric', 
        barmode='group',
        color_discrete_map={'Enrolment': '#19D3F3', 'Updates': '#FF6692'},
        text_auto='.2s'
    )
    fig_bar_group.update_layout(xaxis_title=None, legend_title=None)
    st.plotly_chart(fig_bar_group, use_container_width=True)

# ================= TAB 2: RECOMMENDATIONS =================
with tab2:
    st.subheader("💡 AadhaarSeva: AI-Driven Recommendation Engine")
    
    st.markdown("""
    **Problem Statement:** Strategic Service Gaps & Reactive Planning.  
    **Objective:** Identify high-enrollment areas with low mandatory biometric updates (Ages 5-17).  
    **Solution:** Proactive recommendations for new centers, mobile camps, and awareness drives.
    """)
    st.markdown("---")

    # Generate Recommendations
    # We pass the CURRENT filtered view so the recommendations are relevant to what the user is looking at.
    # But if looking at All India, we might get too many. The function handles top 5 logic.
    
    # We want recommendations for the SELECTED State/District context.
    
    current_state_filter = selected_state
    current_dist_filter = None if selected_district == "All Districts" else selected_district
    
    with st.spinner(f"Analyzing patterns for {display_location}..."):
        recommendations = get_recommendations(df, current_state_filter, current_dist_filter)
        time.sleep(1) # Fake crunch time for UX

    if not recommendations:
        st.success(f"✅ No critical service gaps detected in {display_location}. Metrics are within healthy ranges.")
    else:
        # Display Recommendations
        for rec in recommendations:
            rec_data = rec.to_dict()
            
            # Severity Color
            border_color = "#FF4B4B" if rec_data['Severity'] == "High" else "#FFA500" if rec_data['Severity'] == "Medium" else "#00CC96"
            
            with st.container():
                st.markdown(f"""
                <div style="border-left: 5px solid {border_color}; padding: 10px; background-color: #f9f9f9; border-radius: 5px; margin-bottom: 10px;">
                    <h3 style="margin: 0; color: #333;">{rec_data['Title']}</h3>
                    <p style="margin: 5px 0; font-size: 14px; color: #555;">📍 <strong>{rec_data['District']}</strong> | Pin: {rec_data['PinCode']}</p>
                    <p style="margin: 5px 0;">{rec_data['Description']}</p>
                    <hr style="margin: 5px 0; border-color: #ddd;">
                    <p style="font-weight: bold; color: {border_color}; margin: 5px 0;">🚀 Recommended Action: {rec_data['Action By User']}</p>
                </div>
                """, unsafe_allow_html=True)

    # --- SUPPORTING DATA (EVIDENCE) ---
    st.markdown("### 🔍 Supporting Evidence")
    
    # Show a Scatter Plot of Enrolment vs Bio Updates to visualize outliers
    # Points below the diagonal are "High Enrolment / Low Updates"
    
    ev_df = metric_df.groupby(['District', 'PinCode'])[['Enrolment', 'Updates', 'bio_age_5_17']].sum().reset_index()
    # Filter out noise
    ev_df = ev_df[ev_df['Enrolment'] > 50]
    
    fig_scatter = px.scatter(
        ev_df,
        x="Enrolment",
        y="Updates",
        size="bio_age_5_17",
        hover_name="PinCode",
        color="District", # Color by District to see clusters
        title="Service Gap Analysis: Enrolment vs. Update Activity",
        labels={"Enrolment": "Total Enrolments", "Updates": "Total Updates"},
        template="plotly_white"
    )
    # Add a reference line (1:1 is ideal world, but let's say 20% update rate line)
    # fig_scatter.add_shape(type="line", x0=0, y0=0, x1=ev_df['Enrolment'].max(), y1=ev_df['Enrolment'].max()*0.5, line=dict(color="Gray", dash="dash"))
    
    st.plotly_chart(fig_scatter, use_container_width=True)
    st.caption("Size of bubble represents Biometric Updates (5-17). Small bubbles with high X-value (Enrolment) indicate missed mandatory updates.")

# ================= TAB 4: ADVANCED ANOMALY DETECTION =================
with tab4:
    st.subheader("⚠️ Advanced Anomaly Detection System")
    st.markdown("Identifies statistical irregularities using Isolation Forest, Z-Score, and Spatial Analysis.")
    
    # Init Engine
    ae = AnomalyEngine(df)
    
    # Run detections
    vol_anomalies = ae.detect_volume_anomalies(region_type='District')
    age_anomalies = ae.detect_age_structure_anomalies(region_type='District')
    spatial_anomalies = ae.detect_spatial_anomalies()
    
    # --- SUMMARY METRICS ---
    m1, m2, m3 = st.columns(3)
    m1.metric("Volume Anomalies", len(vol_anomalies), help="Districts with extreme traffic (Z > 2.5)")
    m2.metric("Age Structure Risks", len(age_anomalies), help="Districts with skewed demographics")
    m3.metric("Spatial Outliers", len(spatial_anomalies), help="Districts disconnected from state trends")
    
    st.markdown("---")

    # --- 1. VOLUME ANOMALIES (Interactive Scatter) ---
    st.markdown("#### 📉 Volume Analysis: Outlier Detection")
    if not vol_anomalies.empty:
        c1, c2 = st.columns([2, 1])
        with c1:
            # Visualize Anomalies vs Normal used Scatter
            # We need the full dataset context to show 'Normal' vs 'Anomaly'
            # Let's quickly re-aggregate for the plot
            plot_df = df.groupby('District')[['Enrolment', 'Updates']].sum().reset_index()
            # Mark anomalies
            plot_df['Type'] = 'Normal'
            plot_df.loc[plot_df['District'].isin(vol_anomalies['District']), 'Type'] = 'Anomaly'
            
            fig_vol = px.scatter(
                plot_df, 
                x="Enrolment", 
                y="Updates", 
                color="Type",
                hover_name="District",
                color_discrete_map={'Normal': '#aec7e8', 'Anomaly': '#d62728'},
                title="District Clusters: Enrolment vs Updates",
                size='Enrolment'
            )
            st.plotly_chart(fig_vol, use_container_width=True)
            
        with c2:
            st.warning(f"**{len(vol_anomalies)} Critical Districts Found**")
            st.dataframe(
                vol_anomalies[['District', 'Reason']],
                hide_index=True,
                use_container_width=True
            )
    else:
        st.success("✅ No volume anomalies detected. Traffic is consistent.")

    st.markdown("---")

    # --- 2. AGE STRUCTURE ANALYSIS (Stacked Bar) ---
    st.markdown("#### 👶 Age Structure Demographics")
    if not age_anomalies.empty:
        st.caption("Comparing anomalous districts against the National Average distribution.")
        
        # Prepare data for plotting: Top 5 Anomalies vs National Avg
        top_anom = age_anomalies.head(5).copy()
        
        # Calculate National Avg for comparison row
        nat_avg = df[['age_0_5', 'age_5_17', 'age_18_greater']].sum()
        nat_row = pd.DataFrame([{
            'District': 'National Average',
            'age_0_5': nat_avg['age_0_5'],
            'age_5_17': nat_avg['age_5_17'],
            'age_18_greater': nat_avg['age_18_greater'],
            'Reason': 'Benchmark'
        }])
        
        # Combine
        comp_df = pd.concat([top_anom[['District', 'age_0_5', 'age_5_17', 'age_18_greater']], nat_row])
        
        # Normalize to 100% for comparison
        comp_df['Total'] = comp_df[['age_0_5', 'age_5_17', 'age_18_greater']].sum(axis=1)
        comp_df['0-5 %'] = (comp_df['age_0_5'] / comp_df['Total']) * 100
        comp_df['5-17 %'] = (comp_df['age_5_17'] / comp_df['Total']) * 100
        comp_df['18+ %'] = (comp_df['age_18_greater'] / comp_df['Total']) * 100
        
        fig_age = px.bar(
            comp_df,
            x='District',
            y=['0-5 %', '5-17 %', '18+ %'],
            title="Age Composition: Anomalies vs Benchmark",
            color_discrete_sequence=['#636EFA', '#EF553B', '#00CC96']
        )
        st.plotly_chart(fig_age, use_container_width=True)
        
        with st.expander("View Detailed Age Data"):
            st.dataframe(top_anom[['District', 'Structure_Divergence', 'age_0_5', 'age_5_17']], use_container_width=True)
            
    else:
        st.success("✅ Age demographics are consistent across all regions.")

    st.markdown("---")

    # --- 3. SPATIAL OUTLIERS ---
    st.markdown("#### 🗺️ Spatial Context Analysis")
    if not spatial_anomalies.empty:
        c1, c2 = st.columns(2)
        with c1:
            st.dataframe(
                spatial_anomalies[['State', 'District', 'Enrolment', 'Reason']],
                hide_index=True,
                use_container_width=True
            )
        with c2:
            st.info("""
            **What is a Spatial Outlier?**
            A district is flagged if its Enrolment volume is significantly higher or lower (> 3.5 Modified Z-Score) than the median of other districts in the **same state**.
            
            This helps isolate localized issues (e.g., a specific district center shutdown) vs state-wide trends.
            """)
    else:
        st.success("✅ No spatial outliers detected.")

# ================= TAB 5: TEMPORAL ANALYSIS =================
with tab5:
    st.subheader("⏳ Temporal Pattern Analysis: Metro vs Non-Metro")
    
    with st.expander("ℹ️  Included Metro Regions"):
        st.write(", ".join(sorted(TemporalEngine.METRO_DISTRICTS)))
        
    st.markdown("Analyze seasonal variations to predict peak demand periods and optimize resource allocation.")
    
    te = TemporalEngine(df)
    metro_trends = te.get_metro_trends()
    
    if not metro_trends.empty:
        # 1. Visualization
        col_chart, col_rec = st.columns([3, 1])
        
        with col_chart:
            fig_temp = te.plot_metro_comparison(metro_trends)
            if fig_temp:
                st.plotly_chart(fig_temp, use_container_width=True)
            else:
                st.info("No temporal data available for plotting.")
            
        # 2. Peak Detection & Recommendations
        with col_rec:
            st.markdown("#### 🚀 Peak Demand Alerts")
            peaks = te.detect_peak_periods(metro_trends)
            
            if peaks:
                for p in peaks:
                    with st.container():
                        st.warning(f"**{p['Month']} Peak**")
                        st.caption(f"Volume: {int(p['Volume']):,}")
                        st.info(p['Recommendation'])
                        st.markdown("---")
            else:
                st.success("Demand is stable throughout the year.")
                
        # 3. Data View
        with st.expander("View Underlying Data"):
            st.dataframe(metro_trends, use_container_width=True)
            
    else:
        st.warning("Insufficient temporal data (Month/Date) to generate analysis. Please ensure your dataset includes a Date column.")
