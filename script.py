import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import pathlib
import xlsxwriter

# ==============================================================================
# ASSUMPTIONS & BUSINESS LOGIC
# ==============================================================================
# 1. Output: Excel with TWO tabs ("Summary", "Component Commit Summary").
# 2. Logic:
#    - Demand Prior: W1 = (Act W1 + Act W2), W2 = Act W3...
#    - Commit: MIN( Cum Supply A, Cum Supply B, Cum Demand Prior )
#    - Backlog: Cum Commit - Cum Demand (Actual)
#    - Constraint: Identifies if A or B caused the limit.
# ==============================================================================

def get_iso_week_str(date_obj: datetime) -> str:
    iso_cal = date_obj.isocalendar()
    return f"{iso_cal.year}-W{iso_cal.week:02d}"

def generate_sample_data(seed: int = 42) -> Tuple[List[Dict], List[Dict]]:
    np.random.seed(seed)
    base_date = datetime(2026, 1, 1)
    
    raw_supply = []
    raw_demand = []
    
    days_to_generate = 30 * 7

    for i in range(days_to_generate):
        curr_date = base_date + timedelta(days=i)
        
        if np.random.random() > 0.1: 
            raw_supply.append({"delivery_date": curr_date, "product_type": "A", "quantity": np.random.randint(10, 50)})
        if np.random.random() > 0.1:
            raw_supply.append({"delivery_date": curr_date, "product_type": "B", "quantity": np.random.randint(10, 60)})
        if np.random.random() > 0.1:
            raw_demand.append({"delivery_date": curr_date, "product_type": "C", "quantity": np.random.randint(10, 90)})

    return raw_supply, raw_demand

def build_supply_df(raw_data: List[Dict]) -> pd.DataFrame:
    if not raw_data: return pd.DataFrame(columns=['week', 'product_type', 'quantity'])
    df = pd.DataFrame(raw_data)
    df['delivery_date'] = pd.to_datetime(df['delivery_date'])
    df['quantity'] = df['quantity'].astype(int)
    df['week'] = df['delivery_date'].apply(get_iso_week_str)
    return df.sort_values(by=['week', 'product_type']).reset_index(drop=True)

def build_demand_df(raw_data: List[Dict]) -> pd.DataFrame:
    if not raw_data: return pd.DataFrame(columns=['week', 'product_type', 'quantity'])
    df = pd.DataFrame(raw_data)
    df['delivery_date'] = pd.to_datetime(df['delivery_date'])
    df['quantity'] = df['quantity'].astype(int)
    df['week'] = df['delivery_date'].apply(get_iso_week_str)
    return df.sort_values(by=['week', 'product_type']).reset_index(drop=True)

def export_to_excel_with_formulas(supply_df: pd.DataFrame, demand_df: pd.DataFrame, output_path: str):
    # --- PREPARE DATA ---
    supply_agg = supply_df.groupby(['week', 'product_type'])['quantity'].sum().unstack(fill_value=0)
    for col in ['A', 'B']:
        if col not in supply_agg.columns: supply_agg[col] = 0
            
    demand_agg = demand_df.groupby(['week', 'product_type'])['quantity'].sum().unstack(fill_value=0)
    if 'C' not in demand_agg.columns: demand_agg['C'] = 0

    master_df = supply_agg.join(demand_agg, how='outer').fillna(0).astype(int)
    master_df = master_df.sort_index()
    
    # Transpose so weeks are columns
    df_act = master_df[['A', 'B', 'C']].T
    weeks = df_act.columns.tolist()
    
    workbook = xlsxwriter.Workbook(output_path)
    
    # Shared Formats
    bold_fmt = workbook.add_format({'bold': True})
    num_fmt = workbook.add_format({'num_format': '#,##0'})
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
    highlight_fmt = workbook.add_format({'bg_color': '#FFFFE0', 'num_format': '#,##0'}) 
    red_text = workbook.add_format({'font_color': '#9C0006', 'bg_color': '#FFC7CE', 'num_format': '#,##0'})
    
    # ==========================================================================
    # SHEET 1: SUMMARY
    # ==========================================================================
    ws_main = workbook.add_worksheet("Summary")
    
    # Rows (0-based)
    ROW_A_ACT = 1
    ROW_B_ACT = 2
    ROW_C_ACT = 3
    ROW_C_PRIOR = 4
    ROW_COMMIT = 5          # Weekly Commit (Delta)
    # Blank Row 6
    ROW_DEMAND_TOT = 7      # Cumulative Demand Actual
    ROW_COMMIT_TOT = 8      # Cumulative Commit Total
    ROW_BACKLOG = 9         # NEW: Backlog (Commit Tot - Demand Tot)
    ROW_CONSTRAINT = 10     # NEW: Constraint Indicator
    
    row_labels_main = {
        ROW_A_ACT: 'A_Supply(Act)',
        ROW_B_ACT: 'B_Supply(Act)',
        ROW_C_ACT: 'C_Demand(Act)',
        ROW_C_PRIOR: 'C_Demand(Prior: Special Logic)',
        ROW_COMMIT: 'C_Commit(Based on demand prior)',
        ROW_DEMAND_TOT: 'Total Demand (Cumulative)',
        ROW_COMMIT_TOT: 'Total Commit (Cumulative)',
        ROW_BACKLOG: 'Cumulative Backlog (Commit - Act Demand)',
        ROW_CONSTRAINT: 'Primary Constraint'
    }
    
    # Write Headers
    ws_main.write(0, 0, "Metric", header_fmt)
    for i, week in enumerate(weeks):
        ws_main.write(0, i + 1, week, header_fmt)
    for r_idx, label in row_labels_main.items():
        ws_main.write(r_idx, 0, label, bold_fmt)
        
    for col_idx, week in enumerate(weeks):
        xl_col = col_idx + 1
        col_letter = xlsxwriter.utility.xl_col_to_name(xl_col)
        
        # 1. Actuals
        ws_main.write_number(ROW_A_ACT, xl_col, master_df.loc[week, 'A'], num_fmt)
        ws_main.write_number(ROW_B_ACT, xl_col, master_df.loc[week, 'B'], num_fmt)
        ws_main.write_number(ROW_C_ACT, xl_col, master_df.loc[week, 'C'], num_fmt)
        
        # 2. Demand Prior
        curr_act_ref = f"{col_letter}{ROW_C_ACT + 1}"
        if col_idx < len(weeks) - 1:
            next_col_letter = xlsxwriter.utility.xl_col_to_name(xl_col + 1)
            next_act_ref = f"{next_col_letter}{ROW_C_ACT + 1}"
            if col_idx == 0: formula_prior = f"={curr_act_ref} + {next_act_ref}"
            else: formula_prior = f"={next_act_ref}"
        else:
            if col_idx == 0: formula_prior = f"={curr_act_ref}"
            else: formula_prior = "0"
        ws_main.write_formula(ROW_C_PRIOR, xl_col, formula_prior, highlight_fmt)

        # 3. Calculation Ranges (Used for Commit & Constraint)
        sum_a = f"SUM(${'B'}{ROW_A_ACT+1}:{col_letter}{ROW_A_ACT+1})"
        sum_b = f"SUM(${'B'}{ROW_B_ACT+1}:{col_letter}{ROW_B_ACT+1})"
        sum_prior = f"SUM(${'B'}{ROW_C_PRIOR+1}:{col_letter}{ROW_C_PRIOR+1})"
        
        # 4. Total Commit (Cumulative Min)
        formula_commit_cum = f"MIN({sum_a}, {sum_b}, {sum_prior})"
        ws_main.write_formula(ROW_COMMIT_TOT, xl_col, f"={formula_commit_cum}", num_fmt)
        
        # 5. Weekly Commit (Delta)
        curr_tot_ref = f"{col_letter}{ROW_COMMIT_TOT + 1}"
        if col_idx == 0:
            formula_weekly = f"={curr_tot_ref}"
        else:
            prev_col_letter = xlsxwriter.utility.xl_col_to_name(xl_col - 1)
            prev_tot_ref = f"{prev_col_letter}{ROW_COMMIT_TOT + 1}"
            formula_weekly = f"={curr_tot_ref} - {prev_tot_ref}"
        ws_main.write_formula(ROW_COMMIT, xl_col, formula_weekly, num_fmt)

        # 6. Total Demand (Actual Cumulative)
        sum_dem_act = f"SUM(${'B'}{ROW_C_ACT+1}:{col_letter}{ROW_C_ACT+1})"
        ws_main.write_formula(ROW_DEMAND_TOT, xl_col, f"={sum_dem_act}", num_fmt)

        # 7. Backlog (Commit Tot - Demand Tot)
        dem_tot_ref = f"{col_letter}{ROW_DEMAND_TOT + 1}"
        ws_main.write_formula(ROW_BACKLOG, xl_col, f"={curr_tot_ref} - {dem_tot_ref}", num_fmt)
        
        # 8. Constraint Logic
        #    IF Commit_Tot == Sum_Prior -> "-" (Unconstrained/Met Target)
        #    ELSE IF Sum_A <= Sum_B -> "Supply A"
        #    ELSE -> "Supply B"
        formula_constraint = f'=IF({curr_tot_ref}={sum_prior}, "-", IF({sum_a}<={sum_b}, "Supply A", "Supply B"))'
        ws_main.write_formula(ROW_CONSTRAINT, xl_col, formula_constraint)

    # Conditional Formatting for Backlog (Red if negative)
    last_col = xlsxwriter.utility.xl_col_to_name(len(weeks))
    backlog_range = f"B{ROW_BACKLOG+1}:{last_col}{ROW_BACKLOG+1}"
    ws_main.conditional_format(backlog_range, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': red_text})
    
    ws_main.freeze_panes(1, 1)

    # ==========================================================================
    # SHEET 2: COMPONENT COMMIT SUMMARY (Supply A)
    # ==========================================================================
    ws_comp = workbook.add_worksheet("Component Commit Summary")
    
    ROW_TARGET_CUM = 1
    ROW_A_CUM = 2
    ROW_A_STANDING = 3
    
    comp_labels = {
        ROW_TARGET_CUM: 'Target (Cum Demand Prior)',
        ROW_A_CUM: 'Supply A (Cumulative)',
        ROW_A_STANDING: 'Supply A Standing (Net)'
    }
    
    green_text = workbook.add_format({'font_color': '#006100', 'bg_color': '#C6EFCE', 'num_format': '#,##0'})
    
    ws_comp.write(0, 0, "Component A Analysis", header_fmt)
    for i, week in enumerate(weeks):
        ws_comp.write(0, i + 1, week, header_fmt)
    for r_idx, label in comp_labels.items():
        ws_comp.write(r_idx, 0, label, bold_fmt)
        
    for col_idx, week in enumerate(weeks):
        xl_col = col_idx + 1
        col_letter = xlsxwriter.utility.xl_col_to_name(xl_col)
        
        # Target (from Summary Sheet)
        sum_target_ref = f"SUM('Summary'!$B${ROW_C_PRIOR+1}:{col_letter}${ROW_C_PRIOR+1})"
        ws_comp.write_formula(ROW_TARGET_CUM, xl_col, f"={sum_target_ref}", num_fmt)
        
        # Supply A (from Summary Sheet)
        sum_a_ref = f"SUM('Summary'!$B${ROW_A_ACT+1}:{col_letter}${ROW_A_ACT+1})"
        ws_comp.write_formula(ROW_A_CUM, xl_col, f"={sum_a_ref}", num_fmt)
        
        # Standing
        curr_target = f"{col_letter}{ROW_TARGET_CUM+1}"
        curr_a = f"{col_letter}{ROW_A_CUM+1}"
        ws_comp.write_formula(ROW_A_STANDING, xl_col, f"={curr_a} - {curr_target}", num_fmt)

    standing_range = f"B{ROW_A_STANDING+1}:{last_col}{ROW_A_STANDING+1}"
    ws_comp.conditional_format(standing_range, {'type': 'cell', 'criteria': '<', 'value': 0, 'format': red_text})
    ws_comp.conditional_format(standing_range, {'type': 'cell', 'criteria': '>=', 'value': 0, 'format': green_text})

    ws_comp.freeze_panes(1, 1)

    workbook.close()
    print(f"[SUCCESS] Excel file saved to: {output_path}")

def main():
    print("--- Supply Chain Analytics: Full Suite ---")
    
    raw_supply, raw_demand = generate_sample_data(seed=2026)
    df_supply = build_supply_df(raw_supply)
    df_demand = build_demand_df(raw_demand)
    
    output_file = pathlib.Path('weekly_summary_live.xlsx')
    export_to_excel_with_formulas(df_supply, df_demand, str(output_file))
    print(f"[INFO] Open {output_file} to view Backlog and Constraints.")

if __name__ == "__main__":
    main()