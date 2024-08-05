import os
import csv
from datetime import datetime

def load_top_addresses():
    file_path = os.path.join('TopAddy', 'data', 'top_avax_addresses.csv')
    addresses = {}
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                addresses[row['Address'].lower()] = {
                    'balance': float(row['Balance (AVAX)']),
                    'category': row['Category'],
                    'notes': row['Notes']
                }
    except FileNotFoundError:
        print(f"Warning: {file_path} not found. Run setup_topaddy_structure() to create it.")
    return addresses

def setup_topaddy_structure():
    base_dir = "TopAddy"
    subdirs = ["data", "scripts"]
    
    # Create subdirectories
    for subdir in subdirs:
        os.makedirs(os.path.join(base_dir, subdir), exist_ok=True)
    
    # Create a template CSV file
    template_file = os.path.join(base_dir, "data", "top_avax_addresses.csv")
    with open(template_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Address", "Balance (AVAX)", "Category", "Notes"])
        # Add a few example rows
        writer.writerow(["0x1234...", "1000", "Exchange", "Example exchange hot wallet"])
        writer.writerow(["0x5678...", "5000", "DeFi Protocol", "Example DeFi treasury"])
    
    # Create README file
    readme_content = f"""# Top Addresses

This directory contains manually curated data of top AVAX addresses.

- `data/`: Contains the CSV data of top addresses.
- `scripts/`: Contains scripts for managing and analyzing address data.

To add or update addresses, edit the 'top_avax_addresses.csv' file in the data directory.

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(os.path.join(base_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    print("TopAddy structure updated successfully!")
    print(f"A template CSV file has been created at {template_file}")
    print("You can now start adding top addresses to this file manually.")

def update_address(address, balance, category, notes):
    file_path = os.path.join('TopAddy', 'data', 'top_avax_addresses.csv')
    temp_file = os.path.join('TopAddy', 'data', 'temp_addresses.csv')
    address_found = False

    with open(file_path, 'r') as input_file, open(temp_file, 'w', newline='') as output_file:
        reader = csv.DictReader(input_file)
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            if row['Address'].lower() == address.lower():
                row['Balance (AVAX)'] = str(balance)
                row['Category'] = category
                row['Notes'] = notes
                address_found = True
            writer.writerow(row)

        if not address_found:
            writer.writerow({
                'Address': address,
                'Balance (AVAX)': str(balance),
                'Category': category,
                'Notes': notes
            })

    os.replace(temp_file, file_path)
    print(f"Address {address} {'updated' if address_found else 'added'} successfully.")

if __name__ == "__main__":
    setup_topaddy_structure()
    
    # Example usage of update_address function
    # update_address("0x9876...", 2000, "Whale", "Large individual holder")