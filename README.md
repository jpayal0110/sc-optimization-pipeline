# Supply Chain Allocation Engine

### **Automated Clear-to-Build (CTB) System with FIFO Backlog Management**

![Python](https://img.shields.io/badge/Python-3.10%2B-blue) ![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-green) ![Status](https://img.shields.io/badge/Status-Active-success)

## Project Overview
This project is a Python-based **Supply Chain Analytics System** designed to simulate and optimize the manufacturing "Clear-to-Build" (CTB) process. It addresses a critical problem in semiconductor and hardware operations: **allocating scarce inventory against high demand.**

Unlike simple dashboards, this system functions as an **ETL & Logic Engine**. It generates mock ERP transactional data, identifies component constraints (e.g., shortages in Subcomponents A vs. B), and algorithmically allocates finished goods to customers based on **Strategic Priority (Waterfall)** and **Order Aging (FIFO)**.

## Business Problem Solved
In hardware operations, demand often exceeds supply during ramp-up phases. Operations teams need to answer three questions daily:
1.  **Constraint Analysis:** *Why* can't we build more? (Which subcomponent is the bottleneck?)
2.  **Commitment Logic:** How many units can we effectively promise to the market?
3.  **Allocation Execution:** If we are short, *who* gets the product? (Prioritizing Hyperscalers vs. Retail).

## ⚙️ System Architecture

The system is modularized into two distinct pipelines to mimic real-world Enterprise Systems:

1.  **Data Generator (`generate_data.py`):**
    * Acts as a Mock ERP / Database.
    * Generates probabilistic Supply (Subcomponents) and Demand (Customer Orders).
    * Simulates "Master Data" for Customer Tiers (Strategic, Enterprise, Retail).
    * Outputs timestamped raw CSVs with unique Order IDs.

2.  **Logic Processor (`process_logic.py`):**
    * **Ingestion:** Automatically detects and loads the latest data snapshot.
    * **Transformation (ETL):** Merges transactional demand with Master Data (Segment/Priority).
    * **CTB Engine:** Calculates the "Global Limit" based on the weakest link (min of Subcomponent 1 vs. 2 vs. Prior Lookahead).
    * **Allocation Engine:** Runs a **Multi-Tier Waterfall** algorithm:
        * *Tier Level:* Fills buckets based on Priority (P1 > P2 > P9).
        * *Customer Level:* Fills individual orders using **FIFO (First-In-First-Out)** logic, ensuring backlogs (old orders) are filled before new demand.

##  Key Features
* **Dynamic Constraint Detection:** Identifies whether Subcomponent 1 or 2 is holding back production.
* **Lookahead Logic:** Automatically counts "Next Week's" demand as a requirement for the current week.
* **Waterfall Allocation:** Ensures high-priority customers (e.g., "Data Center") are shielded from shortages affecting lower tiers.
* **FIFO Backlog Filling:** "Time-travels" to fill past-due partial orders when new supply arrives, rather than giving it to new orders.
* **Dual Reporting:**
    * **Executive Summary:** Global Supply vs. Demand balance.
    * **Transactional Report:** Row-level order status (`Full`, `Partial`, `Unfulfilled`).

##  Installation & Usage

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/yourusername/supply-chain-allocation-engine.git](https://github.com/yourusername/supply-chain-allocation-engine.git)
    cd supply-chain-allocation-engine
    ```

2.  **Install Dependencies**
    ```bash
    pip install pandas numpy xlsxwriter
    ```

3.  **Run the Simulation**
    * **Step 1: Generate Data** (Simulates a fresh data dump from SAP/Oracle)
        ```bash
        python generate_data.py
        ```
    * **Step 2: Process Logic** (Runs the Allocation Algorithm)
        ```bash
        python process_logic.py
        ```

## Outputs

The system generates two key reports in the root directory:

1.  **`final_analysis_report.xlsx` (Global View):**
    * Used by: Supply Planners / Executives.
    * Shows: Total Supply A/B, Total Demand, and the calculated "Commit" line.
2.  **`customer_allocation_report.csv` (Execution View):**
    * Used by: Order Management / Sales Operations.
    * Format: Flat transactional file ready for PowerBI/Tableau ingestion.
    * Columns: `Week`, `Order ID`, `Customer`, `Segment`, `Priority`, `Qty Ordered`, `Qty Allocated`, `Status`.

## Future Enhancements
* **Database Integration:** Migration from CSV to **DuckDB** or **Snowflake** for handling millions of rows.
* **Visualization:** Building a **Streamlit** frontend to allow users to adjust "What-If" scenarios (e.g., "What if Supply A increases by 10%?").
* **Containerization:** Dockerizing the application for cloud deployment.
