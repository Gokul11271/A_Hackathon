import streamlit as st

def render_marquee(recommendations):
    """
    Renders a scrolling marquee of recommendations. 
    If recommendations list is empty, it populates it with default items to ensure visibility.
    """
    
    # --- FAILSAFE: Ensure we have data to show ---
    display_recs = []
    if recommendations:
        display_recs = [r.to_dict() for r in recommendations]
    
    # If empty (even after analysis engine), force defaults here
    if not display_recs:
        display_recs = [
             {
                "Title": "Welcome to Aadhaar Insights",
                "District": "National View",
                "PinCode": "N/A",
                "Severity": "Low",
                "Description": "This dashboard provides real-time insights into Enrolment and Update trends across India.",
                "Action By User": "Explore the tabs below for detailed analysis."
            },
            {
                "Title": "Quarterly Trends Available",
                "District": "System Info",
                "PinCode": "N/A",
                "Severity": "Medium",
                "Description": "New Q1 2025 data has been loaded. Check the Quarterly Analysis tab for trend details.",
                "Action By User": "Navigate to 'National Dashboard' > 'Quarterly Analysis'."
            },
             {
                "Title": "Mandatory Updates Required",
                "District": "All Districts",
                "PinCode": "General",
                "Severity": "High",
                "Description": "Biometrics for children aged 5 and 15 must be updated to avoid deactivation.",
                "Action By User": "Prioritize camps in schools for age-specific updates."
            }
        ]

    # --- RENDER HTML ---
    # --- RENDER HTML ---
    # Convert list to a single scrolling string with separators
    marquee_items = []
    for r in display_recs:
        # Simple text format: "Title: Description"
        # We can keep the color coding for severity if desired, or just text.
        # User asked for "hi there hello", implying simple text flow.
        
        # Using a span for color but keeping structure simple
        severity_color = "#FF4B4B" if r['Severity'] == "High" else "#FFA500" if r['Severity'] == "Medium" else "#00CC96"
        item_text = f"<span style='color:{severity_color}; font-weight:bold'>• {r['Title']}</span>: {r['Description']}"
        marquee_items.append(item_text)
            
    # Join with spacing
    full_text = " &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; ".join(marquee_items)
    
    marquee_html = f"""
    <div class="marquee-wrapper">
        <div class="marquee-container">
            <div class="marquee-track">
                <div class="marquee-content">{full_text}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(marquee_html, unsafe_allow_html=True)


def handle_marquee_click(recommendations):
    """
    Checks query params for a click event and shows detail dialog.
    Compatible with both explicit objects and dictionary fail-safes.
    """
    if 'selected_rec_idx' in st.query_params:
        try:
            idx = int(st.query_params['selected_rec_idx'])
            
            # Re-construct the display list same as render logic to match index 
            # (In a real app, this shared state should be better managed, but for this stateless implementation:
            display_recs = []
            if recommendations:
                display_recs = [r.to_dict() for r in recommendations]
            
            # The fallback logic must match perfectly or indices will drift. 
            # Ideally we pass 'display_recs' IN logic, but strictly following 'remove code and rebuild'
            if not display_recs:
                 display_recs = [
                     {
                        "Title": "Welcome to Aadhaar Insights",
                        "District": "National View",
                        "PinCode": "N/A",
                        "Severity": "Low",
                        "Description": "This dashboard provides real-time insights into Enrolment and Update trends across India.",
                        "Action By User": "Explore the tabs below for detailed analysis."
                    },
                    {
                        "Title": "Quarterly Trends Available",
                        "District": "System Info",
                        "PinCode": "N/A",
                        "Severity": "Medium",
                        "Description": "New Q1 2025 data has been loaded. Check the Quarterly Analysis tab for trend details.",
                        "Action By User": "Navigate to 'National Dashboard' > 'Quarterly Analysis'."
                    },
                     {
                        "Title": "Mandatory Updates Required",
                        "District": "All Districts",
                        "PinCode": "General",
                        "Severity": "High",
                        "Description": "Biometrics for children aged 5 and 15 must be updated to avoid deactivation.",
                        "Action By User": "Prioritize camps in schools for age-specific updates."
                    }
                ]

            if 0 <= idx < len(display_recs):
                data = display_recs[idx]
                
                @st.dialog("Insight Details")
                def show_details(d):
                    st.title(d['Title'])
                    st.caption(f"📍 {d['District']}")
                    st.markdown("---")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.error(f"**Problem:**\n\n{d['Description']}")
                    with c2:
                        st.success(f"**Recommendation:**\n\n{d['Action By User']}")
                        
                    st.markdown("---")
                    if st.button("Close / Dismiss"):
                        st.query_params.clear()
                        st.rerun()
                
                show_details(data)
            else:
                st.query_params.clear()
        except Exception as e:
            st.query_params.clear()
