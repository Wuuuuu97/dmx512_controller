"""Internationalization module for DMX Debug Assistant.

Provides a `tr(key, **kwargs)` function for translating UI strings
and a `LanguageManager` singleton that emits ``language_changed``
when the user switches languages.

Usage::

    from src.i18n.translations import tr, set_language, get_manager

    label.setText(tr("app_name"))
    get_manager().language_changed.connect(self._retranslate_ui)
"""

import json
import os
import sys

from PyQt5.QtCore import QObject, pyqtSignal

TRANSLATIONS = {
    "zh": {
        # ---- Application ----
        "app_name": "DMX 调试助手",
        "window_title": "DMX 调试助手",
        # ---- Left panel ----
        "page_title": "页数",
        "port_label": "串口",
        "refresh_port_tooltip": "刷新串口列表",
        "btn_start": "▶ Start",
        "btn_stop": "■ Stop",
        "btn_blackout": "黑场",
        "btn_reset": "全部归零",
        "master_label": "主控",
        "master_value": "100%",
        "no_ports_available": "无可用串口",
        # ---- Status bar ----
        "status_ready": "就绪 — 未连接",
        "status_sending": "发送中 — {port}",
        "status_stopped": "已停止",
        "status_blackout": "黑场",
        "status_new_scene": "已新建场景",
        "status_loaded": "已加载: {name}",
        "status_saved": "已保存: {name}",
        "status_scene_library_loaded": "已加载场景库场景",
        # ---- Page display ----
        "page_label": "第 {current} / 32 页    通道 {start}–{end}",
        # ---- Menu: 文件 ----
        "menu_file": "文件(&F)",
        "act_new_scene": "新建场景(&N)",
        "act_open_scene": "打开场景(&O)...",
        "act_save_scene": "保存场景(&S)",
        "act_save_as": "另存为(&A)...",
        "act_restart": "重启软件(&R)",
        "act_exit": "退出(&X)",
        # ---- Menu: 串口 ----
        "menu_serial": "串口(&S)",
        "act_refresh_port": "刷新端口(&R)",
        "act_disconnect": "断开连接(&D)",
        # ---- Menu: 预设 ----
        "menu_preset": "预设(&P)",
        "act_reset_all": "全部归零",
        "act_set_all_max": "全部最大 (255)",
        "act_invert_all": "全部取反",
        # ---- Menu: 场景 ----
        "menu_scene": "场景(&C)",
        "act_scene_library": "场景库(&L)",
        "act_chaser": "场景轮巡(&H)",
        # ---- Menu: 视图 ----
        "menu_view": "视图(&V)",
        "act_show_statusbar": "显示状态栏",
        # ---- Menu: 语言 ----
        "menu_language": "语言(&L)",
        "lang_chinese": "中文",
        "lang_english": "English",
        # ---- Menu: 帮助 ----
        "menu_help": "帮助(&H)",
        "act_about_dmx": "关于 DMX512",
        "act_usage": "使用说明",
        "act_about": "关于(&A)",
        # ---- Confirmations ----
        "confirm_title": "确认",
        "confirm_reset_all": "确定将所有通道归零吗？\n(锁定通道不受影响)",
        "confirm_set_all_max": "确定将所有通道设为 255 吗？\n(锁定通道不受影响)",
        "confirm_new_scene_title": "新建场景",
        "confirm_new_scene": "确定要新建场景吗？\n当前所有通道数据将被清除。",
        "confirm_restart_title": "确认重启",
        "confirm_restart": "确定要重启软件吗？\n未保存的场景数据将丢失。",
        # ---- Error / Warning ----
        "serial_error_title": "串口错误",
        "select_port_first": "请先选择串口",
        "cannot_open_port": "无法打开串口:\n{error}\n\n可能的原因:\n• 串口已被其他程序占用\n• 设备未连接或驱动未安装\n• 权限不足",
        "system_error_title": "系统错误",
        "cannot_access_port": "无法访问串口:\n{error}\n\n请检查设备连接后重试。",
        "format_error_title": "格式错误",
        "channel_data_incomplete": "通道数据不完整 (需要 512 个值)",
        "load_failed_title": "加载失败",
        "save_failed_title": "保存失败",
        # ---- File dialogs ----
        "dialog_open_scene": "打开场景",
        "dialog_save_scene": "保存场景",
        "dialog_default_filename": "untitled.dmx",
        "scene_file_filter": "DMX Scene (*.dmx *.json);;All Files (*)",
        # ---- Channel rename dialog ----
        "rename_channel_title": "重命名通道 {channel}",
        "rename_channel_label": "输入通道名称 (留空恢复默认):",
        # ---- Channel context menu ----
        "context_rename": "重命名",
        "context_lock": "锁定",
        "context_unlock": "解锁",
        "context_reset": "归零",
        "context_channel_info": "通道: {name}",
        # ---- Channel value input ----
        "input_channel_title": "通道 {name}",
        "input_channel_label": "输入数值 (0-255):",
        # ---- Scene library ----
        "scene_library_title": "场景库",
        "scene_library_heading": "场景库",
        "btn_save_current": "保存当前场景",
        "btn_load": "加载",
        "btn_rename": "重命名",
        "btn_delete": "删除",
        "btn_close": "关闭",
        "load_failed_text": "无法加载场景库:\n{error}",
        "save_failed_text": "无法保存场景库:\n{error}",
        "save_scene_dialog": "保存场景",
        "scene_name_label": "场景名称:",
        "scene_exists_title": "已存在",
        "scene_exists_text": "场景「{name}」已存在，是否覆盖？",
        "data_error_title": "数据错误",
        "scene_data_incomplete": "场景通道数据不完整",
        "rename_dialog_title": "重命名",
        "rename_dialog_label": "新名称:",
        "confirm_delete_title": "确认删除",
        "confirm_delete_text": "确定删除场景「{name}」吗？",
        # ---- Chaser panel ----
        "chaser_title": "场景轮巡",
        "chaser_heading": "场景轮巡",
        "chaser_help": "勾选参与轮巡的场景，设置时间后点击 ▶ 开始",
        "dwell_time_label": "停留时间:",
        "fade_in_label": "淡入:",
        "ms_suffix": " ms",
        "chaser_btn_start": "▶ 开始",
        "chaser_btn_stop": "■ 停止",
        "chaser_status_ready": "就绪",
        "chaser_status_running": "轮巡中...",
        "chaser_status_stopped": "已停止",
        "chaser_hint_title": "提示",
        "chaser_select_at_least_one": "请至少勾选一个场景",
        # ---- Help content ----
        "dmx_info_title": "关于 DMX512",
        "dmx_info_text": (
            "DMX512 是数字多路复用协议，用于舞台灯光控制。\n\n"
            "• 512 个通道，每通道 0-255\n"
            "• 波特率: 250,000 bps\n"
            "• 8 数据位, 2 停止位, 无校验\n"
            "• 帧率: ~36 Hz\n"
            "• 物理层: RS-485"
        ),
        "usage_title": "使用说明",
        "usage_text": (
            "── 基本操作 ──\n"
            "1. 连接 USB 转 RS-485 模块到电脑\n"
            "2. 在左侧「串口」下拉选择端口，点击 ↻ 刷新\n"
            "3. 点击「Start」开始发送 DMX 信号\n"
            "4. 拖动通道滑块控制灯具亮度（0-255）\n"
            "5. 点击「Stop」停止发送\n\n"
            "── 通道控制 ──\n"
            "• 拖动滑块 — 实时调节通道值\n"
            "• 双击数值 — 弹出输入框，直接键入\n"
            "• 右键通道 → 重命名 / 锁定 / 归零\n"
            "• 锁定通道的滑块禁用，批量操作自动跳过\n\n"
            "── 编组操作 ──\n"
            "• 点击通道编号选中（蓝色高亮）\n"
            "• Ctrl+点击多选\n"
            "• 选中多个通道后，拖动任一滑块，所有选中同步变化\n\n"
            "── 页面切换 ──\n"
            "• 左侧 4×8 网格按钮快速跳转\n"
            "• 当前页高亮显示\n\n"
            "── 主控推子 ──\n"
            "• 左侧底部「主控」滑块全局缩放所有通道输出 (0-100%)\n"
            "• 不影响原始存储值，仅实时缩放发送帧\n\n"
            "── 黑场 ──\n"
            "• 点击「黑场」按钮一键输出全零\n"
            "• 再次点击恢复正常\n"
            "• 黑场时 LED 保持发送状态\n\n"
            "── 预设 (菜单栏「预设」) ──\n"
            "• 全部归零 (Ctrl+R) — 所有通道归零\n"
            "• 全部最大 — 所有通道设 255\n"
            "• 全部取反 — 值翻转 (0↔255)\n"
            "• 锁定通道不受预设操作影响\n\n"
            "── 场景文件 (菜单栏「文件」) ──\n"
            "• Ctrl+S 保存 / Ctrl+Shift+S 另存为\n"
            "• Ctrl+O 打开 / Ctrl+N 新建\n"
            "• 场景文件包含通道值、名称、锁定状态\n\n"
            "── 场景库 (Ctrl+L) ──\n"
            "• 在应用内保存/加载/删除/重命名多个场景\n"
            "• 数据存储于 scenes/scenes.json\n\n"
            "── 场景轮巡 (菜单栏「场景」) ──\n"
            "• 勾选场景库中的场景参与轮巡\n"
            "• 设置停留时间和淡入时长\n"
            "• 轮巡期间自动按序切换，支持线性淡入淡出\n\n"
            "── 快捷键 ──\n"
            "Ctrl+N  新建场景\n"
            "Ctrl+O  打开场景文件\n"
            "Ctrl+S  保存场景\n"
            "Ctrl+Shift+S  另存为\n"
            "Ctrl+R  全部归零\n"
            "Ctrl+L  打开场景库\n"
            "F5      刷新串口列表\n"
            "Alt+F4  退出程序"
        ),
        "about_title": "关于 DMX 调试助手",
        "about_text": (
            "DMX 调试助手 v1.0\n\n"
            "基于 Python + PyQt5 的 DMX512 灯光控制工具。\n"
            "通过 USB 转串口模块输出 DMX512 协议信号。\n\n"
            "作者: Wuuuu"
        ),
    },
    "en": {
        # ---- Application ----
        "app_name": "DMX Debug Assistant",
        "window_title": "DMX Debug Assistant",
        # ---- Left panel ----
        "page_title": "Pages",
        "port_label": "Port",
        "refresh_port_tooltip": "Refresh port list",
        "btn_start": "▶ Start",
        "btn_stop": "■ Stop",
        "btn_blackout": "Blackout",
        "btn_reset": "Reset All",
        "master_label": "Master",
        "master_value": "100%",
        "no_ports_available": "No ports available",
        # ---- Status bar ----
        "status_ready": "Ready — Not connected",
        "status_sending": "Sending — {port}",
        "status_stopped": "Stopped",
        "status_blackout": "BLACKOUT",
        "status_new_scene": "New scene created",
        "status_loaded": "Loaded: {name}",
        "status_saved": "Saved: {name}",
        "status_scene_library_loaded": "Scene library scene loaded",
        # ---- Page display ----
        "page_label": "Page {current} / 32    Ch {start}–{end}",
        # ---- Menu: File ----
        "menu_file": "File(&F)",
        "act_new_scene": "New Scene(&N)",
        "act_open_scene": "Open Scene(&O)...",
        "act_save_scene": "Save Scene(&S)",
        "act_save_as": "Save As(&A)...",
        "act_restart": "Restart(&R)",
        "act_exit": "Exit(&X)",
        # ---- Menu: Serial ----
        "menu_serial": "Serial(&S)",
        "act_refresh_port": "Refresh Ports(&R)",
        "act_disconnect": "Disconnect(&D)",
        # ---- Menu: Preset ----
        "menu_preset": "Preset(&P)",
        "act_reset_all": "Reset All",
        "act_set_all_max": "All Max (255)",
        "act_invert_all": "Invert All",
        # ---- Menu: Scene ----
        "menu_scene": "Scene(&C)",
        "act_scene_library": "Scene Library(&L)",
        "act_chaser": "Chase(&H)",
        # ---- Menu: View ----
        "menu_view": "View(&V)",
        "act_show_statusbar": "Show Status Bar",
        # ---- Menu: Language ----
        "menu_language": "Language(&L)",
        "lang_chinese": "中文",
        "lang_english": "English",
        # ---- Menu: Help ----
        "menu_help": "Help(&H)",
        "act_about_dmx": "About DMX512",
        "act_usage": "Usage Guide",
        "act_about": "About(&A)",
        # ---- Confirmations ----
        "confirm_title": "Confirm",
        "confirm_reset_all": "Reset all channels to 0?\n(Locked channels will be skipped)",
        "confirm_set_all_max": "Set all channels to 255?\n(Locked channels will be skipped)",
        "confirm_new_scene_title": "New Scene",
        "confirm_new_scene": "Create a new scene?\nAll current channel data will be cleared.",
        "confirm_restart_title": "Confirm Restart",
        "confirm_restart": "Restart the application?\nUnsaved scene data will be lost.",
        # ---- Error / Warning ----
        "serial_error_title": "Serial Error",
        "select_port_first": "Please select a serial port first",
        "cannot_open_port": "Cannot open port:\n{error}\n\nPossible causes:\n• Port is already in use by another program\n• Device not connected or driver not installed\n• Insufficient permissions",
        "system_error_title": "System Error",
        "cannot_access_port": "Cannot access port:\n{error}\n\nPlease check the device connection and try again.",
        "format_error_title": "Format Error",
        "channel_data_incomplete": "Channel data incomplete (512 values required)",
        "load_failed_title": "Load Failed",
        "save_failed_title": "Save Failed",
        # ---- File dialogs ----
        "dialog_open_scene": "Open Scene",
        "dialog_save_scene": "Save Scene",
        "dialog_default_filename": "untitled.dmx",
        "scene_file_filter": "DMX Scene (*.dmx *.json);;All Files (*)",
        # ---- Channel rename dialog ----
        "rename_channel_title": "Rename Channel {channel}",
        "rename_channel_label": "Enter channel name (leave empty for default):",
        # ---- Channel context menu ----
        "context_rename": "Rename",
        "context_lock": "Lock",
        "context_unlock": "Unlock",
        "context_reset": "Reset",
        "context_channel_info": "Channel: {name}",
        # ---- Channel value input ----
        "input_channel_title": "Channel {name}",
        "input_channel_label": "Enter value (0-255):",
        # ---- Scene library ----
        "scene_library_title": "Scene Library",
        "scene_library_heading": "Scene Library",
        "btn_save_current": "Save Current Scene",
        "btn_load": "Load",
        "btn_rename": "Rename",
        "btn_delete": "Delete",
        "btn_close": "Close",
        "load_failed_text": "Cannot load scene library:\n{error}",
        "save_failed_text": "Cannot save scene library:\n{error}",
        "save_scene_dialog": "Save Scene",
        "scene_name_label": "Scene name:",
        "scene_exists_title": "Already Exists",
        "scene_exists_text": "Scene \"{name}\" already exists. Overwrite?",
        "data_error_title": "Data Error",
        "scene_data_incomplete": "Scene channel data is incomplete",
        "rename_dialog_title": "Rename",
        "rename_dialog_label": "New name:",
        "confirm_delete_title": "Confirm Delete",
        "confirm_delete_text": "Are you sure you want to delete scene \"{name}\"?",
        # ---- Chaser panel ----
        "chaser_title": "Scene Chaser",
        "chaser_heading": "Scene Chaser",
        "chaser_help": "Check scenes to include, set timing, then click ▶ to start",
        "dwell_time_label": "Dwell time:",
        "fade_in_label": "Fade in:",
        "ms_suffix": " ms",
        "chaser_btn_start": "▶ Start",
        "chaser_btn_stop": "■ Stop",
        "chaser_status_ready": "Ready",
        "chaser_status_running": "Running...",
        "chaser_status_stopped": "Stopped",
        "chaser_hint_title": "Notice",
        "chaser_select_at_least_one": "Please select at least one scene",
        # ---- Help content ----
        "dmx_info_title": "About DMX512",
        "dmx_info_text": (
            "DMX512 is a digital multiplex protocol for stage lighting control.\n\n"
            "• 512 channels, 0-255 per channel\n"
            "• Baud rate: 250,000 bps\n"
            "• 8 data bits, 2 stop bits, no parity\n"
            "• Frame rate: ~36 Hz\n"
            "• Physical layer: RS-485"
        ),
        "usage_title": "Usage Guide",
        "usage_text": (
            "── Basic Operations ──\n"
            "1. Connect USB-to-RS-485 adapter to your computer\n"
            "2. Select the port from the left panel dropdown, click ↻ to refresh\n"
            "3. Click \"Start\" to begin DMX transmission\n"
            "4. Drag channel sliders to control fixture brightness (0-255)\n"
            "5. Click \"Stop\" to stop transmission\n\n"
            "── Channel Control ──\n"
            "• Drag slider — real-time value adjustment\n"
            "• Double-click value — type a value directly\n"
            "• Right-click → Rename / Lock / Reset\n"
            "• Locked channels are disabled and skipped in batch ops\n\n"
            "── Group Operations ──\n"
            "• Click channel number to select (blue highlight)\n"
            "• Ctrl+click for multi-select\n"
            "• Drag any selected slider to sync all selected channels\n\n"
            "── Page Switching ──\n"
            "• 4×8 grid buttons for quick page jumps\n"
            "• Current page is highlighted\n\n"
            "── Master Fader ──\n"
            "• Bottom slider scales all channel output (0-100%)\n"
            "• Stored values unchanged, scaling applied in real-time\n\n"
            "── Blackout ──\n"
            "• Click \"Blackout\" to output all zeros instantly\n"
            "• Click again to restore\n"
            "• LED stays lit during blackout\n\n"
            "── Presets (Preset menu) ──\n"
            "• Reset All (Ctrl+R) — all channels to 0\n"
            "• All Max — all channels to 255\n"
            "• Invert All — flip values (0↔255)\n"
            "• Locked channels are unaffected\n\n"
            "── Scene Files (File menu) ──\n"
            "• Ctrl+S Save / Ctrl+Shift+S Save As\n"
            "• Ctrl+O Open / Ctrl+N New\n"
            "• Scene files include values, names, and lock states\n\n"
            "── Scene Library (Ctrl+L) ──\n"
            "• Save/load/delete/rename multiple scenes in-app\n"
            "• Data stored in scenes/scenes.json\n\n"
            "── Scene Chaser (Scene menu) ──\n"
            "• Check scenes from the library to participate\n"
            "• Set dwell time and fade duration\n"
            "• Auto-cycles with linear cross-fade\n\n"
            "── Shortcuts ──\n"
            "Ctrl+N  New Scene\n"
            "Ctrl+O  Open Scene\n"
            "Ctrl+S  Save Scene\n"
            "Ctrl+Shift+S  Save As\n"
            "Ctrl+R  Reset All\n"
            "Ctrl+L  Scene Library\n"
            "F5      Refresh Ports\n"
            "Alt+F4  Exit"
        ),
        "about_title": "About DMX Debug Assistant",
        "about_text": (
            "DMX Debug Assistant v1.0\n\n"
            "A DMX512 lighting control tool built with Python + PyQt5.\n"
            "Outputs DMX512 protocol signals via USB-to-serial adapter.\n\n"
            "Author: Wuuuu"
        ),
    },
}


class _LanguageManager(QObject):
    """Singleton manager for runtime language switching.

    Emits ``language_changed`` whenever the active language changes.
    Language preference is persisted to ``scenes/settings.json``.
    """

    language_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._current = "zh"
        self._settings_loaded = False

    # ---- internal helpers ----

    def _settings_path(self):
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base, "scenes", "settings.json")

    def _load_settings(self):
        path = self._settings_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                saved = data.get("language", "zh")
                if saved in ("zh", "en") and saved != self._current:
                    self._current = saved
            except Exception:
                pass

    def _save_settings(self):
        path = self._settings_path()
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"language": self._current}, f)
        except Exception:
            pass

    # ---- public API ----

    def ensure_loaded(self):
        """Lazy-load saved preference (called before first use)."""
        if not self._settings_loaded:
            self._settings_loaded = True
            self._load_settings()

    def tr(self, key, **kwargs):
        self.ensure_loaded()
        lang_dict = TRANSLATIONS.get(self._current, {})
        text = lang_dict.get(key)
        if text is None:
            text = TRANSLATIONS.get("zh", {}).get(key, key)
        return text.format(**kwargs) if kwargs else text

    def set_language(self, lang):
        self.ensure_loaded()
        if lang in ("zh", "en") and lang != self._current:
            self._current = lang
            self._save_settings()
            self.language_changed.emit()

    @property
    def current_language(self):
        self.ensure_loaded()
        return self._current


_manager = _LanguageManager()


def tr(key, **kwargs):
    """Translate *key* using the active language, optionally formatting
    placeholders from *kwargs*."""
    return _manager.tr(key, **kwargs)


def set_language(lang):
    """Switch to *lang* (``'zh'`` or ``'en'``) and emit
    ``language_changed``."""
    _manager.set_language(lang)


def current_language():
    """Return the active language code (``'zh'`` or ``'en'``)."""
    return _manager.current_language


def get_manager():
    """Return the ``LanguageManager`` singleton (for connecting to
    its ``language_changed`` signal)."""
    return _manager
