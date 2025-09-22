# src/ui.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading # For running conversion in a separate thread
import os
from typing import Optional

from src.config import AppConfig
from src.extractor import Extractor
from src.converter import Converter
from src.models import CloneHeroSongMetadata # Needed for type hints in UI


class AppUI(ctk.CTk):
    def __init__(self, config: AppConfig, extractor: Extractor, converter: Converter):
        super().__init__()

        self.config = config
        self.extractor = extractor
        self.converter = converter

        self.title("Clone Hero to Beat Saber Map Converter")
        self.geometry("800x600")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # Allow scrollable frame to expand

        self._create_widgets()
        self._load_current_settings()

    def _create_widgets(self):
        # --- Frame for ZIP selection ---
        self.zip_frame = ctk.CTkFrame(self)
        self.zip_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.zip_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.zip_frame, text="Clone Hero ZIP(s):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.zip_entry = ctk.CTkEntry(self.zip_frame, placeholder_text="Select one or more Clone Hero song ZIP files...")
        self.zip_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.zip_button = ctk.CTkButton(self.zip_frame, text="Browse", command=self._browse_zips)
        self.zip_button.grid(row=0, column=2, padx=5, pady=5)
        
        # Listbox to display selected ZIPs
        ctk.CTkLabel(self.zip_frame, text="Selected ZIP Files:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.zip_list_frame = ctk.CTkScrollableFrame(self.zip_frame, height=100)
        self.zip_list_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self.selected_zip_paths = [] # Store Path objects
        self.zip_labels = [] # To hold references to CtkLabels in the scrollable frame
        self.update_zip_list_display()


        # --- Frame for Configuration ---
        self.config_frame = ctk.CTkFrame(self)
        self.config_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.config_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.config_frame, text="Output Directory:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.output_dir_entry = ctk.CTkEntry(self.config_frame)
        self.output_dir_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.output_dir_button = ctk.CTkButton(self.config_frame, text="Browse", command=self._browse_output_dir)
        self.output_dir_button.grid(row=0, column=2, padx=5, pady=5)

        ctk.CTkLabel(self.config_frame, text="Audio Target Format:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.audio_format_optionmenu = ctk.CTkOptionMenu(self.config_frame, values=["ogg", "wav"])
        self.audio_format_optionmenu.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        self.audio_format_optionmenu.set(self.config.audio_target_format) # Set initial value

        ctk.CTkLabel(self.config_frame, text="Delete Temp Files:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.delete_temp_checkbox = ctk.CTkCheckBox(self.config_frame, text="")
        self.delete_temp_checkbox.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        if self.config.delete_temp_files:
            self.delete_temp_checkbox.select()
        else:
            self.delete_temp_checkbox.deselect()

        # Difficulty mapping display (read-only for now, could be editable later)
        ctk.CTkLabel(self.config_frame, text="Difficulty Mapping (CH numeric -> BS):", anchor="w").grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        
        # Scrollable frame for difficulty mapping
        self.difficulty_map_scroll_frame = ctk.CTkScrollableFrame(self.config_frame, height=80)
        self.difficulty_map_scroll_frame.grid(row=4, column=0, columnspan=3, padx=5, pady=5, sticky="ew")
        self._update_difficulty_map_display()
        
        self.save_config_button = ctk.CTkButton(self.config_frame, text="Save Settings", command=self._save_settings)
        self.save_config_button.grid(row=5, column=0, columnspan=3, padx=5, pady=10)


        # --- Conversion Control and Status ---
        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=2, column=0, padx=10, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure(0, weight=1)

        self.start_button = ctk.CTkButton(self.control_frame, text="Start Conversion", command=self._start_conversion_thread)
        self.start_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")

        self.progress_bar = ctk.CTkProgressBar(self.control_frame)
        self.progress_bar.grid(row=1, column=0, padx=5, pady=5, sticky="ew")
        self.progress_bar.set(0) # Initialize to 0%

        self.status_label = ctk.CTkLabel(self.control_frame, text="Ready.", wraplength=780)
        self.status_label.grid(row=2, column=0, padx=5, pady=5, sticky="ew")

    def _load_current_settings(self):
        """Loads settings from the config and updates UI elements."""
        self.output_dir_entry.delete(0, ctk.END)
        self.output_dir_entry.insert(0, str(self.config.output_directory))
        
        self.audio_format_optionmenu.set(self.config.audio_target_format)
        
        if self.config.delete_temp_files:
            self.delete_temp_checkbox.select()
        else:
            self.delete_temp_checkbox.deselect()
        
        self._update_difficulty_map_display()

    def _save_settings(self):
        """Saves current UI settings to the config."""
        new_output_dir = Path(self.output_dir_entry.get())
        if not new_output_dir.exists():
            try:
                new_output_dir.mkdir(parents=True, exist_ok=True)
                self.config.set_setting("output_directory", str(new_output_dir))
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create output directory: {e}")
                self._update_status(f"Error: Failed to create output directory: {e}", "red")
                return
        else:
            self.config.set_setting("output_directory", str(new_output_dir))

        self.config.set_setting("audio_target_format", self.audio_format_optionmenu.get())
        self.config.set_setting("delete_temp_files", self.delete_temp_checkbox.get() == 1)
        
        messagebox.showinfo("Settings Saved", "Application settings have been saved.")
        self._update_status("Settings saved successfully.", "green")

    def _update_difficulty_map_display(self):
        """Clears and repopulates the difficulty mapping display."""
        # Clear existing labels
        for widget in self.difficulty_map_scroll_frame.winfo_children():
            widget.destroy()

        mapping = self.config.difficulty_mapping
        if not mapping:
            ctk.CTkLabel(self.difficulty_map_scroll_frame, text="No difficulty mapping configured.").pack(anchor="w")
            return
        
        for ch_diff, bs_diff in mapping.items():
            ctk.CTkLabel(self.difficulty_map_scroll_frame, text=f"CH {ch_diff} -> BS {bs_diff}").pack(anchor="w", padx=2, pady=1)

    def _browse_zips(self):
        """Opens a file dialog to select one or more Clone Hero ZIP files."""
        zip_files = filedialog.askopenfilenames(
            title="Select Clone Hero Song ZIPs",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        if zip_files:
            self.selected_zip_paths = [Path(f) for f in zip_files]
            self.update_zip_list_display()
            self.zip_entry.delete(0, ctk.END)
            self.zip_entry.insert(0, f"{len(self.selected_zip_paths)} ZIP(s) selected")

    def update_zip_list_display(self):
        """Updates the scrollable frame with selected ZIP files."""
        for label in self.zip_labels:
            label.destroy()
        self.zip_labels.clear()

        if not self.selected_zip_paths:
            label = ctk.CTkLabel(self.zip_list_frame, text="No ZIP files selected.")
            label.pack(anchor="w", padx=2, pady=1)
            self.zip_labels.append(label)
        else:
            for i, zip_path in enumerate(self.selected_zip_paths):
                label = ctk.CTkLabel(self.zip_list_frame, text=f"{i+1}. {zip_path.name}", wraplength=700)
                label.pack(anchor="w", padx=2, pady=1)
                self.zip_labels.append(label)

    def _browse_output_dir(self):
        """Opens a directory dialog to select the output folder."""
        output_dir = filedialog.askdirectory(title="Select Output Directory")
        if output_dir:
            self.output_dir_entry.delete(0, ctk.END)
            self.output_dir_entry.insert(0, output_dir)
            self.config.set_setting("output_directory", output_dir) # Update config directly

    def _update_status(self, message: str, color: str = "white", progress: float = -1.0):
        """Updates the status label and optionally the progress bar."""
        self.status_label.configure(text=message, text_color=color)
        if progress >= 0:
            self.progress_bar.set(progress)
        self.update_idletasks() # Refresh UI

    def _start_conversion_thread(self):
        """Starts the conversion process in a separate thread to keep UI responsive."""
        if not self.selected_zip_paths:
            messagebox.showwarning("No Files", "Please select one or more Clone Hero ZIP files to convert.")
            return

        self.start_button.configure(state="disabled", text="Converting...")
        self.progress_bar.set(0)
        self._update_status("Starting conversion...", "white", 0)

        # Ensure settings are applied before starting
        self._save_settings()

        # Start the conversion in a new thread
        conversion_thread = threading.Thread(target=self._run_conversion)
        conversion_thread.start()

    def _run_conversion(self):
        """The actual conversion logic, run in a separate thread."""
        total_zips = len(self.selected_zip_paths)
        successful_conversions = 0

        for i, zip_path in enumerate(self.selected_zip_paths):
            current_progress = (i / total_zips) * 0.9 # Allocate 90% for individual file processing
            self._update_status(f"Processing ({i+1}/{total_zips}): {zip_path.name}", "white", current_progress)

            metadata: Optional[CloneHeroSongMetadata] = None
            try:
                # 1. Extract and Parse
                self._update_status(f"Extracting & parsing {zip_path.name}...", "white", current_progress + 0.02)
                metadata = self.extractor.extract_and_parse(zip_path)
                if not metadata:
                    raise ValueError(f"Failed to extract or parse {zip_path.name}")

                # 2. Convert to Beat Saber
                self._update_status(f"Converting {metadata.name} to Beat Saber format...", "white", current_progress + 0.05)
                success = self.converter.convert_to_beatsaber(metadata)
                if not success:
                    raise ValueError(f"Failed to convert {metadata.name} to Beat Saber format.")

                successful_conversions += 1
                self._update_status(f"Successfully converted: {metadata.name}", "green", (i + 1) / total_zips * 0.9)

            except Exception as e:
                self._update_status(f"Error converting {zip_path.name}: {e}", "red")
                print(f"Detailed error for {zip_path.name}: {e}") # Log detailed error to console
            finally:
                # Clean up temporary files regardless of conversion success for this song
                if metadata and hasattr(metadata, '_temp_dir'):
                    self.extractor.cleanup_temp_files(metadata)


        final_status_message = f"Conversion finished. {successful_conversions}/{total_zips} songs converted successfully."
        if successful_conversions < total_zips:
            messagebox.showwarning("Conversion Complete with Warnings", final_status_message)
            self._update_status(final_status_message, "orange", 1.0)
        else:
            messagebox.showinfo("Conversion Complete", final_status_message)
            self._update_status(final_status_message, "green", 1.0)

        self.start_button.configure(state="normal", text="Start Conversion")
        self.progress_bar.set(0) # Reset progress bar after completion

# If you want to test the UI standalone without main.py, uncomment the following:
# if __name__ == "__main__":
#     ctk.set_appearance_mode("System")  # Modes: "System" (default), "Dark", "Light"
#     ctk.set_default_color_theme("blue")  # Themes: "blue" (default), "dark-blue", "green"
#
#     config = AppConfig(config_file='test_config.json')
#     extractor = Extractor(config)
#     converter = Converter(config)
#
#     app = AppUI(config, extractor, converter)
#     app.mainloop()
#
#     # Clean up test config after closing UI
#     if Path('test_config.json').exists():
#         Path('test_config.json').unlink()