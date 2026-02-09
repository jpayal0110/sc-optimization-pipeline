import pandas as pd
import numpy as np
import glob
import os

def get_latest_file(pattern, directory='./data_inputs'):
    files = glob.glob(os.path.join(directory, pattern))
    if not files: raise FileNotFoundError(f"No files found for {pattern}")
    return max(files, key=os.path.getctime)

def process_supply_chain_data():
    print("--- Starting Processor (FIFO Backlog Logic) ---")
    
    # 1. LOAD DATA
    file_supply = get_latest_file("supply_data_*.csv")
    file_demand = get_latest_file("demand_data_*.csv")
    file_master = "./data_inputs/master_customer_tiers.csv"
    
    df_supply = pd.read_csv(file_supply)
    df_demand = pd.read_csv(file_demand)
    df_master = pd.read_csv(file_master)
    
    # 2. MERGE MASTER DATA
    df_demand = df_demand.merge(df_master, on='Customer', how='left')
    df_demand['Priority'] = df_demand['Priority'].fillna(99)
    df_demand['Segment'] = df_demand['Segment'].fillna("Unknown")

    # 3. GLOBAL CONSTRAINT (Total Available Supply Curve)
    supply_agg = df_supply.groupby(['week', 'product_type'])['quantity'].sum().unstack(fill_value=0)
    for c in ['Subcomponent_1', 'Subcomponent_2']: 
        if c not in supply_agg: supply_agg[c] = 0
    
    demand_global = df_demand.groupby(['week', 'product_type'])['quantity'].sum().unstack(fill_value=0)
    if 'Advanced_Chip' not in demand_global: demand_global['Advanced_Chip'] = 0

    master = supply_agg.join(demand_global, how='outer').fillna(0).astype(int).sort_index()
    
    # Calculate Cumulative Supply Limit
    master['Next_Week_Demand'] = master['Advanced_Chip'].shift(-1).fillna(0)
    master['Demand_Prior'] = master['Advanced_Chip'] + master['Next_Week_Demand']
    master['Total_Commit_Cum'] = master[['Subcomponent_1', 'Subcomponent_2', 'Demand_Prior']].cumsum().min(axis=1)

    # ==========================================================================
    # 4. FIFO ALLOCATION LOGIC
    # ==========================================================================
    print("Calculating FIFO Allocation...")
    
    final_rows = []
    
    # We use the cumulative supply curve to determine total limits
    remaining_supply_curve = master['Total_Commit_Cum'].copy()
    
    # Sort Priorities to ensure Tier 1 eats first
    priorities = sorted(df_demand['Priority'].unique())
    
    for p in priorities:
        # --- A. TIER LEVEL (How much does the Tier get?) ---
        df_p = df_demand[df_demand['Priority'] == p]
        
        # Calculate Tier Demand Curve
        tier_demand_raw = df_p.groupby('week')['quantity'].sum()
        tier_demand_cum = tier_demand_raw.reindex(master.index, fill_value=0).cumsum()
        
        # Calculate Tier Allocation Curve (The Limit)
        tier_allocated_cum = np.minimum(tier_demand_cum, remaining_supply_curve)
        
        # Calculate Global Fill Rate for this Tier (Total Given / Total Asked)
        total_tier_demand = tier_demand_cum.iloc[-1] if len(tier_demand_cum) > 0 else 0
        total_tier_alloc = tier_allocated_cum.iloc[-1] if len(tier_allocated_cum) > 0 else 0
        
        if total_tier_demand > 0:
            tier_global_rate = total_tier_alloc / total_tier_demand
        else:
            tier_global_rate = 1.0

        # --- B. CUSTOMER LEVEL (Pour into Oldest Orders First) ---
        tier_customers = df_p['Customer'].unique()
        
        for cust in tier_customers:
            # 1. CRITICAL STEP: SORT ORDERS BY WEEK (Oldest First)
            # This ensures Week 1 Backlog is prioritized over Week 3 New Orders
            cust_orders = df_p[df_p['Customer'] == cust].sort_values(by=['week', 'order_id'])
            
            # 2. Calculate Customer's Total "Bank Account" of Chips
            # They get their fair share (Pro-Rata) of the Tier's allocation
            total_cust_demand = cust_orders['quantity'].sum()
            total_cust_alloc_pool = int(total_cust_demand * tier_global_rate)
            
            # 3. Pour the pool into the sorted orders
            chips_in_bucket = total_cust_alloc_pool
            
            for _, row in cust_orders.iterrows():
                qty_ordered = row['quantity']
                
                # Take from bucket
                if chips_in_bucket >= qty_ordered:
                    qty_given = qty_ordered
                    chips_in_bucket -= qty_ordered
                    status = "Full"
                else:
                    qty_given = chips_in_bucket
                    chips_in_bucket = 0 # Bucket empty
                    
                    if qty_given == 0: status = "Unfulfilled"
                    else: status = "Partial"
                
                final_rows.append({
                    "week": row['week'],
                    "order_id": row['order_id'],
                    "customer_name": row['Customer'],
                    "market_segment": row['Segment'],
                    "priority": row['Priority'],
                    "quantity": qty_ordered,
                    "allocated_qty": qty_given,
                    "status": status
                })
        
        # Deduct this Tier's consumption from the Global Supply for the next Tier
        remaining_supply_curve = remaining_supply_curve - tier_allocated_cum

    # 5. SAVE REPORT
    df_final = pd.DataFrame(final_rows)
    
    # Enforce Column Order
    output_cols = ["week", "order_id", "customer_name", "market_segment", "priority", "quantity", "allocated_qty", "status"]
    df_final = df_final[output_cols]
    
    # Sort Final Report for readability
    df_final = df_final.sort_values(by=['week', 'priority', 'customer_name'])
    
    output_csv = 'customer_allocation_report.csv'
    df_final.to_csv(output_csv, index=False)
    print(f"[SUCCESS] Flat Report saved: {output_csv}")
    print(f"   -> Logic: Week 1 Partials are filled before Week 3 New Orders.")

if __name__ == "__main__":
    process_supply_chain_data()