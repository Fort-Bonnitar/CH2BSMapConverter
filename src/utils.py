# src/utils.py

import logging
from pathlib import Path
from typing import Optional

def setup_logging(log_file: Optional[Path] = None, level=logging.INFO):
    """
    Sets up a basic logging configuration for the application.

    Logs to both console (INFO level) and optionally to a file (DEBUG level).
    """
    # Create a root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Prevent duplicate handlers if called multiple times
    if not root_logger.handlers:
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        if log_file:
            # Ensure the log directory exists
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            # File handler
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG) # Log more verbosely to file
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)

    logging.info("Logging setup complete.")

# You can add other utility functions here as they become apparent
# For example, a more robust file cleaner than simple shutil.rmtree for specific patterns
# def safe_delete_directory(path: Path):
#     if path.exists() and path.is_dir():
#         try:
#             shutil.rmtree(path)
#             logging.debug(f"Successfully deleted directory: {path}")
#         except OSError as e:
#             logging.error(f"Error deleting directory {path}: {e}")