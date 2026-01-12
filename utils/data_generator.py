import pandas as pd
import numpy as np
import random

def generate_data():
    states = [
        "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", 
        "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", 
        "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", 
        "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", 
        "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", "Chandigarh", 
        "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep", "Delhi", "Puducherry",
        "Jammu and Kashmir", "Ladakh"
    ]
    
    # Sample real districts for a better hackathon demo experience
    # Used common names that likely match standard GeoJSONs (often older English spellings)
    state_districts = {
        "Andhra Pradesh": ["Vishakhapatnam", "Chittoor", "Guntur", "Krishna", "East Godavari"],
        "Arunachal Pradesh": ["Tawang", "West Kameng", "East Siang", "Papum Pare"],
        "Assam": ["Kamrup", "Dibrugarh", "Jorhat", "Cachar"],
        "Bihar": ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur"],
        "Chhattisgarh": ["Raipur", "Durg", "Bilaspur", "Korba"],
        "Goa": ["North Goa", "South Goa"],
        "Gujarat": ["Ahmadabad", "Surat", "Vadodara", "Rajkot"],
        "Haryana": ["Gurgaon", "Faridabad", "Panipat", "Ambala"],
        "Himachal Pradesh": ["Shimla", "Kullu", "Kangra", "Solan"],
        "Jharkhand": ["Ranchi", "Purba Singhbhum", "Dhanbad", "Bokaro"],
        "Karnataka": ["Bangalore Urban", "Mysore", "Dakshin Kannad", "Dharwad"], # Updated to match GeoJSON
        "Kerala": ["Thiruvananthapuram", "Ernakulam", "Kozhikode", "Thrissur"], # Ernakulam is usually Kochi in GeoJSON? No, usually Ernakulam.
        "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur"],
        "Maharashtra": ["Greater Bombay", "Pune", "Nagpur", "Nashik", "Thane"], # Mumbai City -> Greater Bombay
        "Manipur": ["West Imphal", "East Imphal", "Thoubal"],
        "Meghalaya": ["East Khasi Hills", "West Garo Hills"],
        "Mizoram": ["Aizawl", "Lunglei"],
        "Nagaland": ["Kohima", "Dimapur"],
        "Odisha": ["Khordha", "Cuttack", "Sundargarh", "Puri"], # Bhubaneswar -> Khordha, Rourkela -> Sundargarh
        "Punjab": ["Ludhiana", "Amritsar", "Jalandhar", "Patiala"],
        "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota"],
        "Sikkim": ["East", "West Sikkim"],
        "Tamil Nadu": [
            "Ariyalur", "Chennai", "Coimbatore", "Cuddalore", "Dharmapuri", "Dindigul", "Erode", 
            "Kancheepuram", "Kanniyakumari", "Karur", "Madurai", "Nagapattinam", "Namakkal", 
            "Nilgiris", "Perambalur", "Pudukkottai", "Ramanathapuram", "Salem", "Sivaganga", 
            "Thanjavur", "Theni", "Thiruvallur", "Thiruvarur", "Thoothukudi", "Tiruchchirappalli", 
            "Tirunelveli Kattabo", "Tiruvannamalai", "Vellore", "Villupuram", "Virudhunagar"
        ],
        "Telangana": ["Hyderabad", "Warangal", "Nizamabad"],
        "Tripura": ["West Tripura", "Dhalai"],
        "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Gautam Buddha Nagar"], # Noida -> GB Nagar
        "Uttaranchal": ["Dehra Dun", "Haridwar", "Naini Tal"],
        "West Bengal": ["Kolkata", "Haora", "Darjiling", "Jalpaiguri"],
        "Delhi": ["Delhi"],
        "Jammu and Kashmir": ["Srinagar", "Jammu", "Anantnag (Kashmir South)"],
        "Ladakh": ["Leh", "Kargil"],
        "Puducherry": ["Puducherry", "Karaikal"],
        "Chandigarh": ["Chandigarh"],
        "Andaman and Nicobar Islands": ["South Andaman"],
        "Dadra and Nagar Haveli and Daman and Diu": ["Daman", "Diu"],
        "Lakshadweep": ["Kavaratti"]
    }

    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    
    data = []
    
    for state, districts in state_districts.items():
        base_state_enrolment = random.randint(1000000, 50000000)
        
        for district in districts:
            # Distribute state enrolment roughly among districts
            dist_base = int(base_state_enrolment / len(districts) * random.uniform(0.8, 1.2))
            
            for year in years:
                # Growth
                growth_factor = 1 + (random.uniform(-0.01, 0.04))
                dist_base = int(dist_base * growth_factor)
                
                updates = int(dist_base * random.uniform(0.05, 0.25))
                rejections = int(updates * random.uniform(0.01, 0.06))
                
                data.append({
                    "State": state,
                    "District": district,
                    "Year": year,
                    "Enrolment": dist_base,
                    "Updates": updates,
                    "Rejections": rejections,
                    "Avg_Age_Enrolled": round(random.uniform(18, 50), 1),
                    "Gender_Ratio_Female": round(random.uniform(900, 1050), 0)
                })
    
    # Also add "Total" rows? No, we will aggregate in the app for flexibility.
    # This simplifies data loader logic.
            
    df = pd.DataFrame(data)
    df.to_csv("d:/AadharHackathon/aadhaar_data.csv", index=False)
    print("Data generated successfully at d:/AadharHackathon/aadhaar_data.csv")

if __name__ == "__main__":
    generate_data()
