# utils/helpers.py

import logging

def setup_logging(log_level, log_file='avaxwhale.log'):
    """Set up logging configuration."""
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level),
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),  # Log to a file
            logging.StreamHandler()  # Also log to console
        ]
    )

