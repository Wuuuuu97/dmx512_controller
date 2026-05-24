# DMX512 串口控制器

## Overview

基于 Python + PyQt5 的 DMX512 灯光控制工具，通过 USB 转串口模块（RS-485）输出标准 DMX512 协议信号，控制最多 512 个 DMX 通道。

## Functional Requirements

### Must Have
- **FR-1**: 512个DMX通道，分页显示，每页16个通道，共32页
- **FR-2**: 通道控件为垂直 QSlider (0-255) + 通道号标签 + 当前值标签，双击数值可直接输入
- **FR-3**: 左侧面板 4×8 网格页数按钮快速切换，高亮显示当前页
- **FR-4**: 串口配置：端口选择下拉（自动扫描可用串口）、刷新按钮，波特率固定 250000
- **FR-5**: 启动/停止 DMX 信号发送按钮，发送时禁用端口选择和刷新
- **FR-6**: 状态栏显示 LED 指示灯（绿色=发送中/红色=未连接）+ 状态文字 + FPS
- **FR-7**: 菜单栏 — 文件(新建/打开/保存/另存为/退出)、串口(刷新/断开)、预设(归零/最大/取反)、视图(状态栏开关)、帮助
- **FR-8**: 场景保存/加载（JSON格式，含512通道数据）
- **FR-9**: 全部归零、全部最大(255)、全部取反功能

### Nice to Have
- **FR-10**: 帧率显示（状态栏永久标签）
- **FR-11**: 窗口关闭时自动停止发送并释放串口
- **FR-12**: 物理推杆风格滑块（白色手柄 + 水平 grip 线）
- **FR-13**: 程序绘制应用图标（圆形 DMX 标识）

## Technical Architecture

### Design Decisions
- **DD-1**: PyQt5 — 成熟稳定，生态丰富
- **DD-2**: 独立工作线程发送 DMX — 避免阻塞 UI，使用 `QThread` + while 循环
- **DD-3**: pyserial `send_break(0.0001)` + `time.sleep(0.000012)` 方案 — 跨平台兼容，符合 DMX512 时序要求
- **DD-4**: 2×8 网格每页 — 充分利用屏幕横向空间，推杆保持可操作大小
- **DD-5**: 场景文件使用 JSON 格式 — 可读性好，易于编辑和调试
- **DD-6**: 左侧面板集成页数 + 串口 + 控制按钮 — 操作集中，减少鼠标移动距离

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  MenuBar: 文件(&F) | 串口(&S) | 预设(&P) | 场景(&C) | 视图(&V) | 语言(&L) | 帮助(&H)   │
├──────────┬──────────────────────────────────────────────────────┤
│          │               第 1 / 32 页 (通道 1–16)                │
│  01  02  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  03  04  │  │CH001 │ │CH002 │ │CH003 │ │CH004 │               │
│  05  06  │  │ ═╬══  │ │ ═╬══  │ │ ═╬══  │ │ ═╬══  │               │
│  07  08  │  │  128  │ │  0    │ │  255  │ │  64  │               │
│  09  10  │  ├──────┤ ├──────┤ ├──────┤ ├──────┤               │
│  11  12  │  │CH005 │ │CH006 │ │CH007 │ │CH008 │               │
│  13  14  │  │ ═╬══  │ │ ═╬══  │ │ ═╬══  │ │ ═╬══  │               │
│  15  16  │  │  ...  │ │  ...  │ │  ...  │ │  ...  │               │
│  17  18  │  └──────┘ └──────┘ └──────┘ └──────┘               │
│  19  20  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  21  22  │  │CH009 │ │CH010 │ │CH011 │ │CH012 │               │
│  23  24  │  │ ═╬══  │ │ ═╬══  │ │ ═╬══  │ │ ═╬══  │               │
│  25  26  │  │ ...   │ │ ...   │ │ ...   │ │ ...   │               │
│  27  28  │  ├──────┤ ├──────┤ ├──────┤ ├──────┤               │
│  29  30  │  │CH013 │ │CH014 │ │CH015 │ │CH016 │               │
│  31  32  │  │ ═╬══  │ │ ═╬══  │ │ ═╬══  │ │ ═╬══  │               │
│  ─────── │  │ ...   │ │ ...   │ │ ...   │ │ ...   │               │
│  串口     │  └──────┘ └──────┘ └──────┘ └──────┘               │
│ [COM3▼]↻ │                                                      │
│  ─────── │                                                      │
│ ▶ Start  │                                                      │
│ ■ Stop   │                                                      │
│ 全部归零  │                                                      │
├──────────┴──────────────────────────────────────────────────────┤
│  ● 已停止                          FPS: 36                      │
└─────────────────────────────────────────────────────────────────┘
```

### Menu Bar Design

```
文件(&F)          串口(&S)         预设(&P)         场景(&C)         视图(&V)         语言(&L)         帮助(&H)
├─ 新建场景 Ctrl+N ├─ 刷新端口 F5  ├─ 全部归零 Ctrl+R├─ 场景库 Ctrl+L  ├─ ✓ 显示状态栏 ├─ 中文 ✓       ├─ 关于 DMX512
├─ ─────────────── ├─ ──────────── ├─ 全部最大(255) ├─ 场景轮巡       │              ├─ English      ├─ 使用说明
├─ 打开场景 Ctrl+O ├─ 断开连接     ├─ 全部取反      │               │              │              ├─ ──────────
├─ 保存场景 Ctrl+S │              ├─ ──────────── │               │              │              ├─ 关于
├─ 另存为 Ctrl+Sh+S│              │               │               │              │
├─ ─────────────── │              │               │               │              │
├─ 重启 Ctrl+Sh+R  │              │               │               │              │
├─ ─────────────── │              │               │               │              │
└─ 退出 Alt+F4     │              │               │               │              │
```

### Data Flow

```
UI Slider Change → update_channel(ch, val) → DMX Transmitter reads
                                               → send_break(100μs)
                                               → sleep(12μs) MAB
                                               → serial.write(StartCode + 512 bytes)
                                               → sleep(5ms) → repeat (~36Hz)
```

### Data Model
- **dmx_data**: `bytearray(512)` — 共享通道数据缓冲区（GIL保护单字节操作）
- **page_count**: 32（固定）
- **channels_per_page**: 16（固定，2行×8列）
- **current_page**: `int` 0–31 — 当前显示页面
- **running**: `bool` — 发送线程状态标志
- **current_file_path**: `str|None` — 当前场景文件路径（用于保存覆盖）
- **_channel_names**: `dict[int, str]` — 通道自定义名称映射
- **_channel_locks**: `set[int]` — 锁定通道索引集合
- **_current_language**: `"zh"|"en"` — 当前语言（LanguageManager 维护）

### Scene File Format (JSON)
```json
{
    "name": "My Scene",
    "channels": [0, 128, 255, 0, ...],
    "count": 512,
    "names": {"0": "面光 1", "1": "面光 2", "100": "LED 染色"},
    "locked": [5, 6, 7]
}
```

## Implementation Plan

### Dependencies
- PyQt5 >= 5.15
- pyserial >= 3.5

### File Structure

```
D:/work/dmx512_controller/
├── main.py                  # 程序入口（i18n 初始化、窗口启动）
├── build.py                 # PyInstaller 单文件打包脚本
├── build_icon.py            # 图标生成脚本
├── requirements.txt         # 依赖清单
├── icon.ico                 # 程序图标
├── README.md                # 双语 README（中英对照）
├── LICENSE                  # MIT 许可
├── docs/
│   ├── CLAUDE.md            # 英文项目概览（给 AI 用的）
│   └── SPEC.md              # 规格说明书（中文）
└── src/
    ├── __init__.py
    ├── dmx/
    │   ├── __init__.py
    │   └── transmitter.py   # DMX512 协议发送线程（QThread）
    ├── engine/
    │   ├── __init__.py
    │   └── chaser.py        # 场景轮巡引擎（QThread + 淡入淡出）
    ├── i18n/
    │   ├── __init__.py
    │   └── translations.py  # LanguageManager 单例、tr()、TRANSLATIONS 中英字典
    └── ui/
        ├── __init__.py
        ├── main_window.py   # 主窗口（菜单栏+左侧面板+通道区+状态栏+i18n 重新翻译）
        ├── page_widget.py   # 页面控件（2×8 网格）
        ├── channel_widget.py# 单通道控件（滑块+标签+选中/锁定/重命名）
        ├── serial_panel.py  # 串口控制面板（未使用，保留）
        ├── scene_library.py # 场景库对话框（保存/加载/重命名/删除）
        └── chaser_panel.py  # 场景轮巡面板（勾选场景、停留/淡入时间）
```

## DMX512 Protocol Detail

```
Frame Structure:
┌───────┬──────┬──────────┬─────────────────────────────────┐
│ Break │ MAB  │ Start    │ Channel Data (512 bytes)        │
│ ≥88μs │ ≥8μs │ Code 0x00│ Ch1 │ Ch2 │ Ch3 │ ... │ Ch512  │
└───────┴──────┴──────────┴─────────────────────────────────┘

Serial Settings: 250000 baud, 8 data bits, 2 stop bits, no parity
Frame Time = Break(100μs) + MAB(12μs) + 513*11bits/250000 = ~22.6ms
Refresh Rate: ~36 Hz (理论 ~44 Hz 无帧间隔)
```

### Implementation Details
- **Break**: `serial.send_break(0.0001)` — 发送 100μs 低电平
- **MAB**: `time.sleep(0.000012)` — send_break 后线路自动恢复为 marking 态，延时 12μs 满足 ≥8μs 要求
- **Start Code**: 固定 `0x00`
- **帧间隔**: ~5ms (总帧周期 ~28ms，实际约 35fps+)

### Error Recovery
- 连续 3 次发送失败自动停止线程
- USB 拔出检测（Windows 错误码 1167 ERROR_DEVICE_REMOVED）
- 串口消失检测（Windows 错误码 2 ERROR_FILE_NOT_FOUND）

## Error Handling

| 条件 | 处理方式 |
|------|---------|
| 串口打开失败 | QMessageBox 弹窗提示详情 |
| 发送中串口错误 | 自动停止发送，状态栏红色提示 |
| 连续3次发送失败 | 停止发送线程，避免无限重试 |
| USB 设备拔出 | 检测 ERROR_DEVICE_REMOVED，状态栏提示并停止 |
| 串口不存在（设备已拔出） | 检测 ERROR_FILE_NOT_FOUND，状态栏提示并停止 |
| 未选串口点 Start | QMessageBox 警告"请先选择串口" |
| 串口列表为空 | 下拉显示"无可用串口" |
| 场景文件加载失败 | QMessageBox 弹窗提示错误详情 |
| 窗口关闭 | 自动 Stop 发送 → 关闭串口 → 终止线程 |

## Acceptance Criteria

- [ ] 启动后显示 32 页通道，默认第 1 页
- [ ] 垂直滑块拖动实时更新通道值和数值显示
- [ ] 双击数值标签弹出输入框，可直接键入 0-255
- [ ] 左侧页数按钮高亮当前页，点击切换正常
- [ ] 左侧页数按钮 4×8 排列整齐
- [ ] 自动扫描可用串口，下拉列出
- [ ] 选择串口后点击 Start 开始发送 DMX 帧
- [ ] 发送期间端口选择和刷新按钮禁用
- [ ] Stop 停止发送，恢复端口选择
- [ ] LED 指示灯：发送中绿色，停止/未连接红色
- [ ] 菜单栏各项功能正常（新建/打开/保存/归零/最大/取反）
- [ ] 场景文件保存为 JSON，加载后通道值正确恢复
- [ ] 状态栏显示发送状态和端口信息
- [ ] 关闭程序时自动停止发送并释放串口
- [ ] 全部归零/全部最大/全部取反弹出确认对话框
- [ ] 拔出 USB 串口时自动停止并提示

---

# 通道操作增强

## 功能描述

在现有单通道滑条控制基础上，增加批量操作和灵活调配能力。

## FR-20: 主控推子 (Master Fader)

全局输出比例控制，对所有通道值按百分比缩放。

### Acceptance Criteria
- [ ] 界面增加一个主控推子控件（位于左侧面板底部或工具栏区域）
- [ ] 主控推子范围 0–100（百分比）
- [ ] 主控推子为 100% 时，通道输出值不受影响
- [ ] 主控推子为 50% 时，所有通道实际输出值减半（取整）
- [ ] 主控推子为 0% 时，所有通道输出 0（黑场）
- [ ] 主控推子不影响 dmx_data 原始存储值，仅在发送时缩放
- [ ] 推子拖动时实时生效，无延迟

### Technical Design

```
dmx_data (0-255) ──→ Master Scale (%) ──→ scaled value → serial write
     ↑                     ↑
  滑条控制值          主控推子值
```

**实现方式**：发送线程在构建帧时对 bytearray 做一次遍历缩放，原始值保留不变。

```python
# 发送帧时缩放
scale = self._master_level / 100.0  # 0.0 ~ 1.0
if scale < 1.0:
    frame = bytes([0x00]) + bytes(int(b * scale) for b in self.dmx_data)
else:
    frame = bytes([0x00]) + self.dmx_data
```

---

## FR-21: 通道编组

允许用户选择多个通道，联动调节。

### Acceptance Criteria
- [ ] 点击通道号可选中/取消选中该通道
- [ ] 选中通道以高亮边框标识
- [ ] 按住 Ctrl 点击可多选
- [ ] 选中 ≥2 个通道后，拖动任一选中的滑块，所有选中的通道同步变化
- [ ] 同步变化保持各通道原有比例（相对值模式）或设为相同值（绝对值模式）
- [ ] 在页面空白处点击取消全部选中

### Technical Design

**ChannelWidget 新增**：
- 点击 label_ch 切换选中状态
- 选中时 `setObjectName("channelLabelSelected")` + 刷新样式
- 新增信号 `selection_changed(int channel, bool selected)`

**PageWidget 新增**：
- 维护本页选中通道集合
- 接收组调节信号，批量调用 set_value

**MainWindow 协调**：
- 跨页选择管理（或限制为同页编组）

---

## FR-22: 通道命名

允许用户为每个通道设置自定义名称，替代默认的 CH001。

### Acceptance Criteria
- [ ] 右键点击通道号弹出重命名菜单
- [ ] 输入框默认显示当前名称（默认 CH001–CH512）
- [ ] 自定义名称保存后立即更新显示
- [ ] 名称随场景文件一起保存/加载（在 JSON 中增加 names 字段）
- [ ] 支持清空名称恢复默认

### Technical Design

**数据模型扩展**：
```python
self.channel_names = [f"CH{i+1:03d}" for i in range(512)]  # 默认可推导，不实际存储
# 仅存储用户自定义的名称
self.channel_overrides: dict[int, str] = {}  # {index: name}
```

**场景文件格式扩展**：
```json
{
    "name": "My Scene",
    "channels": [0, 128, ...],
    "count": 512,
    "names": {0: "面光 1", 1: "面光 2", 100: "LED 染色"}
}
```

---

## FR-23: 通道锁定

锁定指定通道，防止误触。

### Acceptance Criteria
- [ ] 通道号旁显示锁定图标（🔒 或自定义图标）
- [ ] 锁定通道的滑块不可拖动
- [ ] 锁定通道不受批量操作影响（全部归零/最大/取反/主控推子除外？需定义）
- [ ] 锁定状态随场景文件保存
- [ ] 锁定/解锁通过右键菜单或快捷键切换

---

---

# 场景管理增强

## 功能描述

在现有单文件场景 I/O 基础上，增加内置场景库和自动化控制能力。

## FR-30: 场景库面板

在应用内直接管理多个场景，无需文件对话框。

### Acceptance Criteria
- [ ] 新增场景库面板（可停靠在左侧或右侧，或独立窗口）
- [ ] 场景列表显示场景名称（用户自定义）
- [ ] 支持：保存当前通道状态为新场景、删除场景、重命名场景
- [ ] 点击场景名称立即加载（恢复所有通道值）
- [ ] 场景库存储在本地单一 JSON 文件中（`scenes.json`）
- [ ] 启动时自动加载场景库
- [ ] 加载场景时自动跳转到对应页以反馈变化

### Technical Design

**数据结构**：
```python
@dataclass
class SceneItem:
    name: str
    channels: list[int]  # 512 values
    names: dict[int, str] | None = None  # 可选通道名称
```

**存储文件**：`scenes/scenes.json`（打包后在同级 `scenes/` 目录下）

```json
{
    "scenes": [
        {"name": "开场白光", "channels": [255, 255, 255, 0, ...], "names": {}, "locked": []},
        {"name": "蓝色氛围", "channels": [0, 0, 128, 0, ...], "names": {}, "locked": []}
    ]
}
```

---

## FR-31: 场景轮巡 (Chaser)

按设定的顺序和时间间隔自动切换场景。

### Acceptance Criteria
- [ ] 场景轮巡面板中选择参与轮巡的场景（多选）
- [ ] 设置停留时间（0.5s–60s，步进 0.5s）
- [ ] 点击 ▶ 开始轮巡，■ 停止
- [ ] 轮巡中当前场景自动切换，界面同步更新
- [ ] 切换到下一场景时支持淡入淡出（跨场景过渡）
- [ ] 支持循环模式（最后一场景结束后返回第一个）
- [ ] 停止轮巡后停留在当前场景

### Technical Design

**ChaserEngine**（QThread 子类）：
```python
class ChaserEngine(QThread):
    scene_changed = pyqtSignal(int)  # scene index

    def __init__(self, scenes, interval_ms=2000, fade_ms=500):
        ...
```

**淡入淡出实现**：
- 启动过渡线程，从当前场景值逐步逼近目标场景值
- 步进增量按 `fade_ms / 帧间隔(23ms)` 计算
- 过渡期间主控线程暂停，由过渡线程接管帧发送

---

## FR-32: 黑场 / 恢复 (Blackout)

一键黑场，再按恢复。

### Acceptance Criteria
- [ ] 快捷键或专用按钮（建议 Space 或 B）
- [ ] 按下时所有通道输出 0（不修改 dmx_data 原始值）
- [ ] 再次按下恢复之前的状态
- [ ] 黑场期间界面显示明显提示（红色边框/闪烁文字）
- [ ] 黑场优先于所有其他控制

### Technical Design

```
Blackout 模式：
  dmx_data 保持不变
  blackout_active = True 时，发送帧全部填 0
  blackout_active = False 时恢复正常发送
```

发送线程判断：
```python
if self._blackout:
    frame = bytes([0x00]) + bytes(512)  # 全部 0
else:
    frame = bytes([0x00]) + scaled_data
```

---

# 国际化 (i18n)

## FR-40: 中英文语言切换

UI 界面支持中文/英文动态切换，切换后所有文字立即更新，无需重启。

### Acceptance Criteria
- [x] 菜单栏添加"语言(&L)"菜单，包含"中文"和"English"两个选项，互斥勾选
- [x] 切换语言后所有菜单、按钮、标签、状态栏、对话框文字立即切换
- [x] 已打开的场景库/场景轮巡等对话框立即生效（重启后按新语言显示）
- [x] 语言偏好保存到 `scenes/settings.json`，下次启动自动恢复
- [x] 快捷键：Ctrl+Shift+Z 切换中文，Ctrl+Shift+E 切换英文
- [x] 英文下使用说明、关于 DMX512、快捷键等完整内容均为英文
- [x] 翻译缺失时自动降级：英文 → 中文 → 显示 key（永不崩溃）

### Technical Design

**架构**：Python dict-based，无外部依赖。

```
src/i18n/
├── __init__.py
└── translations.py    # LanguageManager (QObject) + tr() + TRANSLATIONS
```

**核心机制**：
- `LanguageManager` 单例，继承 `QObject`，发射 `language_changed` 信号
- 各窗口连接该信号，在槽函数中重新设置所有文字
- `tr(key, **kwargs)` 全局函数，支持 `str.format()` 参数替换

**翻译字典**（~70 keys × 2 languages）：
```python
TRANSLATIONS = {
    "zh": { "window_title": "DMX 调试助手", "btn_start": "▶ Start", ... },
    "en": { "window_title": "DMX Debug Assistant", "btn_start": "▶ Start", ... },
}
```

**重新翻译策略**：

| UI 类型 | 重新翻译方式 |
|---------|------------|
| 主窗口持久控件 | `language_changed` → `_retranslate_ui()` 逐个 setText |
| 菜单栏 | 同一方法重新设置 setTitle/setText |
| 模态对话框 | 构造时读取 `tr()`，关闭后下次重建 |
| 右键菜单 | 每次 `contextMenuEvent()` 重建，自动用当前语言 |

**持久化**：
```json
// scenes/settings.json
{ "language": "en" }
```

路径解析：frozen 时为 `sys.executable` 同级 `scenes/settings.json`，源码运行时为项目根 `scenes/settings.json`。

---

## FR-41: 软件重启

File → 重启软件 (Ctrl+Shift+R)

### Acceptance Criteria
- [x] 菜单栏文件菜单添加"重启软件"选项
- [x] 点击后弹出确认对话框
- [x] 确认后先停止 DMX 发送、释放串口
- [x] 使用 QProcess.startDetached 启动新进程后关闭当前窗口

### Technical Design
```python
def _restart_application(self):
    self._stop_transmission()
    QApplication.processEvents()  # 确保串口资源完全释放
    if getattr(sys, "frozen", False):
        args = [sys.executable]
    else:
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        args = [sys.executable, os.path.join(root, "main.py")]
    QProcess.startDetached(args[0], args[1:])
    self.close()
```

---

# 附录：优先级建议

| 优先级 | 功能 | 工作量 | 说明 |
|--------|------|--------|------|
| P0 | 主控推子 (FR-20) | 小 | 改动小，实用价值高 |
| P0 | 黑场/恢复 (FR-32) | 小 | 演出安全功能，实现简单 |
| P1 | 场景库面板 (FR-30) | 中 | 替代文件对话框，日常操作频率高 |
| P1 | 通道命名 (FR-22) | 中 | 提升可读性，涉及场景格式变更 |
| P1 | 通道编组 (FR-21) | 中 | 批量调灯核心功能 |
| P2 | 通道锁定 (FR-23) | 小 | 防止误触，实现简单 |
| P2 | 场景轮巡 (FR-31) | 大 | 涉及线程控制和淡入淡出算法 |
