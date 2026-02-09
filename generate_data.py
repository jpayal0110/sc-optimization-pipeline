import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pathlib
import random
import uuid

# --- MASTER DATA ---
CUSTOMER_MASTER = [
    {"Customer": "Microsoft", "Priority": 1, "Segment": "Data Center"},
    {"Customer": "Meta",      "Priority": 1, "Segment": "Data Center"},
    {"Customer": "Tesla",     "Priority": 2, "Segment": "Automotive"},
    {"Customer": "Siemens",   "Priority": 3, "Segment": "Healthcare"},
    {"Customer": "Foxconn",   "Priority": 4, "Segment": "Industrial"},
    {"Customer": "Dell",      "Priority": 5, "Segment": "Pro Viz"},
    {"Customer": "ASUS",      "Priority": 7, "Segment": "Gaming OEM"},
    {"Customer": "Best Buy",  "Priority": 9, "Segment": "Gaming Retail"},
]

def get_iso_week(date_obj):
    iso_cal = date_obj.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"

def generate_csvs():
    np.random.seed(42)
    base_date = datetime(2026, 1, 1)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = pathlib.Path('./data_inputs')
    output_dir.mkdir(exist_ok=True)

    raw_supply = []
    raw_demand = []
    days = 30 * 7

    for i in range(days):
        curr_date = base_date + timedelta(days=i)
        curr_week = get_iso_week(curr_date)
        
        # Supply Generation
        if np.random.random() > 0.1: 
            raw_supply.append({
                "week": curr_week,              # <--- 1st Column
                "delivery_date": curr_date,
                "product_type": "Subcomponent_1", 
                "quantity": np.random.randint(10, 50)
            })
        if np.random.random() > 0.1:
            raw_supply.append({
                "week": curr_week,              # <--- 1st Column
                "delivery_date": curr_date,
                "product_type": "Subcomponent_2", 
                "quantity": np.random.randint(10, 60)
            })
            
        # Demand Generation
        if np.random.random() > 0.1:
            cust = random.choice(CUSTOMER_MASTER)
            raw_demand.append({
                "week": curr_week,              # <--- 1st Column
                "delivery_date": curr_date, 
                "order_id": f"ORD-{uuid.uuid4().hex[:6].upper()}",
                "product_type": "Advanced_Chip", 
                "quantity": np.random.randint(10, 90),
                "Customer": cust["Customer"] 
            })

    # Create DataFrames
    df_supply = pd.DataFrame(raw_supply)
    df_demand = pd.DataFrame(raw_demand)
    
    # Enforce Column Order (Week First)
    supply_cols = ["week", "delivery_date", "product_type", "quantity"]
    demand_cols = ["week", "delivery_date", "order_id", "Customer", "product_type", "quantity"]
    
    df_supply = df_supply[supply_cols]
    df_demand = df_demand[demand_cols]

    # Save Files
    df_supply.to_csv(output_dir / f"supply_data_{timestamp}.csv", index=False)
    df_demand.to_csv(output_dir / f"demand_data_{timestamp}.csv", index=False)
    pd.DataFrame(CUSTOMER_MASTER).to_csv(output_dir / "master_customer_tiers.csv", index=False)
    
    print(f"[SUCCESS] Data Generated.")
    print(f" -> Week is now the 1st column in generated CSVs.")

if __name__ == "__main__":
    generate_csvs()