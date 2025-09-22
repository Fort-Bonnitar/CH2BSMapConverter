# src/converter.py

from pathlib import Path
import shutil
from typing import Optional, Dict, Any, List
import json
import math
import os
import mido
import logging

# pydub will be installed via requirements.txt
# This import needs pydub to be available in the environment
try:
    from pydub import AudioSegment
    from pydub.exceptions import CouldBeDangerous
except ImportError:
    print("Error: pydub not found. Please install it using 'pip install pydub'.")
    print("Audio conversion features will be unavailable without pydub.")
    AudioSegment = None
    CouldBeDangerous = type('CouldBeDangerous', (Exception,), {}) # Dummy exception

# mido will be installed via requirements.txt
try:
    from mido import MidiFile, tempo2bpm, tick2second
    from mido.midifiles.tracks import MidiTrack # For testing MIDI creation
except ImportError:
    print("Error: mido not found. Please install it using 'pip install mido'.")
    print("MIDI parsing features will be unavailable without mido.")
    MidiFile = None
    tempo2bpm = None
    tick2second = None
    MidiTrack = None


from src.models import CloneHeroSongMetadata
from src.config import AppConfig

# --- Constants ---
BS_VERSION = "2.0.0"

# Mapping from Clone Hero MIDI note numbers to Beat Saber "_lineIndex" and "_lineLayer"
# Clone Hero typically uses MIDI notes 60-64 for standard 5-fret guitar:
# Green = 60, Red = 61, Yellow = 62, Blue = 63, Orange = 64
# Beat Saber lanes: _lineIndex (0=leftmost, 3=rightmost), _lineLayer (0=bottom, 2=top)
CH_TO_BS_NOTE_MAP = {
    # Guitar/Bass notes (standard 5-fret mapping)
    # Suggestions: Move Orange to avoid overlap, map Green/Red to Left Saber, Yellow/Blue/Orange to Right Saber
    # _type: 0 = Red (Left Saber), 1 = Blue (Right Saber)
    # _cutDirection: 0 = Up, 1 = Down, 2 = Left, 3 = Right, 4 = Up-Left, 5 = Up-Right, 6 = Down-Left, 7 = Down-Right, 8 = Dot (Any)
    
    # Left Saber (Red, _type: 0)
    60: {"_lineIndex": 0, "_lineLayer": 1, "_type_hint": 0}, # Green -> Leftmost, middle layer
    61: {"_lineIndex": 1, "_lineLayer": 1, "_type_hint": 0}, # Red -> Left-middle, middle layer

    # Right Saber (Blue, _type: 1)
    62: {"_lineIndex": 2, "_lineLayer": 1, "_type_hint": 1}, # Yellow -> Right-middle, middle layer
    63: {"_lineIndex": 3, "_lineLayer": 1, "_type_hint": 1}, # Blue -> Rightmost, middle layer
    # Revised Orange position to avoid collision with Red (Index 1) and make it distinct
    64: {"_lineIndex": 2, "_lineLayer": 2, "_type_hint": 1}, # Orange -> Right-middle, top layer

    # Drum notes (common GH/RB drum MIDI mapping) - Simplified for basic block placement
    # These often represent pads, cymbals, kick.
    # Assigning types for drums: could be all red, all blue, or alternating. For now, defaulting to red (0) for consistency
    # with previous approach, but can be refined.
    36: {"_lineIndex": 0, "_lineLayer": 0, "_type_hint": 0}, # Kick/Bass Drum -> Leftmost, bottom
    38: {"_lineIndex": 1, "_lineLayer": 0, "_type_hint": 0}, # Snare -> Left-middle, bottom
    40: {"_lineIndex": 1, "_lineLayer": 2, "_type_hint": 0}, # Snare rimshot/other -> Left-middle, top
    42: {"_lineIndex": 2, "_lineLayer": 0, "_type_hint": 1}, # Closed Hi-hat -> Right-middle, bottom
    46: {"_lineIndex": 3, "_lineLayer": 0, "_type_hint": 1}, # Open Hi-hat -> Rightmost, bottom
    48: {"_lineIndex": 2, "_lineLayer": 2, "_type_hint": 1}, # High Tom -> Right-middle, top
    50: {"_lineIndex": 3, "_lineLayer": 2, "_type_hint": 1}, # Crash Cymbal -> Rightmost, top
    
    # Future expansion:
    # Open Notes: Could map to bombs (_type: 3) or special blocks. For now, ignored if not in map.
    # Star Power: Could map to a specific lane or trigger an event for future lighting.
}
# --- End Constants ---


class Converter:
    def __init__(self, config: AppConfig):
        self.config = config
        self._check_ffmpeg()
        self._check_mido()
        self.logger = logging.getLogger(__name__)

    def _check_ffmpeg(self):
        """Checks if ffmpeg is available in the system's PATH."""
        if AudioSegment is None:
            self.logger.warning("WARNING: pydub is not installed. ffmpeg check skipped, audio conversion impossible.")
            return

        if shutil.which("ffmpeg") is None:
            self.logger.warning("WARNING: ffmpeg not found in PATH. Audio conversion will fail. "
                  "Please install ffmpeg (e.g., via your OS package manager or from ffmpeg.org) "
                  "and ensure it's accessible from your system's PATH.")
        else:
            self.logger.info("ffmpeg found in PATH. Audio conversion should proceed.")

    def _check_mido(self):
        """Checks if mido is available."""
        if MidiFile is None:
            self.logger.warning("WARNING: mido is not installed. MIDI parsing will fail.")
            
    def convert_audio(self, metadata: CloneHeroSongMetadata) -> Optional[Path]:
        """
        Converts the audio file specified in metadata to the target format (ogg or wav).
        Returns the path to the converted audio file, or None if conversion fails.
        """
        if AudioSegment is None:
            self.logger.error("Error: pydub is not installed. Cannot perform audio conversion.")
            return None

        if not metadata.audio_path or not metadata.audio_path.exists():
            self.logger.error(f"Error: No audio file found for conversion or path is invalid for {metadata.name}.")
            return None

        target_format = self.config.audio_target_format.lower()
        if target_format not in ["ogg", "wav"]:
            self.logger.error(f"Error: Unsupported audio target format '{target_format}'. Must be 'ogg' or 'wav'.")
            return None

        # Ensure the output directory for Beat Saber maps exists.
        song_output_dir = self.config.output_directory / f"{metadata.artist} - {metadata.name}"
        song_output_dir.mkdir(parents=True, exist_ok=True)
        
        output_audio_path = song_output_dir / f"song.{target_format}"

        if metadata.audio_path.suffix.lower() == f".{target_format}":
            self.logger.info(f"Audio is already in target format {target_format}. Copying directly.")
            try:
                shutil.copy(metadata.audio_path, output_audio_path)
                return output_audio_path
            except Exception as e:
                self.logger.error(f"Error copying audio file: {e}")
                return None

        self.logger.info(f"Converting audio from {metadata.audio_path.suffix} to .{target_format}...")
        try:
            audio = AudioSegment.from_file(metadata.audio_path)
            if target_format == "ogg":
                audio.export(output_audio_path, format=target_format, bitrate="192k")
            else: # wav
                audio.export(output_audio_path, format=target_format)
            self.logger.info(f"Audio converted and saved to {output_audio_path}")
            return output_audio_path
        except CouldBeDangerous as e:
            self.logger.warning(f"Warning: pydub issued a 'CouldBeDangerous' warning. "
                  f"This might indicate an issue with audio file or ffmpeg: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error converting audio file {metadata.audio_path}: {e}")
            return None

    def _get_tempo_map(self, mid_file) -> List[tuple]:
        """
        Generates a tempo map from a MIDI file.
        Returns a list of tuples: (absolute_tick, tempo_in_microseconds_per_beat, bpm_at_this_tick).
        """
        tempo_map = []
        current_tempo = 500000  # Default to 120 BPM (500,000 microseconds per beat)
        current_tick = 0
        
        # Add initial tempo (even if it's default) at tick 0
        tempo_map.append((0, current_tempo, tempo2bpm(current_tempo)))

        # Iterate through all tracks to find tempo changes. Tempo events are global.
        # We need to accumulate time globally for tempo changes.
        all_tempo_events = []
        for track in mid_file.tracks:
            abs_track_tick = 0
            for msg in track:
                abs_track_tick += msg.time
                if msg.type == 'set_tempo':
                    all_tempo_events.append((abs_track_tick, msg.tempo))
        
        # Sort all tempo events by their absolute tick time
        all_tempo_events.sort(key=lambda x: x[0])

        for event_tick, event_tempo in all_tempo_events:
            if not tempo_map or tempo_map[-1][1] != event_tempo or event_tick == 0:
                # Add if tempo actually changed or if it's the very first explicit tempo change
                tempo_map.append((event_tick, event_tempo, tempo2bpm(event_tempo)))
        
        # Ensure tempo_map starts with tick 0 and is sorted
        tempo_map_final = [t for t in tempo_map if t[0] == 0] + [t for t in tempo_map if t[0] > 0]
        # Remove duplicates based on tick if any
        seen_ticks = set()
        unique_tempo_map = []
        for item in tempo_map_final:
            if item[0] not in seen_ticks:
                unique_tempo_map.append(item)
                seen_ticks.add(item[0])
            elif item[0] == 0 and unique_tempo_map[0][1] != item[1]: # Special case for tick 0 if tempo is immediately changed
                unique_tempo_map[0] = item # Overwrite initial default if an actual tempo is at tick 0
        
        return sorted(unique_tempo_map, key=lambda x: x[0])


    def _ticks_to_seconds(self, tick: int, tempo_map: List[tuple], ticks_per_beat: int) -> float:
        """
        Converts a MIDI tick to an absolute time in seconds, accounting for tempo changes.
        Tempo map: [(absolute_tick, tempo_in_microseconds_per_beat, bpm_at_that_tick)]
        """
        current_seconds = 0.0
        last_tick_in_map = 0
        
        # Find the starting tempo for calculations.
        # Tempo map is guaranteed to have at least one entry at tick 0.
        last_tempo_us_per_beat = tempo_map[0][1] 

        # Iterate through the tempo map to find the relevant tempo segment
        for map_tick_boundary, tempo_us_per_beat, _ in tempo_map:
            if tick < map_tick_boundary:
                # The target tick is within the current segment (from last_tick_in_map to map_tick_boundary)
                ticks_in_segment = tick - last_tick_in_map
                current_seconds += (ticks_in_segment / ticks_per_beat) * (last_tempo_us_per_beat / 1_000_000.0)
                return current_seconds
            else:
                # Add the full duration of this tempo segment
                ticks_in_segment = map_tick_boundary - last_tick_in_map
                current_seconds += (ticks_in_segment / ticks_per_beat) * (last_tempo_us_per_beat / 1_000_000.0)
                last_tick_in_map = map_tick_boundary
                last_tempo_us_per_beat = tempo_us_per_beat
        
        # If the tick is beyond all explicit tempo changes (i.e., in the last segment defined)
        ticks_in_segment = tick - last_tick_in_map
        current_seconds += (ticks_in_segment / ticks_per_beat) * (last_tempo_us_per_beat / 1_000_000.0)
        return current_seconds

    def _get_dominant_bpm(self, tempo_map: List[tuple]) -> float:
        """
        Estimates the dominant BPM of the song. For Beat Saber, info.dat needs a single BPM.
        This currently uses the first BPM in the tempo map, which is often the intended master BPM.
        """
        if not tempo_map:
            return 120.0 # Default if no tempo map
        
        return tempo_map[0][2]


    def _parse_midi_notes(self, midi_path: Path, tempo_map: List[tuple], ticks_per_beat: int, dominant_bpm: float) -> List[Dict[str, Any]]:
        """
        Parses MIDI notes from the given path, converting them to raw Beat Saber compatible notes.
        Returns a flat list of ALL detected and mapped Beat Saber note objects (before color/cut direction).
        Each note includes '_type_hint' from CH_TO_BS_NOTE_MAP for saber assignment.
        """
        if MidiFile is None:
            self.logger.error("Error: mido is not installed. Cannot parse MIDI.")
            return []

        if not midi_path.exists():
            self.logger.error(f"Error: MIDI file not found at {midi_path}")
            return []

        try:
            mid = MidiFile(midi_path)
        except Exception as e:
            self.logger.error(f"Error reading MIDI file {midi_path}: {e}")
            return []
        
        all_raw_bs_notes = [] # List of Beat Saber note objects
        
        for i, track in enumerate(mid.tracks):
            self.logger.info(f"Processing MIDI track: {track.name or f'Track {i}'}")
            absolute_tick_time_track = 0 
            for msg in track:
                absolute_tick_time_track += msg.time 
                
                if msg.type == 'note_on' and msg.velocity > 0:
                    mapping = CH_TO_BS_NOTE_MAP.get(msg.note)
                    if mapping:
                        # Convert absolute ticks to seconds, then to beats relative to dominant BPM
                        time_in_seconds = self._ticks_to_seconds(absolute_tick_time_track, tempo_map, ticks_per_beat)
                        _time_beats = time_in_seconds * (dominant_bpm / 60.0)
                        
                        all_raw_bs_notes.append({
                            "_time_raw_beats": _time_beats, # Store raw beat time
                            "_midi_note": msg.note, # Keep original midi note for potential future use
                            "_lineIndex": mapping["_lineIndex"],
                            "_lineLayer": mapping["_lineLayer"],
                            "_type_hint": mapping["_type_hint"], # Store saber type hint
                        })
        
        # Sort notes by raw beat time
        all_raw_bs_notes.sort(key=lambda x: x["_time_raw_beats"])
        
        return all_raw_bs_notes

    def _map_notes_to_beatsaber_format(self, raw_bs_notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Takes raw Beat Saber notes and applies _type (color) and _cutDirection based on CH_TO_BS_NOTE_MAP's type hint.
        """
        final_notes = []
        
        # Keep track of notes already placed at a specific beat time and position
        placed_notes_at_beat_pos = set() # Stores (beat_time_rounded, lineIndex, lineLayer)

        for raw_note in raw_bs_notes:
            _time = round(raw_note["_time_raw_beats"], 3) # Round beat time for clean JSON
            _lineIndex = raw_note["_lineIndex"]
            _lineLayer = raw_note["_lineLayer"]
            _type = raw_note["_type_hint"] # Use the type hint from the map
            _cutDirection = 0 # Default to Up cut for now. (Future: vary based on velocity/context)

            note_position_key = (_time, _lineIndex, _lineLayer)
            if note_position_key in placed_notes_at_beat_pos:
                # If a note already exists at this exact beat time and position, skip it.
                continue 
            
            final_notes.append({
                "_time": _time,
                "_lineIndex": _lineIndex,
                "_lineLayer": _lineLayer,
                "_type": _type,
                "_cutDirection": _cutDirection,
            })
            placed_notes_at_beat_pos.add(note_position_key)
            
        return final_notes

    def _generate_info_dat(self, metadata: CloneHeroSongMetadata, audio_filename: str, cover_filename: str, bpm: float) -> Dict[str, Any]:
        """Generates the content for info.dat."""
        return {
            "_version": BS_VERSION,
            "_songName": metadata.name,
            "_songSubName": metadata.album or "",
            "_songAuthorName": metadata.artist,
            "_levelAuthorName": metadata.charter or "Unknown Charter",
            "_beatsPerMinute": round(bpm, 2),
            "_songTimeOffset": 0, # Could be derived from MIDI or song.ini in advanced cases
            "_shuffle": 0,
            "_shufflePeriod": 0.5,
            "_previewStartTime": metadata.preview_start_time / 1000.0 if metadata.preview_start_time is not None else 0, # ms to seconds
            "_previewDuration": 10, # Default, could be configurable or derived
            "_songFilename": audio_filename,
            "_coverImageFilename": cover_filename,
            "_environmentName": "DefaultEnvironment", # Could be configurable
            "_allDirectionsEnvironmentName": "DefaultEnvironment", # Only for version > 3.0.0
            "_songPreviewAudioClipPath": audio_filename, # Alias for _songFilename in newer versions
            "_customData": {},
            "_difficultyBeatmapSets": [] # This will be populated later
        }

    def _generate_difficulty_dat(self, notes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generates the content for a difficulty .dat file."""
        return {
            "_version": BS_VERSION,
            "_notes": notes,
            "_obstacles": [],  # Walls
            "_events": [],     # Lighting events etc.
            "_waypoints": [],
            "_bookmarks": [],
            "_lightshowPortions": [],
            "_bpmEvents": [],  # If Beat Saber wanted granular BPM changes in the difficulty .dat itself
            "_customData": {}
        }

    def convert_to_beatsaber(self, metadata: CloneHeroSongMetadata) -> bool:
        """
        Orchestrates the conversion of a Clone Hero song (metadata, midi, audio, cover)
        into Beat Saber map format, including multiple difficulties.
        """
        self.logger.info(f"\n--- Starting Beat Saber Conversion for: {metadata.name} ---")

        # 1. Ensure MIDI file exists
        if MidiFile is None:
            self.logger.error(f"Error: mido is not installed. Cannot convert MIDI for {metadata.name}.")
            return False
        if not metadata.midi_path or not metadata.midi_path.exists():
            self.logger.error(f"Error: MIDI file (notes.mid) not found for {metadata.name}. Cannot convert to Beat Saber.")
            return False

        # 2. Convert audio
        converted_audio_path = self.convert_audio(metadata)
        if not converted_audio_path:
            self.logger.error(f"Error: Audio conversion failed for {metadata.name}. Aborting Beat Saber conversion.")
            return False
        
        # 3. Copy cover image
        bs_map_output_dir = self.config.output_directory / f"{metadata.artist} - {metadata.name}"
        bs_map_output_dir.mkdir(parents=True, exist_ok=True) 
        
        cover_filename = "cover.jpg" # Standard Beat Saber cover image filename
        if metadata.cover_path and metadata.cover_path.exists():
            try:
                shutil.copy(metadata.cover_path, bs_map_output_dir / cover_filename)
                self.logger.info(f"Cover image copied to {bs_map_output_dir / cover_filename}")
            except Exception as e:
                self.logger.warning(f"Warning: Could not copy cover image {metadata.cover_path}: {e}")
                cover_filename = "" # Indicate no cover was successfully copied
        else:
            self.logger.warning("Warning: No cover image found or path invalid. Map will have no cover.")
            cover_filename = ""

        # 4. Parse MIDI for tempo map, dominant BPM, and all raw notes
        try:
            midi_file_obj = MidiFile(metadata.midi_path)
            tempo_map = self._get_tempo_map(midi_file_obj)
            dominant_bpm = self._get_dominant_bpm(tempo_map)
            
            # Get all mappable notes from MIDI, regardless of declared difficulty
            all_raw_bs_notes = self._parse_midi_notes(metadata.midi_path, tempo_map, midi_file_obj.ticks_per_beat, dominant_bpm)

        except Exception as e:
            self.logger.error(f"Error during MIDI parsing: {e}")
            return False

        # If no notes were parsed, we can't create any difficulty maps.
        if not all_raw_bs_notes:
            self.logger.warning(f"Warning: No mappable notes found in MIDI file for {metadata.name}. "
                  "Generating info.dat with no difficulty maps.")
            # Generate info.dat anyway as a base
            info_dat_content = self._generate_info_dat(metadata, converted_audio_path.name, cover_filename, dominant_bpm)
            info_dat_path = bs_map_output_dir / "info.dat"
            try:
                with open(info_dat_path, 'w', encoding='utf-8') as f:
                    json.dump(info_dat_content, f, indent=4)
                self.logger.info(f"Generated Beat Saber info.dat (no difficulties): {info_dat_path}")
                return True
            except Exception as e:
                self.logger.error(f"Error writing info.dat file {info_dat_path}: {e}")
                return False

        # 5. Determine which Beat Saber difficulties to generate
        difficulties_to_generate = set() # Use a set to avoid duplicate BS difficulty outputs
        
        ch_to_bs_difficulty_map = self.config.difficulty_mapping

        if metadata.difficulties:
            for ch_instrument_diff_key, ch_numeric_diff_val in metadata.difficulties.items():
                # ch_numeric_diff_val is typically 0-6 in CH. Config maps these to BS strings.
                mapped_bs_difficulty = ch_to_bs_difficulty_map.get(str(ch_numeric_diff_val), None)
                if mapped_bs_difficulty:
                    difficulties_to_generate.add(mapped_bs_difficulty)
                else:
                    self.logger.warning(f"Warning: No Beat Saber difficulty mapping found for Clone Hero numeric difficulty '{ch_numeric_diff_val}' "
                          f"from '{ch_instrument_diff_key}'. Skipping this difficulty.")
        
        # Rule: If no difficulties are found in song.ini or couldn't be mapped, default to Expert
        if not difficulties_to_generate:
            self.logger.info("No mappable Clone Hero difficulties found in song.ini. Defaulting to 'Expert' Beat Saber map.")
            difficulties_to_generate.add("Expert")

        # 6. Generate Info.dat base structure
        info_dat_content = self._generate_info_dat(metadata, converted_audio_path.name, cover_filename, dominant_bpm)
        
        # Prepare the _difficultyBeatmapSets structure
        info_dat_content["_difficultyBeatmapSets"] = [{
            "_beatmapCharacteristicName": "Standard", # Most common characteristic
            "_difficultyBeatmaps": [] # Actual difficulties will be added here
        }]

        # 7. Generate difficulty .dat files for each determined Beat Saber difficulty
        bs_difficulty_levels = ["Easy", "Normal", "Hard", "Expert", "ExpertPlus"] # Order for _difficultyRank

        for bs_difficulty_name in sorted(list(difficulties_to_generate), key=lambda x: bs_difficulty_levels.index(x)):
            self.logger.info(f"Generating Beat Saber map for difficulty: {bs_difficulty_name}")
            
            # Apply color/cut direction mapping. (Future: filter/simplify notes per difficulty here)
            final_bs_notes = self._map_notes_to_beatsaber_format(all_raw_bs_notes)
            
            difficulty_dat_content = self._generate_difficulty_dat(final_bs_notes)
            
            difficulty_filename = f"Standard{bs_difficulty_name}.dat"
            difficulty_path = bs_map_output_dir / difficulty_filename

            try:
                with open(difficulty_path, 'w', encoding='utf-8') as f:
                    json.dump(difficulty_dat_content, f, indent=4)
                self.logger.info(f"Generated Beat Saber difficulty map: {difficulty_path}")
                
                # Add this difficulty to the info.dat structure
                info_dat_entry = {
                    "_difficulty": bs_difficulty_name,
                    "_difficultyRank": bs_difficulty_levels.index(bs_difficulty_name),
                    "_beatmapFilename": difficulty_filename,
                    "_noteJumpMovementSpeed": 10, # Configurable later (often based on BPM/difficulty)
                    "_noteJumpStartBeatOffset": 0,
                    "_customData": {}
                }
                info_dat_content["_difficultyBeatmapSets"][0]["_difficultyBeatmaps"].append(info_dat_entry)

            except Exception as e:
                self.logger.error(f"Error writing difficulty .dat file {difficulty_path}: {e}")
                return False # Critical failure for this difficulty, stop conversion

        # 8. Write final info.dat
        info_dat_path = bs_map_output_dir / "info.dat"
        try:
            with open(info_dat_path, 'w', encoding='utf-8') as f:
                json.dump(info_dat_content, f, indent=4)
            self.logger.info(f"Generated Beat Saber info.dat: {info_dat_path}")
        except Exception as e:
            self.logger.error(f"Error writing info.dat file {info_dat_path}: {e}")
            return False

        self.logger.info(f"Beat Saber conversion completed successfully for {metadata.name} (with {len(difficulties_to_generate)} difficulties)!")
        return True

# Example Usage Block (now reflects full conversion workflow)
if __name__ == "__main__":
    try:
        from PIL import Image # For dummy image
    except ImportError as e:
        print(f"\nSkipping example usage because a required library is not installed: {e}")
        print("Please ensure 'mido', 'pydub', and 'Pillow' are installed.")
        exit()

    if MidiFile is None or AudioSegment is None:
        print("\nSkipping example usage because essential libraries (mido/pydub) are not installed.")
        exit()

    # --- Setup dummy config and directories ---
    temp_config_file = Path("temp_test_config_converter.json")
    if temp_config_file.exists():
        temp_config_file.unlink() 
    
    temp_config = AppConfig(config_file=temp_config_file)
    output_base_dir_multi = Path("./temp_bs_output_test_multi")
    output_base_dir_no_diff = Path("./temp_bs_output_test_no_diff")
    temp_config.set_setting("output_directory", str(output_base_dir_multi)) # Initial setting
    output_base_dir_multi.mkdir(parents=True, exist_ok=True) 
    output_base_dir_no_diff.mkdir(parents=True, exist_ok=True) # Ensure it exists

    dummy_temp_dir_for_extractor = Path("./temp_extracted_songs_for_converter_test")
    dummy_temp_dir_for_extractor.mkdir(exist_ok=True)

    # --- Create dummy MIDI, Audio, Cover for testing ---
    midi_test_file_path = dummy_temp_dir_for_extractor / "notes.mid"
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    mid.ticks_per_beat = 480 # Standard for many MIDI files

    # Test with tempo changes and various notes
    track.append(mido.Message('set_tempo', tempo=mido.bpm2tempo(120), time=0)) # 120 BPM
    track.append(mido.Message('note_on', note=60, velocity=64, time=0)) # Green note at Beat 0.0 (Left Saber)
    track.append(mido.Message('note_off', note=60, velocity=0, time=mid.ticks_per_beat // 2)) # Releases at Beat 0.5

    track.append(mido.Message('note_on', note=62, velocity=64, time=mid.ticks_per_beat // 2)) # Yellow note at Beat 1.0 (Right Saber)
    track.append(mido.Message('note_off', note=62, velocity=0, time=mid.ticks_per_beat // 2)) # Releases at Beat 1.5

    track.append(mido.Message('set_tempo', tempo=mido.bpm2tempo(180), time=mid.ticks_per_beat)) # Change to 180 BPM after 1 beat at 120 (at total beat 2.5)
    
    track.append(mido.Message('note_on', note=64, velocity=64, time=mid.ticks_per_beat // 2)) # Orange note at Beat 2.5 + 0.5 = 3.0 (at 180 BPM, Right Saber)
    track.append(mido.Message('note_off', note=64, velocity=0, time=0)) 

    mid.save(midi_test_file_path)
    print(f"Dummy MIDI created: {midi_test_file_path}")

    dummy_audio_path = dummy_temp_dir_for_extractor / "song.opus"
    silent_audio = AudioSegment.silent(duration=15000) # 15 seconds
    silent_audio.export(dummy_audio_path, format="opus")
    print(f"Dummy Audio created: {dummy_audio_path}")

    dummy_cover_path = dummy_temp_dir_for_extractor / "album.jpg"
    img = Image.new('RGB', (128, 128), color = 'red')
    img.save(dummy_cover_path)
    print(f"Dummy Cover created: {dummy_cover_path}")

    # Dummy metadata object with multiple difficulties
    test_metadata_multi_diff = CloneHeroSongMetadata(
        name="Multi-Difficulty Test",
        artist="Test Dev",
        charter="Agent",
        album="Test Album",
        year="2023",
        preview_start_time=1000, 
        song_length=15000, # 15 seconds
        midi_path=midi_test_file_path,
        audio_path=dummy_audio_path,
        cover_path=dummy_cover_path,
        difficulties={
            "diff_guitar": 4,  # Maps to Expert
            "diff_bass": 2,    # Maps to Normal
            "diff_drums": 0,   # Maps to Easy
            "diff_vocals": 99  # Should be ignored (no mapping)
        },
        _temp_dir = dummy_temp_dir_for_extractor # For cleanup in example
    )

    # Dummy metadata object with no difficulties (should default to Expert)
    test_metadata_no_diff = CloneHeroSongMetadata(
        name="No Difficulty Test",
        artist="Test Dev",
        charter="Agent",
        album="No Diff Album",
        year="2024",
        preview_start_time=1000,
        song_length=15000,
        midi_path=midi_test_file_path,
        audio_path=dummy_audio_path,
        cover_path=dummy_cover_path,
        difficulties={}, # Empty difficulties
        _temp_dir = dummy_temp_dir_for_extractor # For cleanup in example
    )
    
    converter = Converter(temp_config)
    
    # --- Execute the conversion for multiple difficulties ---
    print("\n--- Testing Multi-Difficulty Conversion ---")
    temp_config.set_setting("output_directory", str(output_base_dir_multi)) # Ensure correct output dir
    success_multi = converter.convert_to_beatsaber(test_metadata_multi_diff)
    print(f"Multi-Difficulty Conversion Success: {success_multi}")

    # --- Execute the conversion for no specified difficulties ---
    print("\n--- Testing No-Difficulty Conversion (should default to Expert) ---")
    temp_config.set_setting("output_directory", str(output_base_dir_no_diff)) # Change output dir to avoid conflict
    success_no_diff = converter.convert_to_beatsaber(test_metadata_no_diff)
    print(f"No-Difficulty Conversion Success: {success_no_diff}")


    # --- Cleanup ---
    if temp_config_file.exists():
        temp_config_file.unlink()
    if output_base_dir_multi.exists():
        shutil.rmtree(output_base_dir_multi)
    if output_base_dir_no_diff.exists():
        shutil.rmtree(output_base_dir_no_diff)
    if dummy_temp_dir_for_extractor.exists():
        shutil.rmtree(dummy_temp_dir_for_extractor)
    print("Cleanup complete for converter example.")