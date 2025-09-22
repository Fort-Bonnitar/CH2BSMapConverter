# src/config.py

import json
from pathlib import Path

class AppConfig:
    def __init__(self, config_file: Path | str = 'config.json'):
        self.config_file = Path(config_file)
        self._settings = self._load_config()

    def _load_config(self) -> dict:
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            default_settings = {
                "output_directory": "./output_bs_maps",
                "difficulty_mapping": {
                    "0": "Easy",
                    "1": "Easy",
                    "2": "Normal",
                    "3": "Hard",
                    "4": "Expert",
                    "5": "Expert",
                    "6": "Expert+"
                },
                "audio_target_format": "ogg", # or "wav"
                "delete_temp_files": True,
            }
            # Ensure the output directory exists
            output_dir = Path(default_settings["output_directory"])
            output_dir.mkdir(parents=True, exist_ok=True)
            
            self._save_config(default_settings)
            return default_settings

    def _save_config(self, settings: dict):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)

    def get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key: str, value):
        self._settings[key] = value
        self._save_config(self._settings)

    @property
    def difficulty_mapping(self) -> dict:
        return self._settings.get("difficulty_mapping", {})

    @property
    def output_directory(self) -> Path:
        return Path(self._settings.get("output_directory"))

    @property
    def audio_target_format(self) -> str:
        return self._settings.get("audio_target_format", "ogg")

    @property
    def delete_temp_files(self) -> bool:
        return self._settings.get("delete_temp_files", True)