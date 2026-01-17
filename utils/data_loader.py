import pandas as pd
import streamlit as st
import json
import requests
import os

@st.cache_data
def load_data(filepath):
    """
    Loads and processes the Aadhaar CSV data.
    Supports loading from 'segregated_data' folder if available.
    """
    # Check if we should load from segregated folder
    import os
    # Use relative path for portability
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    segregated_dir = os.path.join(base_dir, "Final_Processed_DataSet")
    
    df_list = []
    
    # Common Date Processing Function
    def process_dates(temp_df):
        if 'date' in temp_df.columns:
            temp_df['datestamp'] = pd.to_datetime(temp_df['date'], errors='coerce')
            # If Year is missing, extract from date
            if 'Year' not in temp_df.columns:
                temp_df['Year'] = temp_df['datestamp'].dt.year
            
            temp_df['Month'] = temp_df['datestamp'].dt.strftime('%b') # Jan, Feb
            temp_df['MonthOrder'] = temp_df['datestamp'].dt.month
            temp_df['Quarter'] = temp_df['datestamp'].dt.quarter
        return temp_df

    if os.path.exists(segregated_dir) and os.path.isdir(segregated_dir):
        files = [f for f in os.listdir(segregated_dir) if f.endswith('.csv')]
        if files:
            # st.info(f"Loading {len(files)} files from segregated_data...")
            for f in files:
                full_path = os.path.join(segregated_dir, f)
                try:
                    # Specific handling for the new format
                    temp_df = pd.read_csv(full_path, low_memory=False)
                    
                    # RENAME COLUMNS to match our internal logic
                    # New: enrol_age_0_5 -> age_0_5
                    rename_map = {
                        'state': 'State', 
                        'district': 'District', 
                        'pincode': 'PinCode',
                        'enrol_age_0_5': 'age_0_5',
                        'enrol_age_5_17': 'age_5_17',
                        'enrol_age_18_greater': 'age_18_greater',
                        'demo_demo_age_5_17': 'demo_age_5_17',
                        'demo_demo_age_17_': 'demo_age_17_',
                        'bio_bio_age_5_17': 'bio_age_5_17',
                        'bio_bio_age_17_': 'bio_age_17_'
                    }
                    temp_df.rename(columns=rename_map, inplace=True)
                    
                    df_list.append(temp_df)
                except Exception as e:
                    st.error(f"Failed to load {f}: {e}")
    
    if df_list:
        df = pd.concat(df_list, ignore_index=True)
    else:
        # Fallback to single file logic
        # Override filepath to the new source if the default is passed
        # Use relative path logic for fallback too
        if "aadhaar_data.csv" in filepath or "d:/" in filepath:
             # Try to find the large CSV in the root
             filepath = os.path.join(base_dir, "combined_full_Q1_Jan_Apr.csv")

        try:
            df = pd.read_csv(filepath, low_memory=False)
            df.rename(columns={'state': 'State', 'district': 'District', 'year': 'Year', 'pincode': 'PinCode'}, inplace=True)
        except FileNotFoundError:
            st.error(f"Data file not found at {filepath}. Please check file path.")
            return pd.DataFrame()

    # Apply Date Processing (Unified)
    df = process_dates(df)

    # 2. Cleaning
    # Remove rows where State is numeric (dirty data)
    df = df[~df['State'].astype(str).str.isnumeric()]
    
    # Fill NaNs with 0 for calculation
    # Ensure columns exist before filling
    metric_cols = ['age_0_5', 'age_5_17', 'age_18_greater', 'bio_age_5_17', 'bio_age_17_', 'demo_age_5_17', 'demo_age_17_']
    for col in metric_cols:
        if col not in df.columns:
            df[col] = 0
            
    df[metric_cols] = df[metric_cols].fillna(0)
    
    # 3. Calculate Metrics
    # Enrolment = Sum of age-based enrolments
    df['Enrolment'] = (df['age_0_5'] + df['age_5_17'] + df['age_18_greater']).fillna(0).astype(int)
    
    # Updates = Sum of Bio + Demo updates
    df['Updates'] = (df['bio_age_5_17'] + df['bio_age_17_'] + 
                     df['demo_age_5_17'] + df['demo_age_17_']).fillna(0).astype(int)
    
    # Detailed Update Breakdowns
    df['Demographic Updates'] = (df['demo_age_5_17'] + df['demo_age_17_']).fillna(0).astype(int)
    df['Biometric Updates'] = (df['bio_age_5_17'] + df['bio_age_17_']).fillna(0).astype(int)
                     
    # Rejections - Not in dataset, set to 0
    df['Rejections'] = 0
    
    # Metadata placeholders (to avoid breaking app logic)
    df['Avg_Age_Enrolled'] = 0.0 
    df['Gender_Ratio_Female'] = 0.0
    
    # Ensure Year is int
    # If Year was extracted by process_dates, it might be float, so convert safely
    if 'Year' in df.columns:
        df['Year'] = pd.to_numeric(df['Year'], errors='coerce').fillna(2025).astype(int)
    else:
        df['Year'] = 2025
    
    # Fix casing for consistency (PROPER CASE)
    df['State'] = df['State'].astype(str).str.title().str.strip()
    df['District'] = df['District'].astype(str).str.title().str.strip()
    
    # --- ROBUST NORMALIZATION ---
    
    # 1. District Aliases (New Name -> Legacy GeoJSON Name)
    district_aliases = {
        # --- ANDHRA PRADESH ---
        "Visakhapatanam": "Vishakhapatnam", "Y. S. R": "Cuddapah", "Y.S.R.": "Cuddapah", "Kadapa": "Cuddapah",
        "Sri Potti Sriramulu Nellore": "Nellore", "Ananthapur": "Anantapur", "Spsr Nellore": "Nellore",
        "Nandyal": "Kurnool", "Palnadu": "Guntur", "Bapatla": "Guntur", "Konaseema": "East Godavari",
        "Dr. B. R. Ambedkar Konaseema": "East Godavari", "Eluru": "West Godavari", "N. T. R": "Krishna", "Ntr": "Krishna",
        "Sri Sathya Sai": "Anantapur", "Annamayya": "Cuddapah", "Tirupati": "Chittoor",
        "Parvathipuram Manyam": "Vizianagaram", "Anakapalli": "Visakhapatnam", "Alluri Sitharama Raju": "Visakhapatnam",
        "Kakinada": "East Godavari",

        # --- ARUNACHAL PRADESH ---
        "Longding": "Tirap", "Namsai": "Lohit", "Kra Daadi": "Kurung Kumey", "Kamle": "Lower Subansiri",
        "Siang": "West Siang", "Shi-Yomi": "West Siang", "Lepa Rada": "West Siang", "Pakke Kessang": "East Kameng",
        
        # --- ASSAM ---
        "Biswanath": "Sonitpur", "Charaideo": "Sivasagar", "Hojai": "Nagaon", "Majuli": "Jorhat",
        "South Salmara Mankachar": "Dhubri", "West Karbi Anglong": "Karbi Anglong", "Kamrup Metro": "Kamrup",
        "Bajali": "Barpeta", "Tamulpur": "Baksa", "Tamulpur District": "Baksa", "Sribhumi": "Karimganj",

        # --- BIHAR ---
        "Purbi Champaran": "East Champaran", "Paschim Champaran": "West Champaran", 
        "Kaimur (Bhabua)": "Kaimur", "Bhabua": "Kaimur", "Monghyr": "Munger", "Purnea": "Purnia",
        "Samstipur": "Samastipur", "Sheikpura": "Sheikhpura", "East Champaran": "East Champaran",

        # --- CHHATTISGARH ---
        "Balod": "Durg", "Baloda Bazar": "Raipur", "Balrampur": "Surguja", "Bemetara": "Durg",
        "Gariyaband": "Raipur", "Gaurela-Pendra-Marwahi": "Bilaspur", "Gaurella Pendra Marwahi": "Bilaspur",
        "Kondagaon": "Bastar", "Mungeli": "Bilaspur", "Narayanpur": "Bastar", "Sukma": "Dakshin Bastar Dantewada",
        "Surajpur": "Surguja", "Mohla-Manpur-Ambagarh Chowki": "Rajnandgaon", "Mohla-Manpur-Ambagarh Chouki": "Rajnandgaon",
        "Sarangarh-Bilaigarh": "Raigarh", "Sakti": "Janjgir-Champa", "Khairagarh-Chhuikhadan-Gandai": "Rajnandgaon",
        "Khairagarh Chhuikhadan Gandai": "Rajnandgaon", "Manendragarh-Chirmiri-Bharatpur": "Koriya",
        "Manendragarh Chirmiri Bharatpur": "Koriya", "Manendragarhchirmiribharatpur": "Koriya",
        "Manendragarhâ€“Chirmiriâ€“Bharatpur": "Koriya", "Uttar Bastar Kanker": "Kanker",
        "Kabeerdham": "Kawardha", "Janjgir Champa": "Janjgir-Champa", "Dakshin Bastar Dantewada": "Dantewada",

        # --- DELHI ---
        "Central Delhi": "Central", "East Delhi": "East", "New Delhi": "New Delhi", "North Delhi": "North",
        "North East Delhi": "North East", "North West Delhi": "North West", "Shahdara": "East", # Mapped to East/NE
        "South Delhi": "South", "South East Delhi": "South", "South West Delhi": "South West", "West Delhi": "West",
        "Najafgarh": "South West", "Alipur": "North", "Kanjhawala": "North West", # Approx

        # --- GUJARAT ---
        "Ahmedabad": "Ahmadabad", "Banaskantha": "Banas Kantha", "Sabarkantha": "Sabar Kantha",
        "Chhotaudepur": "Vadodara", "Devbhumi Dwarka": "Jamnagar", "Gir Somnath": "Junagadh",
        "Mahisagar": "Panch Mahals", "Morbi": "Rajkot", "Botad": "Bhavnagar", "Arvalli": "Sabar Kantha",
        "Dohad": "Dohad", "Panchmahals": "Panch Mahals", "Surendra Nagar": "Surendranagar",

        # --- HARYANA ---
        "Gurugram": "Gurgaon", "Nuh": "Mewat", "Charkhi Dadri": "Bhiwani", "Palwal": "Faridabad",
        "Yamunanagar": "Yamuna Nagar", "Sonipat": "Sonipat",

        # --- HIMACHAL PRADESH ---
        "Lahaul And Spiti": "Lahul & Spiti", "Lahul And Spiti": "Lahul & Spiti",

        # --- JHARKHAND ---
        "East Singhbhum": "Purbi Singhbhum", "West Singhbhum": "Pashchimi Singhbhum",
        "Seraikela-Kharsawan": "Pashchimi Singhbhum", "Khunti": "Ranchi", "Ramgarh": "Hazaribagh",
        "Simdega": "Gumla", "Latehar": "Palamau", "Jamtara": "Dumka", "Saraikela-Kharsawan": "Pashchimi Singhbhum", # Approx
        "East Singhbum": "Purbi Singhbhum",

        # --- KARNATAKA ---
        "Bengaluru Urban": "Bangalore Urban", "Bengaluru Rural": "Bangalore Rural", "Bengaluru": "Bangalore Urban",
        "Belagavi": "Belgaum", "Bellary": "Ballari", "Vijayapura": "Bijapur", "Bijapur(Kar)": "Bijapur",
        "Kalaburagi": "Gulbarga", "Shivamogga": "Shimoga", "Tumakuru": "Tumkur",
        "Mysuru": "Mysore", "Chikkamagaluru": "Chikmagalur", "Chickmagalur": "Chikmagalur",
        "Dakshina Kannada": "Dakshin Kannad", "Uttara Kannada": "Uttar Kannad",
        "Vijayanagara": "Ballari", "Ramanagara": "Bangalore Rural", "Ramanagar": "Bangalore Rural",
        "Chikkaballapur": "Kolar", "Yadgir": "Gulbarga", "Davangere": "Davanagere", "Hasan": "Hassan",
        "Chamrajanagar": "Chamarajanagar",

        # --- KERALA ---
        "Thiruvananthapuram": "Thiruvananthapuram", "Alappuzha": "Alappuzha", "Kasargod": "Kasaragod",

        # --- MADHYA PRADESH ---
        "Agar Malwa": "Shajapur", "Alirajpur": "Jhabua", "Ashok Nagar": "Guna", "Singrauli": "Sidhi",
        "Anuppur": "Shahdol", "Burhanpur": "Khandwa", "Niwari": "Tikamgarh", "Mauganj": "Rewa",
        "Maihar": "Satna", "Pandhurna": "Chhindwara", "Narmadapuram": "Hoshangabad", "Narsimhapur": "Narsimhapur",
        "Khandwa": "East Nimar", "Khargone": "West Nimar",

        # --- MAHARASHTRA ---
        "Mumbai Suburban": "Greater Bombay", "Mumbai City": "Greater Bombay", "Mumbai": "Greater Bombay",
        "Mumbai( Sub Urban )": "Greater Bombay",
        "Dharashiv": "Osmanabad", "Chhatrapati Sambhajinagar": "Aurangabad", "Chatrapati Sambhaji Nagar": "Aurangabad",
        "Palghar": "Thane", "Raigarh": "Raigarh", "Raigarh(Mh)": "Raigarh", "Ahmed Nagar": "Ahmadnagar",

        # --- MANIPUR ---
        "Imphal East": "Imphal East", "Imphal West": "Imphal West", "Jiribam": "Imphal East",
        "Kakching": "Thoubal", "Pherzawl": "Churachandpur", "Noney": "Tamenglong", 
        "Kamjong": "Ukhrul", "Tengnoupal": "Chandel", "Kangpokpi": "Senapati",

        # --- MEGHALAYA ---
        "East Jaintia Hills": "Jaintia Hills", "West Jaintia Hills": "Jaintia Hills",
        "North Garo Hills": "East Garo Hills", "South West Garo Hills": "West Garo Hills",
        "South West Khasi Hills": "West Khasi Hills", "Eastern West Khasi Hills": "West Khasi Hills",
        "Ri Bhoi": "Ri-Bhoi", 
        
        # --- MIZORAM ---
        "Hnahthial": "Lunglei", "Khawzawl": "Champhai", "Saitual": "Aizawl", "Mammit": "Mamit",

        # --- NAGALAND ---
        "Chumukedima": "Dimapur", "Niuland": "Dimapur", "Tseminyu": "Kohima", "Noklak": "Tuensang",
        "Shamator": "Tuensang", "Longleng": "Tuensang", "Kiphire": "Tuensang", "Peren": "Kohima",

        # --- ODISHA ---
        "Balasore": "Baleswar", "Angul": "Anugul", "Boudh": "Baudh", "Deogarh": "Debagarh",
        "Keonjhar": "Kendujhar", "Jajpur": "Jajapur", "Nabarangpur": "Nabarangapur", 
        "Sonepur": "Subarnapur", "Jagatsinghpur": "Jagatsinghapur",

        # --- PUNJAB ---
        "Fazilka": "Firozpur", "Pathankot": "Gurdaspur", "S.A.S Nagar": "Rupnagar", "S.A.S Nagar(Mohali)": "Rupnagar",
        "Sas Nagar (Mohali)": "Rupnagar", "Mohali": "Rupnagar", "Sahibzada Ajit Singh Nagar": "Rupnagar",
        "Barnala": "Sangrur", "Malerkotla": "Sangrur", "Tarn Taran": "Amritsar",
        "Sri Muktsar Sahib": "Muktsar", "Shaheed Bhagat Singh Nagar": "Nawanshahr",

        # --- RAJASTHAN ---
        "Pratapgarh": "Chittorgarh", "Rajsamand": "Rajsamand", "Dausa": "Dausa",
        "Didwana-Kuchaman": "Nagaur", "Khairthal-Tijara": "Alwar", "Neem Ka Thana": "Sikar",
        "Kotputli-Behror": "Jaipur", "Balotra": "Barmer", "Anupgarh": "Ganganagar",
        "Deeg": "Bharatpur", "Salumbar": "Udaipur", "Gangapur City": "Sawai Madhopur",
        "Shahpura": "Bhilwara", "Kekri": "Ajmer", "Beawar": "Ajmer", "Dudo": "Jaipur",
        "Jaipur Rural": "Jaipur", "Jodhpur Rural": "Jodhpur", "Phalodi": "Jodhpur",
        "Jalore": "Jalor", "Dholpur": "Dhaulpur", "Jhunjhunu": "Jhunjhunun",

        # --- SIKKIM ---
        "East Sikkim": "East District", "West Sikkim": "West District", 
        "North Sikkim": "North District", "South Sikkim": "South District",
        "Mangan": "North District", "Gyalshing": "West District", 
        "Gangtok": "East District", "Namchi": "South District", "Pakyong": "East District", "Soreng": "West District",
        "North": "North District", "South": "South District", "East": "East District", "West": "West District",

        # --- TAMIL NADU ---
        "Kanchipuram": "Kancheepuram", "Chengalpattu": "Kancheepuram", "Kanyakumari": "Kanniyakumari",
        "Chennai (formerly Madras)": "Chennai", "Tirunelveli": "Tirunelveli Kattabo", "Tenkasi": "Tirunelveli Kattabo",
        "Ranipet": "Vellore", "Tirupathur": "Vellore", "Tirupattur": "Vellore", "Viluppuram": "Villupuram",
        "Kallakurichi": "Villupuram", "Mayiladuthurai": "Nagapattinam", "Tuticorin": "Thoothukudi",
        "Thoothukkudi": "Thoothukudi", "Tiruchirappalli": "Tiruchchirappalli", "Tiruvallur": "Thiruvallur",
        "Krishnagiri": "Dharmapuri", "Tiruppur": "Coimbatore", "The Nilgiris": "Nilgiris",

        # --- TELANGANA ---
        "Medchal Malkajgiri": "Rangareddy", "Rangareddy": "Rangareddy", "Vikarabad": "Rangareddy",
        "Sangareddy": "Medak", "Siddipet": "Medak", "Medak": "Medak",
        "Jagtial": "Karimnagar", "Peddapalli": "Karimnagar", "Rajanna Sircilla": "Karimnagar",
        "Jayashankar Bhupalpally": "Warangal", "Mulugu": "Warangal", "Mahabubabad": "Warangal",
        "Warangal Urban": "Warangal", "Warangal Rural": "Warangal", "Hanamkonda": "Warangal",
        "Jangaon": "Warangal", "Bhadradri Kothagudem": "Khammam", "Khammam": "Khammam",
        "Suryapet": "Nalgonda", "Yadadri Bhuvanagiri": "Nalgonda",
        "Nagarkurnool": "Mahbubnagar", "Wanaparthy": "Mahbubnagar", "Jogulamba Gadwal": "Mahbubnagar",
        "Narayanpet": "Mahbubnagar", "Mancherial": "Adilabad", "Nirmal": "Adilabad",
        "Komaram Bheem Asifabad": "Adilabad", "Asifabad": "Adilabad",
        "K.V.Rangareddy": "Rangareddy", "K.V. Rangareddy": "Rangareddy", 
        "Mahabub Nagar": "Mahbubnagar", "Mahabubnagar": "Mahbubnagar", "Karim Nagar": "Karimnagar",

        # --- TRIPURA ---
        "Khowai": "West Tripura", "Sepahijala": "West Tripura",
        "Unakoti": "North Tripura", "Gomati": "South Tripura", "Dhalai": "Dhalai",

        # --- UTTAR PRADESH ---
        "Prayagraj": "Allahabad", "Ayodhya": "Faizabad", "Amethi": "Sultanpur",
        "Sambhal": "Moradabad", "Bhimnagar": "Moradabad", "Shamli": "Muzaffarnagar", "Prabuddha Nagar": "Muzaffarnagar",
        "Hapur": "Ghaziabad", "Panchsheel Nagar": "Ghaziabad", "Kasganj": "Etah", "Kanshi Ram Nagar": "Etah",
        "Lakhimpur Kheri": "Kheri", "Kushi Nagar": "Kushinagar", "Sant Ravidas Nagar": "Sant Ravi Das Nagar",
        "Bhadohi": "Sant Ravi Das Nagar", "Sant Ravidas Nagar Bhadohi": "Sant Ravi Das Nagar",
        "Amroha": "Jyotiba Phule Nagar", "Hathras": "Mahamaya Nagar",
        "Bagpat": "Baghpat", "Budaun": "Badaun", "Bulandshahar": "Bulandshahr", "Shrawasti": "Shravasti",
        "Siddharthnagar": "Siddharth Nagar", "Barabanki": "Bara Banki", "Raebareli": "Rae Bareli",

        # --- WEST BENGAL ---
        "Alipurduar": "Jalpaiguri", "Kalimpong": "Darjiling", "Jhargram": "Paschim Medinipur",
        "Paschim Bardhaman": "Barddhaman", "Purba Bardhaman": "Barddhaman", "Bardhaman": "Barddhaman",
        "Purba Medinipur": "Medinipur", "Paschim Medinipur": "Medinipur", "Medinipur West": "Medinipur", "Medinipur": "Medinipur",
        "North 24 Parganas": "North Twenty Four Parganas", "South 24 Parganas": "South Twenty Four Parganas",
        "24 Paraganas North": "North Twenty Four Parganas", "24 Paraganas South": "South Twenty Four Parganas",
        "Coochbehar": "Koch Bihar", "Hooghiy": "Hugli", "Hawrah": "Haora", "Purulia": "Puruliya",
        "Dinajpur Dakshin": "Dakshin Dinajpur", "South Dinajpur": "Dakshin Dinajpur",
        "Dinajpur Uttar": "Uttar Dinajpur", "North Dinajpur": "Uttar Dinajpur", "Malda": "Maldah",
        "South Dumdum(M)": "North Twenty Four Parganas",
            
        # --- OTHER ---
        "Pondicherry": "Puducherry"
    }
    df['District'] = df['District'].replace(district_aliases)

    # 2. State Mappings (UI Name -> data normal form)
    # We must map CSV State names to the EXACT GeoJSON State Name keys.
    # This ensures the map fills completely.
    
    state_map_final = {
        # Merges for Dadra/Daman to single GeoJSON Feature
        "Dadra & Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
        "Dadra And Nagar Haveli": "Dadra and Nagar Haveli and Daman and Diu",
        "Daman & Diu": "Dadra and Nagar Haveli and Daman and Diu",
        "Daman And Diu": "Dadra and Nagar Haveli and Daman and Diu",
        "The Dadra And Nagar Haveli And Daman And Diu": "Dadra and Nagar Haveli and Daman and Diu",
        
        # Variations
        "Andaman & Nicobar Islands": "Andaman & Nicobar",
        "Andaman And Nicobar Islands": "Andaman & Nicobar",
        "Jammu And Kashmir": "Jammu & Kashmir",
        "Jammu and Kashmir": "Jammu & Kashmir",
        "Orissa": "Odisha",
        "Pondicherry": "Puducherry",
        "Westbengal": "West Bengal",
        "West Bangal": "West Bengal",
        "West  Bengal": "West Bengal",
        "Nct Of Delhi": "Delhi",
        "Delhi": "Delhi"
    }
    
    df['State'] = df['State'].replace(state_map_final)
    
    # GeoState is strictly for map joining. 
    # Since we normalized 'State' to match GeoJSON keys, we use it directly.
    df['GeoState'] = df['State']
    
    # --- ADD CITY COLUMN FROM PINCODE ---
    # Using pgeocode to fetch City/Place Name
    try:
        import pgeocode
        nomi = pgeocode.Nominatim('in')
        
        # Get unique valid pincodes
        unique_pins = df['PinCode'].unique().astype(str).tolist()
        
        # Batch query (pgeocode handles lists efficiently)
        geo_data = nomi.query_postal_code(unique_pins)
        
        # Create a mapping dictionary: Pincode -> Place Name
        # We use 'place_name' as it usually represents the specific Locality/City Area for the pincode.
        
        # Note: pgeocode returns NaN for invalid pins.
        pin_to_city = dict(zip(geo_data['postal_code'], geo_data['place_name']))
        
        # Map back to DF (City)
        df['City'] = df['PinCode'].astype(str).map(pin_to_city).fillna("Unknown")
        
        # --- NEW: Add Lat/Lon for Dot Density Map (e.g. for Delhi) ---
        # geo_data has 'postal_code', 'latitude', 'longitude'
        # We map them similarly to avoid heavy merges if possible, or just map.
        pin_to_lat = dict(zip(geo_data['postal_code'], geo_data['latitude']))
        pin_to_lon = dict(zip(geo_data['postal_code'], geo_data['longitude']))
        
        df['Latitude'] = df['PinCode'].astype(str).map(pin_to_lat)
        df['Longitude'] = df['PinCode'].astype(str).map(pin_to_lon)
        
    except ImportError:
        st.warning("pgeocode library not found. City column will be empty.")
        df['City'] = "Unknown"
        df['Latitude'] = pd.NA
        df['Longitude'] = pd.NA
    except Exception as e:
        st.warning(f"Error fetching city data: {e}")
        df['City'] = "Unknown"
        df['Latitude'] = pd.NA
        df['Longitude'] = pd.NA
        
    return df

@st.cache_data
def load_geojson():
    """
    Loads India States GeoJSON.
    Tries local asset first, then falls back to URL.
    """
    local_path = "d:/AadharHackathon/AadharHackathon/assets/india_states.geojson"
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading local State GeoJSON: {e}")
            
    url = "https://gist.githubusercontent.com/jbrobst/56c13bbbf9d97d187fea01ca62ea5112/raw/e388c4cae20aa53cb5090210a42ebb9b765c0a36/india_states.geojson"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading State GeoJSON: {e}")
        return None

@st.cache_data
def load_district_geojson():
    """
    Loads India Districts GeoJSON.
    Tries local asset first, then falls back to URL.
    """
    local_path = "d:/AadharHackathon/AadharHackathon/assets/india_district.geojson"
    if os.path.exists(local_path):
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            st.error(f"Error loading local District GeoJSON: {e}")

    url = "https://raw.githubusercontent.com/geohacker/india/master/district/india_district.geojson"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error loading District GeoJSON: {e}")
        return None

def get_state_centroid(state_name, geojson):
    """
    Calculates the centroid of a state polygon for zooming.
    Simple approximation using the bounding box of the geometry.
    """
    if not geojson:
        return None, None

    for feature in geojson['features']:
        if feature['properties']['ST_NM'] == state_name:
            # This is a simplification. For complex multipolygons, we might need a library like shapely.
            # But for visual zooming, getting coordinates from the first polygon ring is often 'good enough' to center.
            # However, a better approach for Plotly is to let it auto-center or provide a lat/lon map.
            
            # Let's hardcode some approximate centroids for better UX if needed, 
            # or rely on Plotly's fitbounds.
            # For this hackathon scope, we return the feature to let Plotly handle fitbounds if possible,
            # or we can derive center.
            return feature
            
    return None
