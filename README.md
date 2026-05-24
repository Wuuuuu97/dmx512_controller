<div align="center">
  <img src="icon.ico" width="64" alt="DMX Logo" />
  <h1>DMX 调试助手</h1>
  <p><b>DMX512 Lighting Controller</b> — 基于 Python + PyQt5 的专业灯光控制工具</p>

  <p>
    <img src="https://img.shields.io/badge/python-3.9+-blue?logo=python" alt="Python 3.9+" />
    <img src="https://img.shields.io/badge/pyqt-5.15-brightgreen?logo=qt" alt="PyQt5" />
    <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License" />
    <img src="https://img.shields.io/github/stars/Wuuuuu97/dmx512_controller?style=social" alt="GitHub Stars" />
  </p>

  <p>
    <a href="#features">功能</a> •
    <a href="#quick-start">快速开始</a> •
    <a href="#hardware">硬件接线</a> •
    <a href="#download">下载</a> •
    <a href="docs/README.md">详细文档</a>
  </p>

  <img src="docs/ui_preview.png" width="700" alt="UI Preview" />
</div>

---

## 📦 Features

| 功能 | 说明 |
|------|------|
| **512 通道控制** | 32 页 × 16 通道，2×8 推杆网格 |
| **物理推杆风格** | iOS 式白色滑块，双击数值直接键入 |
| **主控推子** | 全局 0-100% 输出缩放，不破坏原始值 |
| **黑场** | 一键全零输出，恢复保留原值 |
| **通道编组** | Ctrl+多选，同步调节 |
| **通道命名** | 右键重命名，随场景保存 |
| **通道锁定** | 锁定后滑块禁用，批量操作自动跳过 |
| **场景库** | 内置多场景管理器，JSON 本地存储 |
| **场景轮巡** | 勾选场景，设停留/淡入时间，自动循环切换 |
| **预设操作** | 全部归零 / 最大 / 取反，跳过锁定通道 |
| **帧率显示** | 状态栏实时 FPS |
| **串口自动扫描** | 自动检测可用串口，一键刷新 |

## 🚀 Quick Start

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py

# 构建单文件 exe
python build.py
```

构建产物：`build/DMX调试助手/DMX调试助手.exe`

## 🔌 Hardware

USB 转 RS-485 模块 → DMX512 设备

```
USB 转 RS-485 模块          DMX512 设备
┌─────────────┐           ┌────────────┐
│     A (+)   ├───────────┤ DATA+      │
│     B (-)   ├───────────┤ DATA-      │
│     GND     ├───────────┤ GND        │
└─────────────┘           └────────────┘
```

> 总线末端需接 **120Ω 终端电阻** 防止信号反射。

## 📖 Documentation

- [完整使用说明](docs/README.md) — 详细功能指南、快捷键、技术架构
- [开发规格书](docs/SPEC.md) — 协议细节、模块设计、验收标准

## 🛠️ Tech Stack

| 层 | 技术 |
|------|--------|
| UI | PyQt5 |
| 协议发送 | QThread + pyserial (250000 baud, 8N2) |
| 帧时序 | `time.perf_counter()` 自旋等待 (μs 级精度) |
| 打包 | PyInstaller → 单文件 exe |

## 📄 License

[MIT](LICENSE)

---

<div align="center">
  <sub>Built with ❤️ for the stage lighting community</sub>
</div>
