# src/extractor.py

import zipfile
import configparser
import os
import shutil
from pathlib import Path
from typing import Optional
import logging 

from src.models import CloneHeroSongMetadata
from src.config import AppConfig # Assuming config.py is in src/

class Extractor:
    def __init__(self, config: AppConfig):
        self.config = config
        self.temp_extract_dir = Path("temp_extracted_songs") # Temporary directory for extraction
        self.temp_extract_dir.mkdir(exist_ok=True) # Ensure it exists
        self.logger = logging.getLogger(__name__)

    def _clean_temp_dir(self, path: Path):
        """Removes the temporary directory after processing."""
        if path.exists() and self.config.delete_temp_files:
            shutil.rmtree(path)
            self.logger.info(f"Cleaned up temporary directory: {path}")

    def extract_and_parse(self, zip_filepath: Path) -> Optional[CloneHeroSongMetadata]:
        """
        Extracts a Clone Hero song ZIP file and parses its contents.
        Returns a CloneHeroSongMetadata object or None on failure.
        """
        if not zip_filepath.exists():
            self.logger.error(f"Error: ZIP file not found at {zip_filepath}")
            return None

        # Create a unique temporary directory for this song
        song_temp_dir = self.temp_extract_dir / zip_filepath.stem
        song_temp_dir.mkdir(exist_ok=True)

        try:
            with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                zip_ref.extractall(song_temp_dir)
            self.logger.info(f"Extracted {zip_filepath.name} to {song_temp_dir}")

            metadata = self._parse_extracted_folder(song_temp_dir)
            if metadata:
                self.logger.info(f"Successfully parsed metadata for {metadata.name}")
                metadata.midi_path = self._find_file(song_temp_dir, "notes.mid")
                metadata.audio_path = self._find_audio_file(song_temp_dir)
                metadata.cover_path = self._find_cover_image(song_temp_dir)
                
                # Assign the temporary directory for cleanup later if needed
                metadata._temp_dir = song_temp_dir 
                return metadata
            else:
                self.logger.warning(f"Could not parse song.ini or find essential files in {song_temp_dir}")
                self._clean_temp_dir(song_temp_dir)
                return None

        except zipfile.BadZipFile:
            self.logger.error(f"Error: {zip_filepath.name} is not a valid ZIP file.")
            self._clean_temp_dir(song_temp_dir)
            return None
        except Exception as e:
            self.logger.error(f"An unexpected error occurred during extraction or parsing: {e}")
            self._clean_temp_dir(song_temp_dir)
            return None

    def _parse_extracted_folder(self, folder_path: Path) -> Optional[CloneHeroSongMetadata]:
        """
        Parses the song.ini file within an extracted Clone Hero song folder.
        """
        song_ini_path = folder_path / "song.ini"
        if not song_ini_path.exists():
            # Sometimes song.ini might be nested, try to find it
            for root, _, files in os.walk(folder_path):
                if "song.ini" in files:
                    song_ini_path = Path(root) / "song.ini"
                    break
            if not song_ini_path.exists():
                self.logger.error(f"Error: song.ini not found in {folder_path}")
                return None

        config_parser = configparser.ConfigParser()
        # configparser is case-insensitive by default for section/option names.
        # Ensure it reads the raw casing if needed, but for song.ini, it's usually fine.
        try:
            config_parser.read(song_ini_path, encoding='utf-8')
        except configparser.MissingSectionHeaderError:
            self.logger.error(f"Error: Missing section header in {song_ini_path}. Attempting to add a default [song] section.")
            with open(song_ini_path, 'r', encoding='utf-8') as f:
                content = f.read()
            with open(song_ini_path, 'w', encoding='utf-8') as f:
                f.write("[song]\n" + content)
            config_parser.read(song_ini_path, encoding='utf-8')
        except Exception as e:
            self.logger.error(f"Error reading song.ini at {song_ini_path}: {e}")
            return None

        metadata = CloneHeroSongMetadata()
        if 'song' in config_parser:
            song_section = config_parser['song']
            metadata.name = song_section.get('name', "Unknown Song")
            metadata.artist = song_section.get('artist', "Unknown Artist")
            metadata.album = song_section.get('album')
            metadata.genre = song_section.get('genre')
            metadata.year = song_section.get('year')
            metadata.charter = song_section.get('charter', song_section.get('frets')) # 'frets' is an older tag for charter
            
            # Parse numeric fields
            metadata.preview_start_time = self._parse_int(song_section, 'preview_start_time', 0)
            metadata.song_length = self._parse_int(song_section, 'song_length')

            # Parse difficulties
            diff_prefixes = ['diff_guitar', 'diff_bass', 'diff_drums', 'diff_keys',
                             'diff_vocals', 'diff_band', 'diff_ghl_guitar', 'diff_ghl_bass', 'diff_rhythm']
            for prefix in diff_prefixes:
                if prefix in song_section:
                    try:
                        metadata.difficulties[prefix] = int(song_section[prefix])
                    except ValueError:
                        self.logger.warning(f"Warning: Invalid difficulty value for {prefix} in {song_ini_path}")
        else:
            self.logger.warning(f"Warning: '[song]' section not found in {song_ini_path}. Metadata might be incomplete.")
        
        return metadata

    def _parse_int(self, section, key, default=None):
        """Helper to safely parse an integer from a config section."""
        value = section.get(key)
        if value is not None:
            try:
                return int(value)
            except ValueError:
                self.logger.warning(f"Warning: Could not parse '{key}' as integer (value: '{value}')")
        return default

    def _find_file(self, folder_path: Path, filename: str) -> Optional[Path]:
        """Finds a specific file, potentially nested."""
        for root, _, files in os.walk(folder_path):
            if filename in files:
                return Path(root) / filename
        self.logger.warning(f"Warning: {filename} not found in {folder_path}")
        return None

    def _find_audio_file(self, folder_path: Path) -> Optional[Path]:
        """Finds the audio file, preferring .opus then common audio formats."""
        audio_extensions = ['.opus', '.ogg', '.wav', '.mp3'] # Prioritize opus as per request
        for ext in audio_extensions:
            found_file = self._find_file(folder_path, f"song{ext}") # common naming convention
            if found_file:
                return found_file
        
        # Fallback: search for any audio file
        for root, _, files in os.walk(folder_path):
            for file in files:
                if any(file.endswith(ext) for ext in audio_extensions):
                    return Path(root) / file
        self.logger.warning(f"Warning: No supported audio file found in {folder_path}")
        return None

    def _find_cover_image(self, folder_path: Path) -> Optional[Path]:
        """Finds the cover image, preferring .jpg then other common image formats."""
        image_names = ['album.jpg', 'album.png', 'cover.jpg', 'cover.png'] # common naming conventions
        for name in image_names:
            found_file = self._find_file(folder_path, name)
            if found_file:
                return found_file
        
        # Fallback: search for any image file (less specific)
        image_extensions = ['.jpg', '.jpeg', '.png']
        for root, _, files in os.walk(folder_path):
            for file in files:
                if any(file.endswith(ext) for ext in image_extensions):
                    return Path(root) / file
        self.logger.warning(f"Warning: No supported cover image found in {folder_path}")
        return None

    # This method will be implemented in the converter module, but we can call it here for cleanup.
    def cleanup_temp_files(self, song_metadata: CloneHeroSongMetadata):
        """Removes temporary files associated with a processed song."""
        if hasattr(song_metadata, '_temp_dir'):
            self._clean_temp_dir(song_metadata._temp_dir)


# Example usage (would typically be called from main.py or ui.py):
if __name__ == "__main__":
    # Create a dummy config for testing
    temp_config = AppConfig(config_file='temp_test_config.json')
    extractor = Extractor(temp_config)

    # To test this, you would need a 'test_song.zip' file
    # with 'notes.mid', 'song.ini', 'song.opus'/'song.ogg', 'album.jpg' inside.
    # For example:
    # ├── test_song.zip
    #     ├── notes.mid
    #     ├── song.ini
    #     ├── song.opus
    #     └── album.jpg
    #
    # Example song.ini content:
    # [song]
    # name = Test Song
    # artist = Test Artist
    # album = Test Album
    # year = 2023
    # charter = Tester
    # preview_start_time = 10000
    # song_length = 120000
    # diff_guitar = 4
    # diff_drums = 2

    test_zip = Path("path/to/your/test_song.zip") # <--- REPLACE WITH ACTUAL PATH TO A TEST ZIP
    if test_zip.exists():
        extracted_data = extractor.extract_and_parse(test_zip)
        if extracted_data:
            print("\n--- Extracted Metadata ---")
            print(f"Name: {extracted_data.name}")
            print(f"Artist: {extracted_data.artist}")
            print(f"Charter: {extracted_data.charter}")
            print(f"MIDI Path: {extracted_data.midi_path}")
            print(f"Audio Path: {extracted_data.audio_path}")
            print(f"Cover Path: {extracted_data.cover_path}")
            print(f"Difficulties: {extracted_data.difficulties}")
            # Clean up after processing (if delete_temp_files is True in config)
            extractor.cleanup_temp_files(extracted_data)
        else:
            print(f"Failed to process {test_zip.name}")
    else:
        print(f"Please create a dummy '{test_zip}' file for testing purposes.")
        print("See comments in the example usage for expected zip structure and song.ini content.")
    
    # Clean up the dummy config file
    if temp_config.config_file.exists():
        temp_config.config_file.unlink()