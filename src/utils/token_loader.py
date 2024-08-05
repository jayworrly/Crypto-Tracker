import os

def load_token_addresses(directory='avalanche_eco'):  # Specify the directory relative to the src folder
    token_labels = {}
    try:
        # Calculate the base path of the current script (token_loader.py)
        base_path = os.path.dirname(os.path.abspath(__file__))  # Absolute path of the current file

        # Calculate the target path to the 'avalanche_eco' directory
        target_path = os.path.join(base_path, '..', directory)  # Navigate up one level and into 'avalanche_eco'

        # Normalize the path to make it platform-independent
        target_path = os.path.normpath(target_path)

        # Iterate through each file in the target directory
        for filename in os.listdir(target_path):
            file_path = os.path.join(target_path, filename)
            if os.path.isfile(file_path):
                # Open each file and read line by line
                with open(file_path, 'r') as file:
                    for line in file:
                        line = line.strip()
                        if line:  # Ensure the line is not empty
                            # Split each line into address and label
                            address, label = line.split(',')
                            # Add the address and label to the dictionary
                            token_labels[address.strip().lower()] = label.strip()
    except Exception as e:
        print(f"Error loading token addresses: {e}")
    
    return token_labels

