import os
import random
import pandas as pd

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def generate_retail_sales():
    path = os.path.join(DATA_DIR, "retail_sales.csv")
    if os.path.exists(path):
        return
        
    random.seed(42)
    rows = []
    
    # Base names for fuzzy matching
    clients = ["Rahul Patel", "Alice Smith", "Bob Jones", "David Miller", "Emma Wilson", "Michael Brown"]
    regions = ["East", "West", "North", "South"]
    
    for i in range(550):
        order_id = f"ORD-{1000 + i}"
        
        # Inject fuzzy duplicate variations for Rahul Patel (Client ID / Name)
        if i % 40 == 0:
            client = "Rahul Patel"
        elif i % 40 == 1:
            client = "Rahul K Patel"
        elif i % 40 == 2:
            client = "R Patel"
        elif i % 40 == 3:
            client = "Rahulk Patel"
        else:
            client = random.choice(clients[1:])
            
        # Inconsistent region casing
        region = random.choice(regions)
        if i % 15 == 0:
            region = region.upper()
        elif i % 15 == 1:
            region = region.lower()
            
        # Missing values (Completeness issues)
        phone = f"98765{random.randint(10000, 99999)}"
        if i % 12 == 0:
            phone = ""
            
        # Missing values and anomalies in Revenue
        revenue_val = random.randint(50, 5000)
        revenue = str(revenue_val)
        if i % 10 == 0:
            revenue = ""  # null values
        elif i % 25 == 0:
            revenue = f"${revenue_val}.00"  # string formatting issue
        elif i % 50 == 0:
            revenue = f"-{revenue_val}"  # negative revenue (anomaly)
            
        # Extreme statistical outlier
        if i == 250:
            revenue = "1250000"  # massive outlier GPA / Revenue
            
        # Date format issue
        order_date = f"2026-08-{random.randint(1, 28):02d}"
        if i % 30 == 0:
            order_date = "invalid-date-format"
            
        rows.append({
            "OrderID": order_id,
            "Client": client,
            "Phone": phone,
            "Region": region,
            "Revenue": revenue,
            "OrderDate": order_date
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"Generated retail_sales.csv with {len(df)} rows.")

def generate_customer_churn():
    path = os.path.join(DATA_DIR, "customer_churn.csv")
    if os.path.exists(path):
        return
        
    random.seed(43)
    rows = []
    
    # Class imbalance: ~72% non-churn (0), ~28% churn (1)
    churn_labels = [0] * 72 + [1] * 28
    
    for i in range(600):
        # High cardinality ID
        cust_id = f"CUST-ID-{i:05d}-{random.randint(10, 99)}"
        
        churn = random.choice(churn_labels)
        
        # Target leakage: CancellationDate is present ONLY when churn is 1
        cancel_date = ""
        if churn == 1:
            cancel_date = f"2026-07-{random.randint(1, 28):02d}"
            
        # Tenure (missing values)
        tenure = random.randint(1, 72)
        if i % 15 == 0:
            tenure = ""
            
        # Monthly charges (missing values)
        monthly_charges = round(random.uniform(20.0, 150.0), 2)
        if i % 20 == 0:
            monthly_charges = ""
            
        rows.append({
            "CustomerID": cust_id,
            "Tenure": tenure,
            "MonthlyCharges": monthly_charges,
            "CancellationDate": cancel_date,
            "Churn": churn
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"Generated customer_churn.csv with {len(df)} rows.")

def generate_inventory_logistics():
    path = os.path.join(DATA_DIR, "inventory_logistics.csv")
    if os.path.exists(path):
        return
        
    random.seed(44)
    rows = []
    
    categories = ["Electronics", "Appliances", "Logistics", "Stationery"]
    
    for i in range(520):
        # Product ID duplicate issue
        item_number = f"SKU-{2000 + (i // 2 if i % 60 == 0 else i)}"
        
        # Category spelling variants
        category = random.choice(categories)
        if i % 20 == 0:
            category = category + " "  # trailing whitespace
        elif i % 20 == 1:
            category = category.lower()
            
        # Negative quantity (anomaly)
        pallet_count = random.randint(5, 500)
        if i % 25 == 0:
            pallet_count = random.randint(-50, -1)
            
        # Missing supplier (completeness issue)
        supplier = f"Supplier-{random.randint(1, 10)}"
        if i % 14 == 0:
            supplier = ""
            
        # Invalid dates
        last_updated = f"2026-08-{random.randint(1, 28):02d}"
        if i % 40 == 0:
            last_updated = ""
            
        rows.append({
            "ItemNumber": item_number,
            "ItemName": f"Product-{i}",
            "PackSize": random.choice([6, 12, 24]),
            "PalletCount": pallet_count,
            "SupplierCode": supplier,
            "LastUpdated": last_updated
        })
        
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    print(f"Generated inventory_logistics.csv with {len(df)} rows.")

def generate_demo_merge_files():
    # 1. CRM.xlsx
    crm_path = os.path.join(DATA_DIR, "CRM.xlsx")
    crm_rows = []
    # 2. Tally.xlsx
    tally_path = os.path.join(DATA_DIR, "Tally.xlsx")
    tally_rows = []
    # 3. POS.csv
    pos_path = os.path.join(DATA_DIR, "POS.csv")
    pos_rows = []
    # 4. Sales.xlsx
    sales_path = os.path.join(DATA_DIR, "Sales.xlsx")
    sales_rows = []
    
    # Standard entities to merge
    entities = [
        # Entity 1: Rahul Patel
        {"crm": ("CUST-1001", "Rahul Patel", "9876543210", "rahul.patel@gmail.com", "2026-08-20"),
         "tally": ("TALLY-1001", "RAHUL PATEL", "9876543211", "24AAAAP1234A1Z1", "54000"),
         "pos": ("POS-5001", "Rahul K Patel", "9876543210", "1500", "2026-08-21"),
         "sales": ("ORD-8001", "R Patel", "9876543210", "1800", "2026-08-23", "System", "Follow up needed")},
        # Entity 2: Michael Brown
        {"crm": ("CUST-1002", "Michael Brown", "9876583563", "michael@brown.com", "2026-08-22"),
         "tally": ("TALLY-1002", "Michael Brown", "9876583563", "24AAAAP5678B1Z2", "32000"),
         "pos": ("POS-5002", "Michael Brown", "9876583563", "2200", "2026-08-22"),
         "sales": ("ORD-8002", "Michael Brown", "9876583563", "2400", "2026-08-22", "System", "Normal")},
        # Entity 3: David Miller
        {"crm": ("CUST-1003", "David Miller", "9876530926", "david@miller.com", "2026-08-19"),
         "tally": ("TALLY-1003", "David Miller", "9876530926", "24AAAAP9012C1Z3", "12000"),
         "pos": ("POS-5003", "David Miller", "9876530926", "980", "2026-08-23"),
         "sales": ("ORD-8003", "David Miller", "9876530926", "1100", "2026-08-21", "Admin", "VIP")},
        # Entity 4: Alice Smith
        {"crm": ("CUST-1004", "Alice Smith", "9876522676", "alice@smith.com", "2026-08-23"),
         "tally": ("TALLY-1004", "Alice Smith", "9876522676", "24AAAAP3456D1Z4", "28000"),
         "pos": ("POS-5004", "Alice Smith", "9876522676", "1240", "2026-08-20"),
         "sales": ("ORD-8004", "Alice Smith", "9876522676", "1500", "2026-08-20", "System", "Check payment")},
        # Entity 5: Bob Jones
        {"crm": ("CUST-1005", "Bob Jones", "9876599999", "bob@jones.com", "2026-08-15"),
         "tally": ("TALLY-1005", "Bob Jones", "9876599999", "24AAAAP7890E1Z5", "15000"),
         "pos": ("POS-5005", "Bob Jones", "9876599999", "450", "2026-08-18"),
         "sales": ("ORD-8005", "Bob Jones", "9876599999", "800", "2026-08-19", "Admin", "New lead")}
    ]
    
    # Add matching standard rows
    for ent in entities:
        crm_rows.append({
            "Customer_ID": ent["crm"][0],
            "Customer_Name": ent["crm"][1],
            "Phone": ent["crm"][2],
            "Email": ent["crm"][3],
            "Last_Login": ent["crm"][4]
        })
        tally_rows.append({
            "Party_ID": ent["tally"][0],
            "Party_Name": ent["tally"][1],
            "Mobile": ent["tally"][2],
            "GSTIN": ent["tally"][3],
            "Sales": ent["tally"][4]
        })
        pos_rows.append({
            "POS_ID": ent["pos"][0],
            "Customer": ent["pos"][1],
            "Contact": ent["pos"][2],
            "Bill_Amount": ent["pos"][3],
            "Invoice_Date": ent["pos"][4]
        })
        sales_rows.append({
            "OrderID": ent["sales"][0],
            "Customer Name": ent["sales"][1],
            "Phone": ent["sales"][2],
            "Revenue": ent["sales"][3],
            "OrderDate": ent["sales"][4],
            "Created_By": ent["sales"][5],
            "Internal_Notes": ent["sales"][6]
        })
        
    # Generate additional unique records to simulate larger datasets
    random.seed(100)
    names = ["Amit Shah", "Neha Patel", "John Doe", "Jane Roe", "Vijay Kumar", "Sanjay Sharma", "Sunita Rao", "Priya Singh", "Ramesh Verma", "Karan Johar"]
    
    for i in range(15):
        # CRM unique
        crm_rows.append({
            "Customer_ID": f"CUST-200{i}",
            "Customer_Name": random.choice(names),
            "Phone": f"98250{random.randint(10000, 99999)}",
            "Email": f"user{i}@crm.com",
            "Last_Login": f"2026-08-{random.randint(1, 28):02d}"
        })
        # Tally unique
        tally_rows.append({
            "Party_ID": f"TALLY-200{i}",
            "Party_Name": random.choice(names),
            "Mobile": f"98250{random.randint(10000, 99999)}",
            "GSTIN": f"24AAAAP{random.randint(1000, 9999)}F1Z{random.randint(0, 9)}",
            "Sales": random.randint(1000, 45000)
        })
        # POS unique
        pos_rows.append({
            "POS_ID": f"POS-700{i}",
            "Customer": random.choice(names),
            "Contact": f"98250{random.randint(10000, 99999)}",
            "Bill_Amount": random.randint(100, 5000),
            "Invoice_Date": f"2026-08-{random.randint(1, 28):02d}"
        })
        # Sales unique
        sales_rows.append({
            "OrderID": f"ORD-900{i}",
            "Customer Name": random.choice(names),
            "Phone": f"98250{random.randint(10000, 99999)}",
            "Revenue": random.randint(500, 8000),
            "OrderDate": f"2026-08-{random.randint(1, 28):02d}",
            "Created_By": random.choice(["Admin", "System", "Operator"]),
            "Internal_Notes": random.choice(["Normal", "Regular client", "Needs review", "Refund request"])
        })
        
    # Save files
    pd.DataFrame(crm_rows).to_excel(crm_path, index=False)
    pd.DataFrame(tally_rows).to_excel(tally_path, index=False)
    pd.DataFrame(pos_rows).to_csv(pos_path, index=False)
    pd.DataFrame(sales_rows).to_excel(sales_path, index=False)
    print("Generated CRM.xlsx, Tally.xlsx, POS.csv, and Sales.xlsx for merge testing.")
    
    # Generate Reconciliation files
    generate_reconciliation_files()

def generate_reconciliation_files():
    inv_path = os.path.join(DATA_DIR, "Invoices.xlsx")
    pay_path = os.path.join(DATA_DIR, "Payments.xlsx")
    inventory_path = os.path.join(DATA_DIR, "Inventory.xlsx")
    
    # Invoices
    inv_data = [
        {"Invoice_No": "INV1025", "Customer_Name": "Rahul Patel", "Amount": 12500, "Date": "2026-08-20"},
        {"Invoice_No": "INV1026", "Customer_Name": "Alice Smith", "Amount": 15000, "Date": "2026-08-21"},
        {"Invoice_No": "INV1027", "Customer_Name": "Bob Jones", "Amount": 8000, "Date": "2026-08-22"},
        {"Invoice_No": "INV1028", "Customer_Name": "David Miller", "Amount": 5000, "Date": "2026-08-23"},
        {"Invoice_No": "INV1029", "Customer_Name": "Emma Wilson", "Amount": 9500, "Date": "2026-08-24"}
    ]
    
    # Payments
    pay_data = [
        {"Payment_Ref": "INV1025", "Customer": "RAHUL P", "Paid_Amount": 12000, "Payment_Date": "2026-08-21"},
        {"Payment_Ref": "INV1026", "Customer": "Alice Smith", "Paid_Amount": 15000, "Payment_Date": "2026-08-22"},
        {"Payment_Ref": "INV-1027", "Customer": "Bob Jones", "Paid_Amount": 8000, "Payment_Date": "2026-08-22"},
        {"Payment_Ref": "PAY8990", "Customer": "David Miller", "Paid_Amount": 5000, "Payment_Date": "2026-08-24"},
        {"Payment_Ref": "PAY9999", "Customer": "Unknown Customer", "Paid_Amount": 2500, "Payment_Date": "2026-08-24"}
    ]
    
    # Inventory
    inventory_data = [
        {"SKU": "SKU001", "Product_Name": "Samsung Galaxy S24", "Stock_Remaining": 80},
        {"SKU": "SKU002", "Product_Name": "iPhone 15 Pro", "Stock_Remaining": 3},
        {"SKU": "SKU003", "Product_Name": "Dell XPS 13", "Stock_Remaining": -2},
        {"SKU": "SKU004", "Product_Name": "HP Spectre x360", "Stock_Remaining": 15},
        {"SKU": "SKU005", "Product_Name": "Lenovo ThinkPad X1", "Stock_Remaining": 22}
    ]
    
    pd.DataFrame(inv_data).to_excel(inv_path, index=False)
    pd.DataFrame(pay_data).to_excel(pay_path, index=False)
    pd.DataFrame(inventory_data).to_excel(inventory_path, index=False)
    print("Generated Invoices.xlsx, Payments.xlsx, and Inventory.xlsx for reconciliation testing.")

if __name__ == "__main__":
    generate_retail_sales()
    generate_customer_churn()
    generate_inventory_logistics()
    generate_demo_merge_files()
