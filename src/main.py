# src/main.py

import customtkinter as ctk
import logging # Import logging
from pathlib import Path # For log file path

from src.config import AppConfig
from src.extractor import Extractor
from src.converter import Converter
from src.ui import AppUI
from src.utils import setup_logging # Import setup_logging

def main():
    # Setup logging first
    log_dir = Path("./logs")
    log_file = log_dir / "app.log"
    setup_logging(log_file=log_file, level=logging.INFO)
    logger = logging.getLogger(__name__) # Get logger for this module
    logger.info("Application starting...")

    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    config = AppConfig()
    extractor = Extractor(config)
    converter = Converter(config)

    app = AppUI(config, extractor, converter)
    app.mainloop()

    logger.info("Application closed.")

if __name__ == "__main__":
    main()