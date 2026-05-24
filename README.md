<div align="center">
  <img src="icon.ico" width="64" alt="DMX Logo" />
  <h1>DMX 调试助手</h1>
  <p><b>DMX512 Lighting Controller</b></p>
  <p>A DMX512 lighting control tool built with Python + PyQt5.<br>
  基于 Python + PyQt5 的 DMX512 灯光控制上位机。</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.9+-blue?logo=python" alt="Python 3.9+" />
    <img src="https://img.shields.io/badge/pyqt-5.15-brightgreen?logo=qt" alt="PyQt5" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
    <img src="https://img.shields.io/github/stars/Wuuuuu97/dmx512_controller?style=social" alt="GitHub Stars" />
  </p>

  <p>
    <a href="#features">Features</a> •
    <a href="#quick-start">Quick Start</a> •
    <a href="#hardware">Hardware</a> •
    <a href="#download">Download</a> •
    <a href="docs/CLAUDE.md">Full Guide</a>
  </p>

  <img src="docs/ui_preview.png" width="700" alt="UI Preview" />
</div>

---

## Features / 功能

| English | 中文 |
|---------|------|
| **512 Channels** — 32 pages × 16 channels, 2×8 fader grid | **512 通道控制** — 32 页 × 16 通道，2×8 推杆网格 |
| **Master Fader** — Global 0-100% output scaling, stored values unchanged | **主控推子** — 全局 0-100% 输出缩放，不破坏原始值 |
| **Blackout** — One-key all-zero output, restore preserves original values | **黑场** — 一键全零输出，恢复保留原值 |
| **Channel Grouping** — Ctrl+click multi-select, sync adjust | **通道编组** — Ctrl+多选，同步调节 |
| **Channel Naming** — Right-click rename, saved with scenes | **通道命名** — 右键重命名，随场景保存 |
| **Channel Lock** — Locks disable slider, batch ops auto-skip | **通道锁定** — 锁定后滑块禁用，批量操作自动跳过 |
| **Scene Library** — Built-in multi-scene manager, JSON storage | **场景库** — 内置多场景管理器，JSON 本地存储 |
| **Scene Chaser** — Select scenes, set interval/fade, auto loop | **场景轮巡** — 勾选场景，设停留/淡入时间，自动循环切换 |
| **Presets** — Reset all / Max all / Invert all, skip locked channels | **预设操作** — 全部归零 / 最大 / 取反，跳过锁定通道 |
| **FPS Monitor** — Real-time frame rate in status bar | **帧率显示** — 状态栏实时 FPS |
| **Language Switch** — Chinese/English toggle, Ctrl+Shift+Z/E, persists on restart | **中英双语** — 一键切换，Ctrl+Shift+Z/E，重启保持 | 
| **Auto Port Scan** — Detect available serial ports, one-click refresh | **串口自动扫描** — 自动检测可用串口，一键刷新 |

## Quick Start / 快速开始

```bash
# Install dependencies / 安装依赖
pip install -r requirements.txt

# Run / 运行
python main.py

# Build single-file exe / 构建单文件 exe
python build.py
```

Output: `build/DMX调试助手/DMX调试助手.exe`

## Hardware / 硬件接线

USB-to-RS-485 adapter → DMX512 fixture

```
USB 转 RS-485 模块          DMX512 设备
┌─────────────┐           ┌────────────┐
│     A (+)   ├───────────┤ DATA+      │
│     B (-)   ├───────────┤ DATA-      │
│     GND     ├───────────┤ GND        │
└─────────────┘           └────────────┘
```

> A **120Ω termination resistor** is required at the end of the DMX bus to prevent signal reflection.<br>
> 总线末端需接 **120Ω 终端电阻** 防止信号反射。

## Download / 下载

**Windows users**: Download the standalone exe from [Releases](https://github.com/Wuuuuu97/dmx512_controller/releases). No Python required.

**Windows 用户**：从 [Releases](https://github.com/Wuuuuu97/dmx512_controller/releases) 下载单文件 exe，无需安装 Python。

## Tech Stack / 技术栈

| Layer / 层 | Technology / 技术 |
|-------------|-------------------|
| UI | PyQt5 |
| DMX Protocol | QThread + pyserial (250000 baud, 8N2) |
| Frame Timing | `time.perf_counter()` spin-wait (μs precision) |
| Packaging | PyInstaller → single-file exe (`python build.py`) |

## Documentation / 文档

- [Full User Guide / 完整使用说明](docs/README.md) — features, shortcuts, architecture
- [Specification / 开发规格书](docs/SPEC.md) — protocol details, module design, acceptance criteria

## License / 许可

[MIT](LICENSE)

---

<div align="center">
  <sub>Built for the stage lighting community · 为舞台灯光社区制作</sub>
</div>
