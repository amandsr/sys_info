#!/usr/bin/env python

import pandas as pd
import json
import sys

def main():
    """
    Reads an Excel file and prints a JSON-formatted Ansible dynamic inventory.
    """
    # --- Configuration (MODIFIED FOR YOUR COLUMNS) ---
    excel_file = 'servers.xlsx'          # The name of your Excel file
    hostname_col = 'Computer Name'       # Changed from 'Hostname'
    ip_address_col = 'IPv4 Address'      # Changed from 'IP Address'
    # Use only 'Source ID' for creating Ansible groups
    group_cols = ['Source ID']           

    # Initialize the main inventory structure
    inventory = {
        "_meta": {
            "hostvars": {}
        }
    }

    try:
        # Read the Excel file into a pandas DataFrame
        df = pd.read_excel(excel_file)
    except FileNotFoundError:
        print(json.dumps({"_error": f"Excel file '{excel_file}' not found."}, indent=4))
        sys.exit(1)

    # Process each row in the spreadsheet
    for index, row in df.iterrows():
        # Clean up column values
        hostname = str(row[hostname_col]).strip()
        ip_address = str(row[ip_address_col]).strip()
        
        # Add the host's variables to the _meta section
        inventory["_meta"]["hostvars"][hostname] = {
            "ansible_host": ip_address
        }

        # Add the host to its respective groups from the 'Source ID' column
        for col in group_cols:
            group_name = str(row[col]).strip().lower()
            
            if group_name not in inventory:
                inventory[group_name] = {"hosts": []}
            
            inventory[group_name]["hosts"].append(hostname)
            
    # When Ansible requests the list, print the inventory as a JSON string
    if len(sys.argv) == 2 and sys.argv[1] == '--list':
        print(json.dumps(inventory, indent=4))
    else:
        print(json.dumps({}))

if __name__ == "__main__":
    main()
