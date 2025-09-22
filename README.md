# CH2BSMapConverter

A tool to seamlessly convert Clone Hero song ZIP files into playable Beat Saber maps. This project aims to bridge the gap between two popular rhythm games, allowing you to bring your extensive Clone Hero library into Beat Saber with minimal effort.

## 1. Overview

MIDI2BSMap automates the complex process of converting Clone Hero song packages (`.zip` files) into Beat Saber map folders. It parses Clone Hero's `notes.mid` for musical events, extracts and converts audio, uses `song.ini` for metadata, and automatically generates Beat Saber-compatible `info.dat` and difficulty `.dat` files.

**Key Features:**

*   **Clone Hero ZIP Input**: Directly processes Clone Hero song ZIP files, handling extraction of `notes.mid`, audio files (`.opus`, `.ogg`, `.wav`, `.mp3`), `cover.jpg`, and `song.ini`.
*   **Automatic Audio Conversion**: Converts `.opus` (and other formats) to Beat Saber-compatible `.ogg` or `.wav` audio using `ffmpeg`.
*   **Intelligent MIDI Parsing**: Extracts tempo changes and note events from `notes.mid`, converting them into Beat Saber's beat-time system.
*   **Metadata Integration**: Populates Beat Saber's `info.dat` with song name, artist, charter, album, preview times, and BPM from `song.ini`.
*   **Dynamic Difficulty Mapping**: Reads Clone Hero's numeric difficulties (`diff_guitar`, `diff_band`, etc.) from `song.ini` and maps them to Beat Saber difficulty levels (Easy, Normal, Hard, Expert, Expert+). If no difficulties are specified, it defaults to generating an "Expert" map.
*   **User Interface (UI)**: A simple, intuitive graphical interface built with `customtkinter` for easy file selection, configuration, and conversion.
*   **Modular Codebase**: Cleanly organized into `extractor.py`, `converter.py`, `ui.py`, and `config.py` for maintainability and extensibility.

## 2. Installation

To get MIDI2BSMap up and running, follow these steps:

### 2.1. Clone the Repository

First, clone the project repository to your local machine:

```bash
git clone https://github.com/Fort-Bonnitar/MIDI2BSMap.git
cd MIDI2BSMap
```

### 2.2. Python Environment Setup

MIDI2BSMap requires Python 3.8 or newer. It's recommended to use a virtual environment:

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 2.3. Install FFmpeg

`pydub`, the audio processing library used by MIDI2BSMap, requires `ffmpeg` to be installed on your system and accessible in your system's PATH.

*   **Windows**:
    1.  Go to the official FFmpeg website: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
    2.  Download a `git` build (e.g., from gyan.dev or BtbN).
    3.  Extract the downloaded ZIP file to a location like `C:\ffmpeg`.
    4.  Add the `bin` directory (e.g., `C:\ffmpeg\bin`) to your system's PATH environment variable.
        *   *Guide*: [How to Add FFmpeg to PATH on Windows](https://www.wikihow.com/Install-FFmpeg-on-Windows) (You can search for more specific guides if needed).
*   **macOS**:
    Install via Homebrew (if you don't have Homebrew, install it first from [brew.sh](https://brew.sh)):
    ```bash
    brew install ffmpeg
    ```
*   **Linux (Debian/Ubuntu)**:
    ```bash
    sudo apt update
    sudo apt install ffmpeg
    ```
*   **Linux (Fedora)**:
    ```bash
    sudo dnf install ffmpeg
    ```
    (Other Linux distributions will have similar commands via their package managers.)

## 3. Usage

Once installed, you can launch the application and start converting your Clone Hero songs.

### 3.1. Running the Application

Make sure your virtual environment is activated (see Installation step 2.2). Then run:

```bash
python src/main.py
```

This will open the graphical user interface.

### 3.2. Using the UI

1.  **Select Clone Hero ZIP(s)**:
    *   Click the "Browse" button next to "Clone Hero ZIP(s)".
    *   Select one or more `.zip` files containing Clone Hero songs. The selected files will appear in the "Selected ZIP Files" list.
2.  **Configure Output & Settings**:
    *   **Output Directory**: Specify where the converted Beat Saber maps will be saved. You can type a path or click "Browse" to select a folder.
    *   **Audio Target Format**: Choose between `.ogg` (default, smaller file size) or `.wav` (larger, uncompressed) for the output Beat Saber audio.
    *   **Delete Temp Files**: Check this box if you want the temporary extraction folders to be automatically cleaned up after each song conversion.
    *   **Difficulty Mapping**: This section displays the current Clone Hero numeric difficulty to Beat Saber string mapping. You can customize these mappings by directly editing `config.json` (see Configuration section).
    *   Click "Save Settings" to apply your changes.
3.  **Start Conversion**:
    *   Click the "Start Conversion" button.
    *   A progress bar will show the overall progress, and the status label will provide updates on individual song conversions.
    *   Upon completion, a summary message will appear, indicating how many songs were successfully converted.

### 3.3. Output

Successfully converted Beat Saber maps will be organized into subfolders within your specified output directory. Each subfolder will be named `[Artist] - [Song Name]` (e.g., `Test Dev - Multi-Difficulty Test`) and will contain:

*   `info.dat`
*   `Standard[Difficulty].dat` (e.g., `StandardExpert.dat`, `StandardNormal.dat`)
*   `song.ogg` or `song.wav` (the converted audio)
*   `cover.jpg` (if found in the original ZIP)

You can then place these folders directly into your Beat Saber `CustomLevels` directory.

## 4. Configuration

All user-adjustable settings are consolidated into a single configuration file, `config.json`, located in the root of your project directory (where `main.py` is). If this file doesn't exist, it will be created automatically with default values upon first run.

You can modify these settings directly in the UI or by editing `config.json` with a text editor.

Example `config.json`:

```json
{
    "output_directory": "./output_bs_maps",
    "difficulty_mapping": {
        "0": "Easy",
        "1": "Easy",
        "2": "Normal",
        "3": "Hard",
        "4": "Expert",
        "5": "Expert",
        "6": "ExpertPlus"
    },
    "audio_target_format": "ogg",
    "delete_temp_files": true
}
```

*   **`output_directory`**: The default folder where converted Beat Saber maps will be saved.
*   **`difficulty_mapping`**: A dictionary that maps Clone Hero's numeric difficulty values (from `song.ini`'s `diff_guitar`, `diff_drums`, etc.) to Beat Saber's string difficulty names.
*   **`audio_target_format`**: The desired audio format for the Beat Saber map. Can be `"ogg"` or `"wav"`.
*   **`delete_temp_files`**: If `true`, temporary extraction folders created during conversion will be automatically deleted.

## 5. Customization

For advanced users, several aspects of the conversion can be customized.

### 5.1. Difficulty Mapping Rules

The `difficulty_mapping` in `config.json` allows you to define how Clone Hero's numeric difficulties (0-6 typically) translate to Beat Saber's difficulties.

*   **To change**: Edit the `config.json` file directly, or use the UI if applicable (the current UI displays but doesn't allow editing these mappings directly; this would be a future UI feature).
*   **Behavior**: For each `diff_[instrument]` entry in a Clone Hero `song.ini`, if its numeric value is present as a key in `difficulty_mapping`, a corresponding Beat Saber `.dat` file will be generated (e.g., `diff_guitar = 4` with the default mapping will create a `StandardExpert.dat`). If no difficulties are found or mapped, an `StandardExpert.dat` will be generated by default using all detected notes.

### 5.2. MIDI Note to Beat Saber Block Mapping

The core mapping logic from Clone Hero MIDI notes to Beat Saber `_lineIndex` (lane) and `_lineLayer` (height) is defined in the `CH_TO_BS_NOTE_MAP` constant within `src/converter.py`.

*   **File**: `src/converter.py`
*   **Constant**: `CH_TO_BS_NOTE_MAP`
*   **How to change**: You can modify this dictionary to:
    *   Adjust the lane/layer for existing frets/drums.
    *   Add mappings for other Clone Hero MIDI notes (e.g., GHLive specific notes, additional drum components, open notes).
    *   Change the `_type_hint` for saber assignment.
*   **Current Mapping Logic**:
    *   Green (MIDI 60) and Red (MIDI 61) are mapped to the left saber (`_type_hint: 0`).
    *   Yellow (MIDI 62), Blue (MIDI 63), and Orange (MIDI 64) are mapped to the right saber (`_type_hint: 1`).
    *   Drum notes are split between left and right sabers for a two-handed feel.
    *   Orange note (MIDI 64) is mapped to `_lineIndex: 2, _lineLayer: 2` to avoid collision and provide visual distinction.
*   **Caution**: Modifying this map requires understanding of both MIDI note numbers and Beat Saber's map format. Incorrect changes can lead to unplayable or erroneous maps.

### 5.3. Cut Direction and Advanced Note Logic

Currently, all generated Beat Saber notes default to an "Up" cut direction (`_cutDirection: 0`). The `_map_notes_to_beatsaber_format` method in `src/converter.py` is where this logic resides.

*   **File**: `src/converter.py`
*   **Method**: `_map_notes_to_beatsaber_format`
*   **Future Enhancement**: Advanced users could modify this method to:
    *   Vary `_cutDirection` based on note sequences, velocity (if available in MIDI), or other patterns.
    *   Implement logic for generating bombs (`_type: 3`) for specific MIDI events (e.g., open notes).
    *   Interpret MIDI sustain pedal events or long note-on/note-off durations to generate Beat Saber walls or arcs (Beat Saber 3.x only).

## 6. Limitations

While powerful, the current version of MIDI2BSMap has some limitations:

*   **Basic Note Conversion**: Primarily focuses on converting `note_on` events to standard Beat Saber blocks.
*   **Simple Cut Directions**: All notes currently default to an "Up" cut direction. More complex cut patterns are not yet generated automatically.
*   **No Note Filtering/Simplification**: All generated difficulties currently use the same set of parsed notes. There is no built-in logic to simplify note patterns for "Easy" or "Normal" difficulties; this requires manual editing or future feature implementation.
*   **No Advanced Beat Saber Features**: Does not generate arcs, chains, or complex lighting events present in Beat Saber's v3.x map format. It sticks to the widely compatible v2.0.0 format.
*   **Limited Obstacles/Events**: Does not generate walls (`_obstacles`) or lighting events (`_events`) beyond the basic note blocks.
*   **FFmpeg Requirement**: Relies on an external `ffmpeg` installation for audio conversion.

## 7. Future Plans

The project is designed to be extensible, with several features planned for future development:

*   **Advanced Cut Direction Generation**: Implement algorithms to generate more intelligent and varied `_cutDirection` values based on musical flow or common Beat Saber charting patterns.
*   **Obstacles (Walls) and Bombs**:
    *   Generate walls for sustained notes in MIDI.
    *   Map specific MIDI notes (e.g., Clone Hero's open notes) to Beat Saber bombs.
*   **Note Simplification for Difficulties**: Introduce algorithms to automatically filter or simplify notes for lower difficulty levels (Easy, Normal, Hard).
*   **Beat Saber v3.x Support**: Add support for newer Beat Saber map format features like arcs and chains.
*   **Enhanced Lighting Events**: Implement basic lighting event generation based on song structure or MIDI track data.
*   **Customizable Difficulty Mapping UI**: Integrate a UI element to allow direct editing of the `difficulty_mapping` within the application.
*   **Command-Line Interface (CLI)**: Provide a CLI option for batch processing or integration into other tools, alongside the GUI.
*   **Expanded Instrument Support**: Better handling and specific mappings for GHLive (6-fret) notes, and more nuanced drum chart conversion.
