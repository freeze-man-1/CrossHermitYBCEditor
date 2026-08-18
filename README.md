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
![image](https://raw.githubusercontent.com/freeze-man-1/CrossHermitYBCEditor/refs/heads/main/Screenshots/Screenshot%202026-07-08%20061115.png)

## Translation alignment guard

The string table is **index-addressed**: box *N* always shows string *N*, together
with its own voice clip, portrait and nameplate. A translation must therefore stay
strictly **one source box : one target box**. Splitting one source line in two shifts
every later line onto the wrong voice — and because a later merge can re-absorb the
extra line, the total line count still matches, so counting alone will not catch it.

To detect this, keep the untranslated script beside the one you are editing as
`<name>-orig.ybc` (a `.bak` written by *Compile .ybc* also works). Then:

* **Check alignment** (toolbar) compares every box against the reference and reports
  drift regions, including whether a uniform ±1 shift would repair them.
* **Compile .ybc / Compile As…** refuse to write a drifted script (HTTP 409). The
  report is shown with an explicit *Ignore and continue* override.
* The **Bulk Text Editor** shows the source line beside each target line, highlights
  boxes whose shape no longer matches their source, and blocks *Apply* on drift.
* **Export .txt** writes each line prefixed with its box number; **Import .txt** keys
  on those numbers and rejects files with missing, duplicated or extra boxes.

Box width is measured in half-width cells (a full-width Japanese glyph counts as two),
so *Auto-fix overflow* wraps Japanese and English against the same real box width.

## Technical Overview

* **`editor.py`**: The Flask backend handles parsing the proprietary `.ybc` binary format into JSON for the frontend, and recompiling JSON back into `.ybc` binary files.
* **`opcode_schema.js`**: Defines the authoritative schema for the game's Virtual Machine (VM), including opcodes, parameter mapping, character lists, and slot definitions.
* **`index.html`**: The frontend GUI built with PIXI.js, providing the visual layout, timeline navigation, and property inspection.
![image](https://raw.githubusercontent.com/freeze-man-1/CrossHermitYBCEditor/refs/heads/main/Screenshots/Screenshot%202026-07-08%20061737.png)
---

*Note: This tool is intended for development and modding purposes related to "Cross Hermit: Welcome to the Farthest".*
