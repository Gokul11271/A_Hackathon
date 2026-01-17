
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
from utils.analytics_engine import AnalyticsEngine
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
import os
# Use a relative path placeholder, load_data handles the fallback logic but likes a path argument.
# We'll stick to a simple filename which load_data will treat as relative/fallback.
DATA_PATH = "aadhaar_data.csv" 
df = load_data(DATA_PATH)
state_geojson = load_geojson()
district_geojson = load_district_geojson()

if df.empty or not state_geojson:
    st.error("Data loading failed. Please check data files.")
    st.stop()

# --- ADVANCED FILTERS SIDEBAR ---
with st.sidebar:
    st.header("Advanced Filters")
    
    # Date range filter (if temporal data available)
    if 'datestamp' in df.columns:
        min_date = df['datestamp'].min()
        max_date = df['datestamp'].max()
        
        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_filter"
        )
        
        # Apply date filter
        if len(date_range) == 2:
            df = df[(df['datestamp'] >= pd.Timestamp(date_range[0])) & 
                   (df['datestamp'] <= pd.Timestamp(date_range[1]))]
    
    st.divider()
    
    # Age group filter
    st.subheader("Demographics")
    age_filter = st.multiselect(
        "Age Groups",
        ["0-5", "5-17", "18+"],
        default=["0-5", "5-17", "18+"],
        key="age_filter"
    )
    
    # Update type filter
    st.subheader("Update Types")
    show_demo = st.checkbox("Demographic Updates", value=True, key="show_demo")
    show_bio = st.checkbox("Biometric Updates", value=True, key="show_bio")
    
    st.divider()
    
    # Quick stats
    st.subheader("Quick Stats")
    st.metric("Total States", df['State'].nunique())
    st.metric("Total Districts", df['District'].nunique())
    st.metric("Data Points", len(df))





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
    # --- ENHANCED KPI CARDS WITH TRENDS ---
    st.subheader(f"Key Performance Indicators: {display_location}")
    
    # Initialize analytics engine
    analytics = AnalyticsEngine(df)
    
    # Calculate current metrics
    total_enrol = metric_df['Enrolment'].sum()
    total_updates = metric_df['Updates'].sum()
    demo_updates = (metric_df['demo_age_5_17'] + metric_df['demo_age_17_']).sum()
    bio_updates = (metric_df['bio_age_5_17'] + metric_df['bio_age_17_']).sum()
    
    # Calculate trends if temporal data available
    enrol_trend = analytics.calculate_trends(metric_df, 'Enrolment')
    update_trend = analytics.calculate_trends(metric_df, 'Updates')
    
    # Display KPI cards
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        if enrol_trend:
            delta_val = f"{enrol_trend['change_pct']:+.1f}%"
            m1.metric(
                "Total Enrolment", 
                f"{total_enrol:,.0f}", 
                delta=delta_val,
                delta_color="normal" if enrol_trend['trend'] == 'up' else "inverse"
            )
        else:
            m1.metric("Total Enrolment", f"{total_enrol:,.0f}")
    
    with m2:
        if update_trend:
            delta_val = f"{update_trend['change_pct']:+.1f}%"
            m2.metric(
                "Total Updates", 
                f"{total_updates:,.0f}",
                delta=delta_val,
                delta_color="normal" if update_trend['trend'] == 'up' else "inverse"
            )
        else:
            m2.metric("Total Updates", f"{total_updates:,.0f}")
    
    with m3:
        update_rate = (total_updates / total_enrol * 100) if total_enrol > 0 else 0
        m3.metric(
            "Update Rate", 
            f"{update_rate:.1f}%",
            help="Percentage of enrolments with updates"
        )
    
    with m4:
        bio_rate = (bio_updates / total_updates * 100) if total_updates > 0 else 0
        m4.metric(
            "Biometric Rate", 
            f"{bio_rate:.1f}%",
            help="Biometric updates as % of total updates"
        )
    
    # --- AUTO-GENERATED INSIGHTS PANEL ---
    with st.expander("Key Insights & Patterns", expanded=True):
        insights = analytics.generate_insights(metric_df, display_location)
        
        if insights:
            cols = st.columns(len(insights))
            for idx, insight in enumerate(insights):
                with cols[idx]:
                    if insight['type'] == 'success':
                        st.success(f"**{insight['title']}**\n\n{insight['message']}")
                    elif insight['type'] == 'warning':
                        st.warning(f"**{insight['title']}**\n\n{insight['message']}")
                    else:
                        st.info(f"**{insight['title']}**\n\n{insight['message']}")
        else:
            st.info("Analyzing patterns... More data needed for insights.")

    st.markdown("---")

    # --- MAIN GRID: 2:1 SPLIT ---
    # Col 1: Map (67%)
    # Col 2: Ranking + Demographics (33%)
    
    col_map, col_right = st.columns([2, 1], gap="medium")

    # === COLUMN 1: MAP ===
    with col_map:
        with st.container(border=True):
            st.subheader("Geospatial Analysis")
            map_metric = st.radio("Map Layer:", ["Enrolment", "Updates"], horizontal=True, label_visibility="collapsed")

            try:
                fig = render_india_map(
                    df, 
                    state_geojson, 
                    district_geojson, 
                    map_metric, 
                    selected_year, 
                    st.session_state['selected_state']
                )
                # Increase map height to match the stacked right column
                fig.update_layout(height=650, margin=dict(l=0, r=0, t=0, b=0))
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Map rendering failed: {e}")
                st.caption("Try filtering by State to reduce memory usage.")

    # === COLUMN 2: RIGHT PANEL ===
    with col_right:
        # --- SECTION A: INTERACTIVE RANKING ---
        with st.container(border=True):
            # Metric selector
            col_title, col_metric = st.columns([2, 1])
            with col_title:
                st.subheader("Regional Rankings")
            with col_metric:
                rank_metric = st.selectbox(
                    "Metric",
                    ["Enrolment", "Updates", "Update Rate"],
                    label_visibility="collapsed",
                    key="rank_metric_selector"
                )
            
            if st.session_state['view_mode'] == 'India':
                rank_df = filtered_df.groupby('State')[['Enrolment', 'Updates']].sum().reset_index()
                x_col = 'State'
            else:
                rank_df = metric_df.groupby('District')[['Enrolment', 'Updates']].sum().reset_index()
                x_col = 'District'
            
            # Calculate derived metrics
            rank_df['Update Rate'] = (rank_df['Updates'] / rank_df['Enrolment'] * 100).fillna(0)
            
            # Sort by selected metric
            rank_df = rank_df.sort_values(rank_metric, ascending=False)
            
            # Color scale based on metric
            color_scale = 'Viridis' if rank_metric in ['Enrolment', 'Updates'] else 'RdYlGn'
            
            fig_rank = px.bar(
                rank_df,
                x=x_col,
                y=rank_metric,
                color=rank_metric,
                color_continuous_scale=color_scale,
                template="plotly_white",
                hover_data={'Enrolment': ':,.0f', 'Updates': ':,.0f', 'Update Rate': ':.1f%'}
            )
            fig_rank.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                height=300,
                xaxis=dict(title=None, tickangle=-45),
                yaxis=dict(title=None),
                margin=dict(l=0, r=0, t=0, b=0),
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_rank, use_container_width=True)

        # --- SECTION B: ENHANCED DEMOGRAPHICS ---
        with st.container(border=True):
            st.subheader("Demographics")
            st.caption("Distribution of enrolments across age groups and update types.")
            
            # Age distribution pie chart
            age_0_5 = metric_df['age_0_5'].sum()
            age_5_17 = metric_df['age_5_17'].sum()
            age_18_plus = metric_df['age_18_greater'].sum()
            
            pie_data = pd.DataFrame({
                'Age Group': ['0-5', '5-17', '18+'],
                'Count': [age_0_5, age_5_17, age_18_plus]
            })
            
            fig_pie = px.pie(
                pie_data, 
                names='Age Group', 
                values='Count', 
                color='Age Group',
                color_discrete_map={'0-5':'#636EFA', '5-17':'#EF553B', '18+':'#00CC96'},
                hole=0.5,
                template="plotly_white"
            )
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(
                showlegend=False, 
                margin=dict(t=0, b=0, l=0, r=0),
                height=180
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # Update type breakdown
            st.markdown("**Update Distribution**")
            demo_total = (metric_df['demo_age_5_17'] + metric_df['demo_age_17_']).sum()
            bio_total = (metric_df['bio_age_5_17'] + metric_df['bio_age_17_']).sum()
            
            update_data = pd.DataFrame({
                'Type': ['Demographic', 'Biometric'],
                'Count': [demo_total, bio_total]
            })
            
            fig_update = px.bar(
                update_data,
                x='Type',
                y='Count',
                color='Type',
                color_discrete_map={'Demographic': '#FFA15A', 'Biometric': '#AB63FA'},
                template="plotly_white"
            )
            fig_update.update_layout(
                showlegend=False,
                height=150,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=None),
                yaxis=dict(title=None, showticklabels=False)
            )
            st.plotly_chart(fig_update, use_container_width=True)

    st.markdown("---")

    # --- TIME-SERIES TREND ANALYSIS ---
    st.subheader("Trend Analysis Over Time")
    
    if 'datestamp' in metric_df.columns and not metric_df.empty:
        col_trend_left, col_trend_right = st.columns([3, 1])
        
        with col_trend_right:
            # Metric selector for trend
            trend_metrics = st.multiselect(
                "Select Metrics",
                ["Enrolment", "Updates", "Demographic Updates", "Biometric Updates"],
                default=["Enrolment", "Updates"],
                key="trend_metric_selector"
            )
        
        with col_trend_left:
            if trend_metrics:
                # Prepare time-series data
                ts_data = metric_df.groupby('datestamp')[trend_metrics].sum().reset_index()
                ts_data = ts_data.sort_values('datestamp')
                
                # Create multi-line chart
                fig_trend = go.Figure()
                
                colors = {'Enrolment': '#00A389', 'Updates': '#3B82F6', 
                         'Demographic Updates': '#FFA15A', 'Biometric Updates': '#AB63FA'}
                
                for metric in trend_metrics:
                    fig_trend.add_trace(go.Scatter(
                        x=ts_data['datestamp'],
                        y=ts_data[metric],
                        mode='lines+markers',
                        name=metric,
                        line=dict(color=colors.get(metric, '#666'), width=3),
                        marker=dict(size=6)
                    ))
                
                fig_trend.update_layout(
                    height=350,
                    margin=dict(l=0, r=0, t=20, b=0),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        title="Date",
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.1)'
                    ),
                    yaxis=dict(
                        title="Count",
                        showgrid=True,
                        gridcolor='rgba(128,128,128,0.1)'
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_trend, use_container_width=True)
            else:
                st.info("Select at least one metric to view trends")
    else:
        st.info("Time-series data not available. Trends require date information.")

    st.markdown("---")

    # --- COMPARATIVE ANALYTICS & GROWTH RATES ---
    st.subheader("Comparative Analytics")
    
    col_growth, col_benchmark = st.columns(2)
    
    with col_growth:
        st.markdown("**Growth Rate Analysis**")
        
        # Calculate growth rates
        growth_df = analytics.calculate_growth_rates(
            metric_df, 
            'State' if st.session_state['view_mode'] == 'India' else 'District'
        )
        
        if not growth_df.empty and len(growth_df) > 0:
            # Show top and bottom performers
            top_5 = growth_df.nlargest(5, 'Growth_Rate')
            bottom_5 = growth_df.nsmallest(5, 'Growth_Rate')
            
            combined = pd.concat([top_5, bottom_5])
            combined['Category'] = ['Top Growth'] * len(top_5) + ['Slow Growth'] * len(bottom_5)
            
            group_col = 'State' if st.session_state['view_mode'] == 'India' else 'District'
            
            fig_growth = px.bar(
                combined,
                x=group_col,
                y='Growth_Rate',
                color='Category',
                color_discrete_map={'Top Growth': '#00CC96', 'Slow Growth': '#EF553B'},
                template="plotly_white"
            )
            fig_growth.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title=None, tickangle=-45),
                yaxis=dict(title="Growth Rate (%)")
            )
            st.plotly_chart(fig_growth, use_container_width=True)
        else:
            st.info("Growth rate analysis requires temporal data")
    
    with col_benchmark:
        st.markdown("**Performance Benchmarking**")
        
        # Calculate benchmarks
        if st.session_state['view_mode'] == 'India':
            national_avg = filtered_df.groupby('State')['Enrolment'].sum().mean()
            state_totals = filtered_df.groupby('State')['Enrolment'].sum().reset_index()
            state_totals['Benchmark'] = (state_totals['Enrolment'] / national_avg * 100)
            state_totals['Status'] = state_totals['Benchmark'].apply(
                lambda x: 'Above Average' if x > 100 else 'Below Average'
            )
            
            # Show distribution
            fig_bench = px.scatter(
                state_totals,
                x='Enrolment',
                y='Benchmark',
                color='Status',
                size='Enrolment',
                hover_name='State',
                color_discrete_map={'Above Average': '#00CC96', 'Below Average': '#FFA500'},
                template="plotly_white"
            )
            fig_bench.add_hline(y=100, line_dash="dash", line_color="gray", 
                               annotation_text="National Average")
            fig_bench.update_layout(
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="Total Enrolment"),
                yaxis=dict(title="% of National Avg")
            )
            st.plotly_chart(fig_bench, use_container_width=True)
        else:
            st.info("Benchmarking available in All India view")
    
    st.markdown("---")
    
    # --- HEATMAP VISUALIZATION ---
    st.subheader("Regional Performance Heatmap")
    
    if st.session_state['view_mode'] == 'India':
        # Prepare heatmap data
        heatmap_metrics = ['Enrolment', 'Updates', 'Update Rate']
        heatmap_df = filtered_df.groupby('State')[['Enrolment', 'Updates']].sum().reset_index()
        heatmap_df['Update Rate'] = (heatmap_df['Updates'] / heatmap_df['Enrolment'] * 100).fillna(0)
        
        # Normalize for heatmap (0-100 scale)
        for metric in heatmap_metrics:
            if heatmap_df[metric].max() > 0:
                heatmap_df[f'{metric}_Norm'] = (heatmap_df[metric] / heatmap_df[metric].max() * 100)
            else:
                heatmap_df[f'{metric}_Norm'] = 0
        
        # Create matrix for heatmap
        heatmap_matrix = heatmap_df[['State'] + [f'{m}_Norm' for m in heatmap_metrics]].set_index('State')
        heatmap_matrix.columns = heatmap_metrics
        
        # Create heatmap
        fig_heatmap = px.imshow(
            heatmap_matrix.T,
            labels=dict(x="State", y="Metric", color="Performance"),
            x=heatmap_matrix.index,
            y=heatmap_metrics,
            color_continuous_scale='RdYlGn',
            aspect="auto",
            text_auto='.0f'
        )
        fig_heatmap.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=0, b=0),
            xaxis=dict(tickangle=-45)
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)
        st.caption("Normalized performance scores (0-100) across key metrics")
    else:
        st.info("Heatmap available in All India view")
    
    st.markdown("---")
    
    # --- EXPORT FUNCTIONALITY ---
    st.subheader("Export Data")
    
    col_export1, col_export2, col_export3 = st.columns(3)
    
    with col_export1:
        # Export current view as CSV
        export_df = metric_df[['State', 'District', 'Enrolment', 'Updates', 'age_0_5', 'age_5_17', 'age_18_greater']]
        csv = export_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Current View (CSV)",
            data=csv,
            file_name=f"aadhaar_data_{display_location.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_export2:
        # Export insights as text
        insights = analytics.generate_insights(metric_df, display_location)
        insights_text = f"Insights for {display_location}\n\n"
        for i, insight in enumerate(insights, 1):
            insights_text += f"{i}. {insight['title']}\n   {insight['message']}\n\n"
        
        st.download_button(
            label="Download Insights (TXT)",
            data=insights_text,
            file_name=f"insights_{display_location.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )
    
    with col_export3:
        # Export summary stats
        summary_stats = f"""Aadhaar Dashboard Summary
Location: {display_location}
Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

Key Metrics:
- Total Enrolment: {total_enrol:,.0f}
- Total Updates: {total_updates:,.0f}
- Update Rate: {update_rate:.1f}%
- Biometric Rate: {bio_rate:.1f}%

Age Distribution:
- 0-5 years: {age_0_5:,.0f}
- 5-17 years: {age_5_17:,.0f}
- 18+ years: {age_18_plus:,.0f}
"""
        st.download_button(
            label="Download Summary (TXT)",
            data=summary_stats,
            file_name=f"summary_{display_location.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("---")

    # Row 2: Table
    with st.expander("Detailed Regional Breakdown", expanded=True):
        st.dataframe(
            rank_df, # Showing top ranked initially
            use_container_width=True,
            hide_index=True,
            height=250,
            column_config={
                "Enrolment": st.column_config.ProgressColumn("Enrolment", format="%d", min_value=0, max_value=int(rank_df['Enrolment'].max())),
                "Updates": st.column_config.NumberColumn("Overall Updates", format="%d"),
            }
        )

    # Row 3: Quarterly Trends (Left) & Comparison (Right)
    c_trend, c_comp = st.columns(2)
    
    with c_trend:
        # --- QUARTERLY ANALYSIS ---
        if 'Quarter' in metric_df.columns:
            st.subheader("Quarterly Trends (2025)")
            
            # Prepare Data
            if 'datestamp' in metric_df.columns:
                trend_df = metric_df.groupby('datestamp')[['Enrolment', 'Updates']].sum().reset_index()
                trend_df = trend_df.sort_values('datestamp')
                x_axis_col = 'datestamp'
            else:
                trend_df = metric_df.groupby(['Month', 'MonthOrder'])[['Enrolment', 'Updates']].sum().reset_index()
                trend_df = trend_df.sort_values('MonthOrder')
                x_axis_col = 'Month'
            
            if not trend_df.empty:
                # Re-use helper logic inline or cleaned up
                def create_mini_area(data, x_col, y_col, title, color_hex, fill_rgba):
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=data[x_col], y=data[y_col], mode='lines', fill='tozeroy',
                        line=dict(color=color_hex, width=2), fillcolor=fill_rgba
                    ))
                    fig.update_layout(
                        title=dict(text=title, font=dict(size=12)), # Removing explicit color to inherit theme
                        margin=dict(t=30, l=10, r=10, b=20),
                        height=150,
                        xaxis=dict(showgrid=False, showticklabels=False),
                        yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)'), # Removing explicit tickfont black color
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)'
                    )
                    return fig

                st.plotly_chart(create_mini_area(trend_df, x_axis_col, 'Enrolment', "Enrolment", "#00A389", "rgba(0, 163, 137, 0.1)"), use_container_width=True)
                st.plotly_chart(create_mini_area(trend_df, x_axis_col, 'Updates', "Updates", "#3B82F6", "rgba(59, 130, 246, 0.1)"), use_container_width=True)

    with c_comp:
        # --- COMPARISON CHART ---
        st.subheader("Regional Comparison")
        if st.session_state['view_mode'] == 'India':
            comp_group = 'State'
        else:
            comp_group = 'District'
            
        comp_df = metric_df.groupby(comp_group)[['Enrolment', 'Updates']].sum().reset_index()
        comp_df = comp_df.sort_values('Enrolment', ascending=False).head(10)
        comp_df_melt = comp_df.melt(id_vars=comp_group, value_vars=['Enrolment', 'Updates'], var_name='Metric', value_name='Count')
        
        fig_bar_group = px.bar(
            comp_df_melt, 
            x=comp_group, 
            y='Count', 
            color='Metric', 
            barmode='group',
            color_discrete_map={'Enrolment': '#19D3F3', 'Updates': '#FF6692'},
            template="plotly_white"
        )
        fig_bar_group.update_layout(
            legend_title=None, 
            plot_bgcolor="rgba(0,0,0,0)",
            height=320,
            margin=dict(t=20, l=0, r=0, b=0)
        )
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
        # Display Recommendations
        for rec in recommendations:
            rec_data = rec.to_dict()
            
            # Severity Color
            border_color = "#FF4B4B" if rec_data['Severity'] == "High" else "#FFA500" if rec_data['Severity'] == "Medium" else "#00CC96"
            
            with st.container(border=True):
                # Title with colored border effect simulation
                st.markdown(f"### {rec_data['Title']}")
                st.caption(f"📍 **{rec_data['District']}** | Pin: {rec_data['PinCode']}")
                st.markdown(rec_data['Description'])
                st.markdown("---")
                st.markdown(f"**🚀 Recommended Action:** {rec_data['Action By User']}")
                
                # Optional: Add a colored accent line if desired, or rely on the container border
                # Using a small markdown strip to show severity color
                st.markdown(f'<div style="height: 4px; width: 100%; background-color: {border_color}; border-radius: 2px;"></div>', unsafe_allow_html=True)

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
                size='Enrolment',
                template="plotly_white"
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
            color_discrete_sequence=['#636EFA', '#EF553B', '#00CC96'],
            template="plotly_white"
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
    st.subheader(" Temporal Pattern Analysis: Metro vs Non-Metro")
    
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
            st.markdown("#### Peak Demand Alerts")
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
