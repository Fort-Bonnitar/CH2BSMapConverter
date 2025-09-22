# src/models.py

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict

@dataclass
class CloneHeroSongMetadata:
    name: str = "Unknown Song"
    artist: str = "Unknown Artist"
    album: Optional[str] = None
    genre: Optional[str] = None
    year: Optional[str] = None
    charter: Optional[str] = None
    preview_start_time: int = 0  # milliseconds
    song_length: Optional[int] = None # milliseconds
    difficulties: Dict[str, int] = field(default_factory=dict) # e.g., {"diff_guitar": 3}
    
    # Paths to extracted assets
    midi_path: Optional[Path] = None
    audio_path: Optional[Path] = None
    cover_path: Optional[Path] = None

@dataclass
class BeatSaberMapData:
    song_name: str
    song_artist: str
    song_author: str
    beats_per_minute: float
    song_time_offset: int
    shuffle: float
    shuffle_period: float
    preview_start_time: int
    preview_duration: int
    cover_image_filename: str
    environment_name: str
    difficulty_beatsaver_name: str # e.g., "Easy", "Normal", "Expert"
    
    # Paths for Beat Saber specific files
    info_dat_path: Optional[Path] = None
    difficulty_dat_path: Optional[Path] = None
    audio_file_path: Optional[Path] = None
    cover_file_path: Optional[Path] = None

# We will expand this as we get to the converter.