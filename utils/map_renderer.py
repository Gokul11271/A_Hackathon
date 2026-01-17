import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def get_geojson_bounds(geojson):
    """
    Calculates the bounds (min_lon, min_lat, max_lon, max_lat) of a GeoJSON.
    Simple implementation that iterates recursively through coordinates.
    """
    lats = []
    lons = []

    def extract_coords(coords):
        for item in coords:
            if isinstance(item[0], (list, tuple)):
                extract_coords(item)
            else:
                # item is [lon, lat]
                lons.append(item[0])
                lats.append(item[1])

    for feature in geojson['features']:
        geometry = feature['geometry']
        if geometry['type'] == 'Polygon':
            extract_coords(geometry['coordinates'])
        elif geometry['type'] == 'MultiPolygon':
            extract_coords(geometry['coordinates'])
            
    if not lats:
        return None
        
    return {
        "min_lon": min(lons),
        "max_lon": max(lons),
        "min_lat": min(lats),
        "max_lat": max(lats),
        "center_lon": sum(lons) / len(lons), # Centroid of points (approx)
        "center_lat": sum(lats) / len(lats)
    }

def render_india_map(df, geojson, district_geojson, selected_metric, selected_year, selected_state):
    """
    Renders the Choropleth map of India (State or District level) using Mapbox.
    """
    # Filter data for the year
    df_year = df[df['Year'] == selected_year]
    
    # Define premium color scales
    if selected_metric == "Rejections":
        color_scale = "Reds" 
    elif selected_metric == "Updates":
        color_scale = "Blues"
    else:
        color_scale = "Viridis" 

    mapbox_style = "carto-positron" 

    # --- ALL INDIA VIEW ---
    if selected_state == 'All India':
        # Aggregate by GeoState for the map color
        state_df = df_year.groupby('GeoState')[selected_metric].sum().reset_index()
        
        # Merge other cols for tooltips
        df_meta = df_year.groupby('GeoState')[['Avg_Age_Enrolled', 'Gender_Ratio_Female']].mean().reset_index()
        state_df = pd.merge(state_df, df_meta, on='GeoState', how='left')

        fig = px.choropleth_mapbox(
            state_df,
            geojson=geojson, 
            featureidkey="properties.ST_NM", 
            locations='GeoState',
            color=state_df[selected_metric].astype(float),
            color_continuous_scale=color_scale,
            range_color=(0, state_df[selected_metric].max()), 
            mapbox_style=mapbox_style,
            zoom=4.0,
            center={"lat": 22.5937, "lon": 78.9629},
            opacity=0.7,
            labels={selected_metric: selected_metric},
            hover_name='GeoState',
            hover_data={
                selected_metric: True,
                'Avg_Age_Enrolled': ':.1f',
                'Gender_Ratio_Female': ':.0f',
                'GeoState': False
            }
        )
        map_title = f"India - {selected_metric} ({selected_year})"

    # --- STATE / DISTRICT VIEW ---
    else:
        # Filter DF by selected State (Modern)
        df_view = df_year[df_year['State'] == selected_state].copy()
        
        # Aggregate Pincode-level data to District-level for Map
        # Note: We take 'first' for GeoState to preserve it.
        # We sum the metrics.
        # For Enrolment/Updates/Rejections, sum is correct.
        # For Avg_Age_Enrolled, we currently have placeholders (0.0), so mean/sum doesn't matter much but mean is safer.
        df_view = df_view.groupby('District').agg({
            selected_metric: 'sum',
            'GeoState': 'first',
            'Avg_Age_Enrolled': 'mean',
            'Gender_Ratio_Female': 'mean'
        }).reset_index()
        
        if df_view.empty:
            # Fallback if no data for selected state
            return go.Figure()

        # Determine the GeoJSON State Name (Legacy) using GeoState
        geo_state_name = df_view['GeoState'].iloc[0]
        
        # Mapping from our normalized names (State GeoJSON compatible) to District GeoJSON keys
        state_name_mapping = {
            "Andaman & Nicobar": "Andaman and Nicobar",
            "Jammu & Kashmir": "Jammu and Kashmir",
            "Odisha": "Orissa",
            "Uttarakhand": "Uttaranchal",
            "Dadra and Nagar Haveli and Daman and Diu": ["Dadra and Nagar Haveli", "Daman and Diu"]
        }
        
        target_names = state_name_mapping.get(geo_state_name, geo_state_name)
        if not isinstance(target_names, list):
            target_names = [target_names]
            
        # Filter GeoJSON features for this legacy state
        filtered_features = [
            f for f in district_geojson['features'] 
            if (f['properties'].get('st_nm') in target_names or f['properties'].get('NAME_1') in target_names)
        ]
        
        # --- FALLBACK: SCATTER MAP FOR MISSING POLYGONS (e.g. DELHI) ---
        # If we found no detailed district features (count <= 1), but we have Lat/Lon data,
        # render a Scatter/Bubble Map instead of Choropleth.
        # Delhi typically has only 1 feature in this GeoJSON, so it falls here.
        if len(filtered_features) <= 1 and 'Latitude' in df.columns:
            
            # Mapbox Style
            mapbox_style = "carto-positron" # Keep consistent
            
            # Aggregate at Pincode/Location Level for Scatter Plot
            # Filter original DF for this state/year
            df_scatter = df_year[df_year['State'] == selected_state].copy()
            
            # Group by Pincode + City + Lat + Lon
            # Note: Lat/Lon might be nan, drop them
            df_scatter = df_scatter.dropna(subset=['Latitude', 'Longitude'])
            
            if df_scatter.empty:
                 return go.Figure()
                 
            scatter_agg = df_scatter.groupby(['PinCode', 'City', 'District', 'Latitude', 'Longitude'])[[selected_metric]].sum().reset_index()
            
            # Center Map
            center_lat = scatter_agg['Latitude'].mean()
            center_lon = scatter_agg['Longitude'].mean()
            
            fig = px.scatter_mapbox(
                scatter_agg,
                lat="Latitude",
                lon="Longitude",
                size=selected_metric,
                color=selected_metric,
                color_continuous_scale=color_scale,
                size_max=15, # Adjust bubble size
                zoom=9, # Closer zoom for city
                center={"lat": center_lat, "lon": center_lon},
                mapbox_style=mapbox_style,
                hover_name="City",
                hover_data={
                    "District": True,
                    "PinCode": True,
                    selected_metric: True,
                    "Latitude": False,
                    "Longitude": False
                },
                opacity=0.7
            )
            map_title = f"{selected_state} - {selected_metric} (Pincode Density)"
            
            # Append title updater later in code...
            # We return early? No, we need layout updates.
            # Let's assign to 'fig' and let the function flow.
            pass

        else:
            # --- STANDARD CHOROPLETH ---
            
            # Create a temp GeoJSON
            map_geojson = {
                "type": "FeatureCollection",
                "features": filtered_features
            }
            
            # Determine feature key
            feature_key = 'properties.district'
            if filtered_features and 'NAME_2' in filtered_features[0]['properties']:
                 feature_key = 'properties.NAME_2'
    
            locations_col = 'District'
            map_title = f"{selected_state} - {selected_metric} ({selected_year})"
            
            # Calculate dynamic center
            bounds = get_geojson_bounds(map_geojson)
            if bounds:
                map_center = {"lat": bounds['center_lat'], "lon": bounds['center_lon']}
                # Zoom heuristic
                lat_diff = bounds['max_lat'] - bounds['min_lat']
                if lat_diff > 5: map_zoom = 5.5
                elif lat_diff > 2: map_zoom = 6.5
                else: map_zoom = 7.5
            else:
                map_center = {"lat": 20.5937, "lon": 78.9629} 
                map_zoom = 5
    
            # Create Mapbox Figure
            fig = px.choropleth_mapbox(
                df_view,
                geojson=map_geojson,
                featureidkey=feature_key,
                locations=locations_col,
                color=df_view[selected_metric].astype(float),
                color_continuous_scale=color_scale,
                range_color=(0, df_view[selected_metric].max()),
                hover_name=locations_col,
                hover_data={
                    selected_metric: True,
                    'Avg_Age_Enrolled': ':.1f',
                    'Gender_Ratio_Female': ':.0f',
                    locations_col: False
                },
                mapbox_style=mapbox_style,
                center=map_center,
                zoom=map_zoom,
                opacity=0.7 
            )

    # Common Layout Updates
    fig.update_layout(
        margin={"r":0,"t":40,"l":0,"b":0},
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=13, color="#333"),
        title=dict(
            text=map_title,
            y=0.96,
            x=0.02,
            xanchor='left',
            yanchor='top',
            font=dict(size=18)
        ),
        coloraxis_colorbar=dict(
            title=None,
            thicknessmode="pixels", thickness=8,
            lenmode="pixels", len=180,
            yanchor="top", y=0.8,
            xanchor="right", x=0.98,
            bgcolor="rgba(255,255,255,0.6)",
            tickfont=dict(size=10)
        )
    )
    
    return fig
