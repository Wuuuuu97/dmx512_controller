# DMX 调试助手 — Project Overview

A DMX512 lighting control tool built with Python + PyQt5. Controls up to 512 DMX channels via USB-to-serial (RS-485) adapter.

## Quick Start

```bash
pip install -r requirements.txt
python main.py
```

Build single-file exe:
```bash
pyinstaller --onefile --windowed -y --icon icon.ico --name "DMX调试助手" main.py
```
Output goes to `dist/DMX调试助手/DMX调试助手.exe`.

## Project Structure

```
dmx512_controller/
├── main.py                  # Entry point
├── CLAUDE.md                # This file — project overview for AI
├── SPEC.md                  # Full specification (Chinese)
├── requirements.txt         # PyQt5>=5.15, pyserial>=3.5
├── icon.ico                 # Application icon
├── build_icon.py            # Script to regenerate icon.ico
└── src/
    ├── __init__.py
    ├── dmx/
    │   ├── __init__.py
    │   └── transmitter.py   # DMX512 protocol transmitter (QThread)
    ├── engine/
    │   ├── __init__.py
    │   └── chaser.py        # Scene chaser engine (QThread with cross-fade)
    └── ui/
        ├── __init__.py
        ├── main_window.py   # Main window: menu, left panel, page area, status bar
        ├── page_widget.py   # Single page: 2×8 grid of ChannelWidgets
        ├── channel_widget.py# Single channel: slider + labels, selection, lock, rename
        ├── serial_panel.py  # Serial panel (unused, kept as reference)
        ├── scene_library.py # In-app scene library dialog (save/load/rename/delete)
        └── chaser_panel.py  # Scene chaser dialog (sequence, interval, fade)
```

## Architecture

### Data Flow
```
Slider → channel_widget → page_widget → main_window → transmitter (QThread)
                                                          ↓
                                               serial.write() → DMX frame
```

- **dmx_data**: `bytearray(512)` shared buffer. GIL protects single-byte operations.
- **Master fader**: applied as scaling in the transmitter thread (doesn't modify stored values).
- **Blackout**: transmitter sends all-zero frames when active (doesn't modify stored values).

### DMX Frame Timing (serial: 250000 baud, 8N2)
| Segment | Duration | Method |
|---------|----------|--------|
| Break   | 100μs    | `serial.break_condition = True` + `time.perf_counter()` spin-wait |
| MAB     | 12μs     | `serial.break_condition = False` + `time.perf_counter()` spin-wait |
| Data    | ~22.6ms  | `serial.write(start_code + 512 bytes)` |
| MTBP    | ~5ms     | `time.perf_counter()` spin-wait |
| **Total** | **~27.7ms (~36 fps)** | |

### Error Recovery
- 3 consecutive send failures → auto-stop transmitter thread
- USB removal detected via Windows error code 1167 (ERROR_DEVICE_REMOVED)
- Port disappearance detected via Windows error code 2 (ERROR_FILE_NOT_FOUND)

## Key Features

### Channel Control
- 512 channels, 32 pages × 16 channels (2 rows × 8 columns)
- Vertical QSlider (0-255) with iOS fader styling (white handle, grip lines)
- Double-click value label to type a value directly
- Channel selection: click label to select, Ctrl+click for multi-select
- Group edit: drag any selected slider to sync all selected channels

### Master Fader (FR-20)
- Horizontal slider (0-100%) at bottom of left panel
- Scales all output values in transmitter thread (real-time, stored values unchanged)

### Blackout (FR-32)
- Checkable button (Space/B shortcut)
- Forces all-zero output frames, preserves dmx_data
- Red indicator + status bar message when active

### Channel Naming (FR-22)
- Right-click channel number → rename
- Custom names saved in scene JSON (`names` field)
- Empty name restores default CHnnn

### Channel Locking (FR-23)
- Right-click → lock/unlock
- Grayed-out slider, value change blocked
- Locked channels skipped by preset operations (reset/max/invert)

### Scene Library (FR-30)
- `scenes/scenes.json` (sibling to exe)
- Save current state, load, rename, delete scenes
- Stores channels, names, and lock states
- Scene data includes `names: dict[int, str]` and `locked: list[int]`

### Scene Chaser (FR-31)
- Select scenes from library, set interval (0.5-60s) and fade (0-10s)
- Cross-fade via linear interpolation (~33fps during transition)
- Loop mode support
- Stops DMX transmission while running

### Serial
- Auto-scan available ports (dropdown + refresh button)
- Fixed 250000 baud, 8 data bits, 2 stop bits, no parity
- Start/Stop buttons (port config disabled while transmitting)

### Presets (菜单 → 预设)
- 全部归零 (Ctrl+R) — skip locked channels
- 全部最大 (255)
- 全部取反
- All show confirmation dialog

### Scene File I/O
- JSON format: `{name, channels, count, names, locked}`
- Ctrl+N / Ctrl+O / Ctrl+S / Ctrl+Shift+S

## Important Implementation Details

- `time.perf_counter()` spin-wait is used for microsecond precision (Windows default timer is 15.6ms)
- Manual break control via `serial.break_condition` property (not `send_break()` which is imprecise)
- Thread safety: transmitter reads `dmx_data` directly (single byte writes are GIL-safe)
- Scene library path: `_resolve_data_dir()` uses `sys.executable` dir when frozen (PyInstaller), `__file__` otherwise
- Channel index: 0-based internally, displayed as 1-based (CH001-CH512)
- Page index: 0-31, displayed as 1-32
