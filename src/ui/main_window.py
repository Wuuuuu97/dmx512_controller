import json
import os
import sys

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QStackedWidget, QPushButton, QLabel, QComboBox, QSlider,
    QMessageBox, QFileDialog, QAction, QInputDialog,
)
from PyQt5.QtCore import Qt, QRect, QProcess
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QIcon

import serial
import serial.tools.list_ports

from .page_widget import PageWidget
from .scene_library import SceneLibraryDialog
from .chaser_panel import ChaserDialog
from ..dmx.transmitter import DMXTransmitter


class MainWindow(QMainWindow):
    """Main application window for DMX512 Controller.

    Layout:
      ┌──────┬──────────────────────────────────────┐
      │ 页数  │  第 1 / 32 页                         │
      │ ───── │ ┌────┐ ┌────┐ ┌────┐ ┌────┐         │
      │ 01 02 │ │CH01│ │CH02│ │CH03│ │CH04│         │
      │ 03 04 │ │ ═╬═ │ │ ═╬═ │ │ ═╬═ │ │ ═╬═ │         │
      │ ...   │ └────┘ └────┘ └────┘ └────┘         │
      │ 31 32 │ ...                                  │
      │ ───── │                                      │
      │ 串口  │                                      │
      │ [COM▼]│                                      │
      │ ───── │                                      │
      │▶ Start│                                      │
      │■ Stop │                                      │
      │ 黑场  │                                      │
      │全部归零│                                      │
      │ ───── │                                      │
      │ 主控  │                                      │
      │[══o══]│                                      │
      ├──────┴──────────────────────────────────────┤
      │ ● 状态栏                                     │
      └─────────────────────────────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.serial_port = None
        self.transmitter = DMXTransmitter()
        self.transmitter.status_changed.connect(self._on_transmitter_status)
        self._current_page = 0
        self._current_file_path = None

        # Extended state
        self._channel_names = {}   # {index: custom_name}
        self._channel_locks = set()  # set of locked indices

        self._init_ui()
        self._connect_per_widget_signals()
        self._connect_signals()
        self._update_page_display()

    # ----------------------------------------------------------------
    # UI setup
    # ----------------------------------------------------------------
    def _init_ui(self):
        self.setWindowTitle("DMX 调试助手")
        self.setMinimumSize(860, 520)
        self.setWindowIcon(self._make_icon())

        central = QWidget()
        self.setCentralWidget(central)
        h_layout = QHBoxLayout(central)
        h_layout.setSpacing(0)
        h_layout.setContentsMargins(0, 0, 0, 0)

        self._create_menu_bar()

        # ========== Left panel ==========
        left_panel = QWidget()
        left_panel.setObjectName("pagePanel")
        left_panel.setFixedWidth(180)
        left_panel.setStyleSheet("""
            #pagePanel {
                background-color: #f0f2f5;
                border-right: 1px solid #d0d0d0;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(4, 6, 4, 6)
        left_layout.setSpacing(2)

        # Title
        title = QLabel("页数")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #333; "
            "border: none; padding-bottom: 6px;"
        )
        left_layout.addWidget(title)

        # 32 page buttons in 4×8 grid
        page_grid = QGridLayout()
        page_grid.setSpacing(2)
        self.page_buttons = []
        for i in range(32):
            btn = QPushButton(f"{i + 1:02d}")
            btn.setCheckable(True)
            btn.setFixedSize(34, 24)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px; border: 1px solid #ccc;
                    background-color: #fff; border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #e3f0fd; border-color: #0078d4;
                }
                QPushButton:checked {
                    background-color: #0078d4; color: white;
                    font-weight: bold; border-color: #005a9e;
                }
            """)
            btn.clicked.connect(lambda checked, p=i: self._go_to_page(p))
            self.page_buttons.append(btn)
            page_grid.addWidget(btn, i // 4, i % 4)

        left_layout.addLayout(page_grid)
        left_layout.addSpacing(8)

        # Separator
        sep = QLabel()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background: #d0d0d0; border: none;")
        left_layout.addWidget(sep)
        left_layout.addSpacing(4)

        # Port selection
        port_label = QLabel("串口")
        port_label.setAlignment(Qt.AlignCenter)
        port_label.setStyleSheet(
            "font-size: 11px; color: #666; font-weight: bold; border: none;"
        )
        left_layout.addWidget(port_label)

        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(100)
        self.combo_port.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        self.btn_refresh_port = QPushButton("↻")
        self.btn_refresh_port.setFixedSize(26, 24)
        self.btn_refresh_port.setToolTip("刷新串口列表")
        self.btn_refresh_port.setStyleSheet("font-size: 13px;")

        port_row = QHBoxLayout()
        port_row.setSpacing(2)
        port_row.addWidget(self.combo_port, 1)
        port_row.addWidget(self.btn_refresh_port)
        left_layout.addLayout(port_row)

        self._refresh_ports()

        # Separator
        sep2 = QLabel()
        sep2.setFixedHeight(1)
        sep2.setStyleSheet("background: #d0d0d0; border: none;")
        left_layout.addWidget(sep2)
        left_layout.addSpacing(4)

        # ---- Control buttons ----
        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setStyleSheet(
            "QPushButton { color: #1a7a1a; font-weight: bold; padding: 6px; }"
        )
        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { color: #c00; font-weight: bold; padding: 6px; }"
        )
        self.btn_blackout = QPushButton("黑场")
        self.btn_blackout.setCheckable(True)
        self.btn_blackout.setStyleSheet("""
            QPushButton {
                font-weight: bold; padding: 6px;
                background-color: #444; color: #ccc;
                border: 1px solid #666; border-radius: 3px;
            }
            QPushButton:checked {
                background-color: #cc0000; color: white;
                border-color: #990000;
            }
        """)

        self.btn_reset = QPushButton("全部归零")
        self.btn_reset.setStyleSheet("QPushButton { padding: 6px; }")

        left_layout.addWidget(self.btn_start)
        left_layout.addWidget(self.btn_stop)
        left_layout.addSpacing(2)
        left_layout.addWidget(self.btn_blackout)
        left_layout.addSpacing(4)
        left_layout.addWidget(self.btn_reset)

        # ---- Master fader ----
        left_layout.addSpacing(6)
        sep3 = QLabel()
        sep3.setFixedHeight(1)
        sep3.setStyleSheet("background: #d0d0d0; border: none;")
        left_layout.addWidget(sep3)
        left_layout.addSpacing(2)

        master_header = QHBoxLayout()
        master_label = QLabel("主控")
        master_label.setStyleSheet(
            "font-size: 11px; color: #666; font-weight: bold; border: none;"
        )
        self.master_value_label = QLabel("100%")
        self.master_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.master_value_label.setFixedWidth(36)
        self.master_value_label.setStyleSheet("font-size: 10px; color: #333;")
        master_header.addWidget(master_label)
        master_header.addStretch()
        master_header.addWidget(self.master_value_label)
        left_layout.addLayout(master_header)

        self.master_slider = QSlider(Qt.Horizontal)
        self.master_slider.setRange(0, 100)
        self.master_slider.setValue(100)
        self.master_slider.setTickPosition(QSlider.NoTicks)
        self.master_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 6px;
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::sub-page:horizontal {
                background: #007aff;
                border-radius: 3px;
            }
            QSlider::add-page:horizontal {
                background: #ddd;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                width: 16px; height: 16px;
                margin: -5px 0;
                background: white;
                border: 1px solid #aaa;
                border-radius: 8px;
            }
        """)
        left_layout.addWidget(self.master_slider)

        left_layout.addStretch()

        # ========== Right area ==========
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(3)
        right_layout.setContentsMargins(6, 4, 4, 4)

        # Page title bar
        self.page_label = QLabel()
        self.page_label.setFont(QFont("", 13, QFont.Bold))
        self.page_label.setStyleSheet("color: #333; margin-bottom: 2px;")
        right_layout.addWidget(self.page_label)

        # Page stack (32 pages of 16 channels)
        self.stack = QStackedWidget()
        self.pages = []
        for p in range(32):
            page = PageWidget(p)
            page.channel_changed.connect(self._on_channel_changed)
            self.pages.append(page)
            self.stack.addWidget(page)

        right_layout.addWidget(self.stack, 1)

        # Status bar
        status = self.statusBar()
        self.led = QLabel()
        self.led.setFixedSize(12, 12)
        status.addWidget(self.led)
        spacer = QLabel("  ")
        status.addWidget(spacer)
        self.status_label = QLabel("就绪 — 未连接")
        self.status_label.setStyleSheet("color: #888;")
        status.addWidget(self.status_label, 1)
        self.fps_label = QLabel("")
        status.addPermanentWidget(self.fps_label)
        self._set_led(False)

        # Assemble
        h_layout.addWidget(left_panel)
        h_layout.addWidget(right_panel, 1)

    # ----------------------------------------------------------------
    # Menu bar
    # ----------------------------------------------------------------
    def _create_menu_bar(self):
        menubar = self.menuBar()

        # ---- 文件 ----
        menu_file = menubar.addMenu("文件(&F)")
        act_new = QAction("新建场景(&N)", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._new_scene)
        menu_file.addAction(act_new)

        menu_file.addSeparator()

        act_open = QAction("打开场景(&O)...", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self._open_scene)
        menu_file.addAction(act_open)

        act_save = QAction("保存场景(&S)", self)
        act_save.setShortcut("Ctrl+S")
        act_save.triggered.connect(self._save_scene)
        menu_file.addAction(act_save)

        act_save_as = QAction("另存为(&A)...", self)
        act_save_as.setShortcut("Ctrl+Shift+S")
        act_save_as.triggered.connect(self._save_scene_as)
        menu_file.addAction(act_save_as)

        menu_file.addSeparator()

        act_restart = QAction("重启软件(&R)", self)
        act_restart.setShortcut("Ctrl+Shift+R")
        act_restart.triggered.connect(self._restart_application)
        menu_file.addAction(act_restart)

        menu_file.addSeparator()
        act_exit = QAction("退出(&X)", self)
        act_exit.setShortcut("Alt+F4")
        act_exit.triggered.connect(self.close)
        menu_file.addAction(act_exit)

        # ---- 串口 ----
        menu_serial = menubar.addMenu("串口(&S)")
        act_refresh = QAction("刷新端口(&R)", self)
        act_refresh.setShortcut("F5")
        act_refresh.triggered.connect(self._refresh_ports)
        menu_serial.addAction(act_refresh)

        menu_serial.addSeparator()
        act_disconnect = QAction("断开连接(&D)", self)
        act_disconnect.triggered.connect(self._stop_transmission)
        menu_serial.addAction(act_disconnect)

        # ---- 预设 ----
        menu_preset = menubar.addMenu("预设(&P)")
        act_reset = QAction("全部归零", self)
        act_reset.setShortcut("Ctrl+R")
        act_reset.triggered.connect(self._reset_all_channels)
        menu_preset.addAction(act_reset)

        act_max = QAction("全部最大 (255)", self)
        act_max.triggered.connect(self._set_all_max)
        menu_preset.addAction(act_max)

        act_invert = QAction("全部取反", self)
        act_invert.triggered.connect(self._invert_all)
        menu_preset.addAction(act_invert)

        # ---- 场景 ----
        menu_scene = menubar.addMenu("场景(&C)")
        act_library = QAction("场景库(&L)", self)
        act_library.setShortcut("Ctrl+L")
        act_library.triggered.connect(self._open_scene_library)
        menu_scene.addAction(act_library)

        menu_scene.addSeparator()
        act_chaser = QAction("场景轮巡(&H)", self)
        act_chaser.triggered.connect(self._open_chaser)
        menu_scene.addAction(act_chaser)

        # ---- 视图 ----
        menu_view = menubar.addMenu("视图(&V)")
        self.act_show_status = QAction("显示状态栏", self)
        self.act_show_status.setCheckable(True)
        self.act_show_status.setChecked(True)
        self.act_show_status.triggered.connect(
            lambda checked: self.statusBar().setVisible(checked)
        )
        menu_view.addAction(self.act_show_status)

        # ---- 帮助 ----
        menu_help = menubar.addMenu("帮助(&H)")
        act_dmx_info = QAction("关于 DMX512", self)
        act_dmx_info.triggered.connect(self._show_dmx_info)
        menu_help.addAction(act_dmx_info)

        act_usage = QAction("使用说明", self)
        act_usage.triggered.connect(self._show_usage)
        menu_help.addAction(act_usage)

        menu_help.addSeparator()
        act_about = QAction("关于(&A)", self)
        act_about.triggered.connect(self._show_about)
        menu_help.addAction(act_about)

    # ----------------------------------------------------------------
    # Signal wiring
    # ----------------------------------------------------------------
    def _connect_signals(self):
        self.btn_start.clicked.connect(self._start_transmission)
        self.btn_stop.clicked.connect(self._stop_transmission)
        self.btn_blackout.clicked.connect(self._on_blackout_toggled)
        self.btn_reset.clicked.connect(self._reset_all_channels)
        self.btn_refresh_port.clicked.connect(self._refresh_ports)
        self.master_slider.valueChanged.connect(self._on_master_changed)

        # Channel widget signals (connected per-page in _init_ui)
        # Additional per-widget signals connected in _refresh_all_pages setup

    # ----------------------------------------------------------------
    # Page navigation
    # ----------------------------------------------------------------
    def _go_to_page(self, page):
        self._current_page = page
        self._update_page_display()
        self._refresh_current_page()

    def _update_page_display(self):
        self.stack.setCurrentIndex(self._current_page)
        self.page_label.setText(
            f"第 {self._current_page + 1} / 32 页    "
            f"(通道 {self._current_page * 16 + 1}–{(self._current_page + 1) * 16})"
        )
        for i, btn in enumerate(self.page_buttons):
            btn.setChecked(i == self._current_page)

    def _on_channel_changed(self, channel, value):
        self.transmitter.update_channel(channel, value)

    def _refresh_current_page(self):
        """Refresh current page widgets from transmitter data + names + locks."""
        page = self.pages[self._current_page]
        page.set_values(self.transmitter.dmx_data)
        for w in page.channel_widgets:
            idx = w.channel_index
            name = self._channel_names.get(idx)
            if name:
                w.set_custom_name(name)
            w.set_locked(idx in self._channel_locks)

    # ----------------------------------------------------------------
    # Channel rename & lock (wired per-widget via connect_per_widget_signals)
    # ----------------------------------------------------------------
    def _connect_per_widget_signals(self):
        """Connect per-channel signals (rename, lock, selection).

        Called once during init after all pages are created.
        """
        for page in self.pages:
            for w in page.channel_widgets:
                w.rename_requested.connect(self._on_channel_rename)
                w.lock_changed.connect(self._on_channel_lock)

    def _on_channel_rename(self, channel):
        current = self._channel_names.get(channel, "")
        name, ok = QInputDialog.getText(
            self,
            f"重命名通道 CH{channel + 1:03d}",
            "输入通道名称 (留空恢复默认):",
            text=current,
        )
        if not ok:
            return
        if name.strip():
            self._channel_names[channel] = name.strip()
        else:
            self._channel_names.pop(channel, None)
        # Update widget display
        page_idx = channel // 16
        local = channel % 16
        self.pages[page_idx].channel_widgets[local].set_custom_name(
            self._channel_names.get(channel)
        )

    def _on_channel_lock(self, channel, locked):
        if locked:
            self._channel_locks.add(channel)
        else:
            self._channel_locks.discard(channel)

    # ----------------------------------------------------------------
    # Master fader & blackout
    # ----------------------------------------------------------------
    def _on_master_changed(self, value):
        self.master_value_label.setText(f"{value}%")
        self.transmitter.set_master_level(value)

    def _on_blackout_toggled(self, checked):
        self.transmitter.set_blackout(checked)
        self.status_label.setText("黑场" if checked else "已停止")
        self.status_label.setStyleSheet(
            "color: red; font-weight: bold;" if checked else "color: #888;"
        )

    # ----------------------------------------------------------------
    # DMX transmission
    # ----------------------------------------------------------------
    def _set_controls_enabled(self, enabled):
        """Enable/disable all controls during transmission."""
        is_sending = not enabled
        self.btn_start.setEnabled(not is_sending)
        self.btn_stop.setEnabled(is_sending)
        self.combo_port.setEnabled(not is_sending)
        self.btn_refresh_port.setEnabled(not is_sending)

    def _set_led(self, is_green):
        color = "#44cc44" if is_green else "#ff4444"
        border = "#228b22" if is_green else "#cc0000"
        self.led.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
            border: 1px solid {border};
        """)

    def _refresh_ports(self):
        self.combo_port.clear()
        ports = serial.tools.list_ports.comports()
        if ports:
            for p in sorted(ports):
                self.combo_port.addItem(f"{p.device} - {p.description}", p.device)
        else:
            self.combo_port.addItem("无可用串口", None)

    def _current_port(self):
        return self.combo_port.currentData()

    def _start_transmission(self):
        port = self._current_port()
        if not port:
            QMessageBox.warning(self, "串口错误", "请先选择串口")
            return

        # Deactivate blackout when starting fresh
        if self.btn_blackout.isChecked():
            self.btn_blackout.setChecked(False)
            self.transmitter.set_blackout(False)

        try:
            self.serial_port = serial.Serial(
                port=port,
                baudrate=250000,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=0.05,
                write_timeout=0.5,
            )
            self.transmitter.set_serial(self.serial_port)
            self.transmitter.start()
            self._set_controls_enabled(False)
            self._set_led(True)
            self.status_label.setText(f"发送中 — {port}")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        except serial.SerialException as e:
            QMessageBox.critical(
                self, "串口错误",
                f"无法打开串口:\n{e}\n\n"
                "可能的原因:\n"
                "• 串口已被其他程序占用\n"
                "• 设备未连接或驱动未安装\n"
                "• 权限不足",
            )
        except OSError as e:
            QMessageBox.critical(
                self, "系统错误",
                f"无法访问串口:\n{e}\n\n"
                "请检查设备连接后重试。",
            )

    def _stop_transmission(self):
        self.transmitter.stop()
        if self.serial_port:
            try:
                if self.serial_port.is_open:
                    self.serial_port.close()
            except Exception:
                pass
        self._set_controls_enabled(True)
        self._set_led(False)
        if not self.btn_blackout.isChecked():
            self.status_label.setText("已停止")
            self.status_label.setStyleSheet("color: #888;")
        self.fps_label.setText("")

    def _on_transmitter_status(self, ok, message):
        if not ok:
            self._stop_transmission()
            self.status_label.setText(message)
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    # ----------------------------------------------------------------
    # Presets (skip locked channels)
    # ----------------------------------------------------------------
    def _reset_all_channels(self):
        if QMessageBox.question(
            self, "确认", "确定将所有通道归零吗？\n(锁定通道不受影响)",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            for i in range(512):
                if i not in self._channel_locks:
                    self.transmitter.update_channel(i, 0)
            self._refresh_all_pages()

    def _set_all_max(self):
        if QMessageBox.question(
            self, "确认", "确定将所有通道设为 255 吗？\n(锁定通道不受影响)",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            for i in range(512):
                if i not in self._channel_locks:
                    self.transmitter.update_channel(i, 255)
            self._refresh_all_pages()

    def _invert_all(self):
        for i in range(512):
            if i not in self._channel_locks:
                val = 255 - self.transmitter.get_channel(i)
                self.transmitter.update_channel(i, val)
        self._refresh_all_pages()

    def _refresh_all_pages(self):
        """Refresh all page widgets — values, names, locks."""
        for page in self.pages:
            for w in page.channel_widgets:
                idx = w.channel_index
                w.set_value(self.transmitter.dmx_data[idx], block_signals=True)
                name = self._channel_names.get(idx)
                if name:
                    w.set_custom_name(name)
                w.set_locked(idx in self._channel_locks)

    # ----------------------------------------------------------------
    # Scene file I/O
    # ----------------------------------------------------------------
    def _new_scene(self):
        if QMessageBox.question(
            self, "新建场景",
            "确定要新建场景吗？\n当前所有通道数据将被清除。",
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._channel_names.clear()
            self._channel_locks.clear()
            self.transmitter.reset_all()
            self._refresh_all_pages()
            self._current_file_path = None
            self.status_label.setText("已新建场景")
            self.status_label.setStyleSheet("color: #333;")

    def _open_scene(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开场景", "",
            "DMX Scene (*.dmx *.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            channels = data.get("channels", [])
            if len(channels) != 512:
                QMessageBox.warning(self, "格式错误", "通道数据不完整 (需要 512 个值)")
                return
            self.transmitter.set_all_channels(channels)
            # Restore names
            self._channel_names = {}
            for k, v in data.get("names", {}).items():
                self._channel_names[int(k)] = v
            # Restore locks
            self._channel_locks = set(data.get("locked", []))
            self._refresh_all_pages()
            self._current_file_path = path
            self.status_label.setText(f"已加载: {os.path.basename(path)}")
            self.status_label.setStyleSheet("color: #333;")
        except Exception as e:
            QMessageBox.critical(self, "加载失败", str(e))

    def _save_scene(self):
        if self._current_file_path:
            self._save_to_file(self._current_file_path)
        else:
            self._save_scene_as()

    def _save_scene_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存场景", "untitled.dmx",
            "DMX Scene (*.dmx *.json);;All Files (*)",
        )
        if path:
            self._save_to_file(path)

    def _save_to_file(self, path):
        data = {
            "name": os.path.splitext(os.path.basename(path))[0],
            "channels": list(self.transmitter.dmx_data),
            "count": 512,
            "names": {str(k): v for k, v in self._channel_names.items()},
            "locked": sorted(self._channel_locks),
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._current_file_path = path
            self.status_label.setText(f"已保存: {os.path.basename(path)}")
            self.status_label.setStyleSheet("color: #333;")
        except Exception as e:
            QMessageBox.critical(self, "保存失败", str(e))

    # ----------------------------------------------------------------
    # Scene library
    # ----------------------------------------------------------------
    def _open_scene_library(self):
        dlg = SceneLibraryDialog(
            get_channels_fn=lambda: list(self.transmitter.dmx_data),
            get_names_fn=lambda: dict(self._channel_names),
            get_locks_fn=lambda: sorted(self._channel_locks),
            parent=self,
        )
        dlg.scene_loaded.connect(self._on_scene_loaded)
        dlg.exec_()

    def _on_scene_loaded(self, channels, names, locked):
        """Load scene from the library dialog."""
        self.transmitter.set_all_channels(channels)
        self._channel_names = {}
        for k, v in names.items():
            self._channel_names[int(k)] = v
        self._channel_locks = set(locked)
        self._refresh_all_pages()
        self._current_file_path = None
        self.status_label.setText("已加载场景库场景")
        self.status_label.setStyleSheet("color: #333;")

    # ----------------------------------------------------------------
    # Chaser
    # ----------------------------------------------------------------
    def _open_chaser(self):
        # Collect current library scenes for the chaser to use
        scenes_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "scenes",
        )
        scenes_file = os.path.join(scenes_dir, "scenes.json")
        library_scenes = []
        if os.path.exists(scenes_file):
            try:
                with open(scenes_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                library_scenes = data.get("scenes", [])
            except Exception:
                pass

        dlg = ChaserDialog(library_scenes, parent=self)
        dlg.chaser_values.connect(self._on_chaser_values)

        # Stop DMX transmission while chaser runs (chaser owns the output)
        was_transmitting = self.serial_port is not None and self.transmitter.isRunning()
        if was_transmitting:
            self._stop_transmission()

        dlg.exec_()

        # Restart transmission after chaser stops
        if was_transmitting:
            # Update the UI with final chaser values
            self._refresh_all_pages()

    def _on_chaser_values(self, values):
        """Receive intermediate chaser values and push to transmitter + UI."""
        self.transmitter.set_all_channels(values)
        self._refresh_current_page()

    # ----------------------------------------------------------------
    # Help dialogs
    # ----------------------------------------------------------------
    def _show_dmx_info(self):
        QMessageBox.information(
            self, "关于 DMX512",
            "DMX512 是数字多路复用协议，用于舞台灯光控制。\n\n"
            "• 512 个通道，每通道 0-255\n"
            "• 波特率: 250,000 bps\n"
            "• 8 数据位, 2 停止位, 无校验\n"
            "• 帧率: ~36 Hz\n"
            "• 物理层: RS-485",
        )

    def _show_usage(self):
        QMessageBox.information(
            self, "使用说明",
            "── 基本操作 ──\n"
            "1. 连接 USB 转 RS-485 模块到电脑\n"
            "2. 在左侧「串口」下拉选择端口，点击 ↻ 刷新\n"
            "3. 点击「Start」开始发送 DMX 信号\n"
            "4. 点击「Stop」停止发送\n\n"
            "── 通道控制 ──\n"
            "• 拖动滑块 (0-255) 调节通道值\n"
            "• 双击数值弹出输入框，直接键入\n"
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
            "Alt+F4  退出程序",
        )

    def _show_about(self):
        QMessageBox.about(
            self, "关于 DMX 调试助手",
            "DMX 调试助手 v1.0\n\n"
            "基于 Python + PyQt5 的 DMX512 灯光控制工具。\n"
            "通过 USB 转串口模块输出 DMX512 协议信号。\n\n"
            "作者: Wuuuu",
        )

    # ----------------------------------------------------------------
    # App icon
    # ----------------------------------------------------------------
    @staticmethod
    def _make_icon():
        p = QPixmap(64, 64)
        p.fill(Qt.transparent)
        q = QPainter(p)
        q.setRenderHint(QPainter.Antialiasing)
        # Outer glow
        q.setBrush(QColor("#007aff"))
        q.setPen(Qt.NoPen)
        q.drawEllipse(2, 2, 60, 60)
        # Inner highlight
        q.setBrush(QColor("#4da6ff"))
        q.drawEllipse(6, 6, 52, 52)
        # Center core
        q.setBrush(QColor("#007aff"))
        q.drawEllipse(10, 10, 44, 44)
        # Text
        q.setPen(QColor("#ffffff"))
        f = QFont("Arial", 16, QFont.Bold)
        q.setFont(f)
        q.drawText(QRect(0, 0, 64, 64), Qt.AlignCenter, "DMX")
        q.end()
        return QIcon(p)

    # ----------------------------------------------------------------
    # Restart
    # ----------------------------------------------------------------
    def _restart_application(self):
        reply = QMessageBox.question(
            self, "确认重启",
            "确定要重启软件吗？\n未保存的场景数据将丢失。",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._stop_transmission()
        # Flush pending events so resources are fully released
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        if getattr(sys, "frozen", False):
            args = [sys.executable]
        else:
            root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            args = [sys.executable, os.path.join(root, "main.py")]

        QProcess.startDetached(args[0], args[1:])
        self.close()

    # ----------------------------------------------------------------
    # Window lifecycle
    # ----------------------------------------------------------------
    def closeEvent(self, event):
        self._stop_transmission()
        event.accept()
