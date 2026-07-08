# Cross Hermit: Welcome to the Farthest — YBC Editor

A visual, browser-based editor for the *Cross Hermit: Welcome to the Farthest* scripting engine. This tool allows users to visualize, edit, and compile `.ybc` scripts used by the game.

## Features

* **Visual Scene Tree**: Easily navigate script commands with a searchable, tree-based interface.
* **Inspector Panel**: Modify command properties, tagged word operands, and meta-parameters in real-time.
* **Integrated Preview**: Uses PIXI.js to render game visuals, character portraits, and UI layouts directly in your browser.
* **Script Management**: Open existing `.ybc` files, save modifications as JSON, and re-compile them back to `.ybc` format.
* **Bulk Text Editor**: Quickly edit, search, and replace dialogue text across the entire script.
* **Audio Controls**: Real-time adjustment of BGM, voice, and sound effect levels for previewing.

## How to Launch

This application uses **Flask** as a backend to serve files and handle script compilation.

### Prerequisites

* Python 3.x
* Required libraries: `Flask`, `Pillow` (PIL)

1. **Install dependencies**:
```bash
pip install Flask Pillow

```


2. **Organize your Data**:
Ensure your game data is placed in the `Data/` directory as expected by the script (e.g., `Data/SOUND/VOICE`, `Data/SOUND/BGM`).
3. **Launch the server**:
Run the `editor.py` script:
```bash
python editor.py

```


4. **Explore in Browser**:
Once the server is running, open your web browser and navigate to the address provided in your terminal (usually `http://127.0.0.1:5000`).

## Technical Overview

* **`editor.py`**: The Flask backend handles parsing the proprietary `.ybc` binary format into JSON for the frontend, and recompiling JSON back into `.ybc` binary files.
* **`opcode_schema.js`**: Defines the authoritative schema for the game's Virtual Machine (VM), including opcodes, parameter mapping, character lists, and slot definitions.
* **`index.html`**: The frontend GUI built with PIXI.js, providing the visual layout, timeline navigation, and property inspection.

---

*Note: This tool is intended for development and modding purposes related to "Cross Hermit: Welcome to the Farthest".*
