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
from ..i18n.translations import tr, set_language, get_manager as _lang_mgr


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

        _lang_mgr().language_changed.connect(self._retranslate_ui)

    # ----------------------------------------------------------------
    # UI setup
    # ----------------------------------------------------------------
    def _init_ui(self):
        self.setWindowTitle(tr("window_title"))
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
        self.page_title_label = QLabel(tr("page_title"))
        self.page_title_label.setAlignment(Qt.AlignCenter)
        self.page_title_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #333; "
            "border: none; padding-bottom: 6px;"
        )
        left_layout.addWidget(self.page_title_label)

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
        self.port_label = QLabel(tr("port_label"))
        self.port_label.setAlignment(Qt.AlignCenter)
        self.port_label.setStyleSheet(
            "font-size: 11px; color: #666; font-weight: bold; border: none;"
        )
        left_layout.addWidget(self.port_label)

        self.combo_port = QComboBox()
        self.combo_port.setMinimumWidth(100)
        self.combo_port.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        self.btn_refresh_port = QPushButton("↻")
        self.btn_refresh_port.setFixedSize(26, 24)
        self.btn_refresh_port.setToolTip(tr("refresh_port_tooltip"))
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
        self.btn_start = QPushButton(tr("btn_start"))
        self.btn_start.setStyleSheet(
            "QPushButton { color: #1a7a1a; font-weight: bold; padding: 6px; }"
        )
        self.btn_stop = QPushButton(tr("btn_stop"))
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { color: #c00; font-weight: bold; padding: 6px; }"
        )
        self.btn_blackout = QPushButton(tr("btn_blackout"))
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

        self.btn_reset = QPushButton(tr("btn_reset"))
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
        self.master_label = QLabel(tr("master_label"))
        self.master_label.setStyleSheet(
            "font-size: 11px; color: #666; font-weight: bold; border: none;"
        )
        self.master_value_label = QLabel("100%")
        self.master_value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.master_value_label.setFixedWidth(36)
        self.master_value_label.setStyleSheet("font-size: 10px; color: #333;")
        master_header.addWidget(self.master_label)
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
        self.status_label = QLabel(tr("status_ready"))
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
        self.menu_file = menubar.addMenu(tr("menu_file"))
        self.act_new_scene = QAction(tr("act_new_scene"), self)
        self.act_new_scene.setShortcut("Ctrl+N")
        self.act_new_scene.triggered.connect(self._new_scene)
        self.menu_file.addAction(self.act_new_scene)

        self.menu_file.addSeparator()

        self.act_open_scene = QAction(tr("act_open_scene"), self)
        self.act_open_scene.setShortcut("Ctrl+O")
        self.act_open_scene.triggered.connect(self._open_scene)
        self.menu_file.addAction(self.act_open_scene)

        self.act_save_scene = QAction(tr("act_save_scene"), self)
        self.act_save_scene.setShortcut("Ctrl+S")
        self.act_save_scene.triggered.connect(self._save_scene)
        self.menu_file.addAction(self.act_save_scene)

        self.act_save_as = QAction(tr("act_save_as"), self)
        self.act_save_as.setShortcut("Ctrl+Shift+S")
        self.act_save_as.triggered.connect(self._save_scene_as)
        self.menu_file.addAction(self.act_save_as)

        self.menu_file.addSeparator()

        self.act_restart = QAction(tr("act_restart"), self)
        self.act_restart.setShortcut("Ctrl+Shift+R")
        self.act_restart.triggered.connect(self._restart_application)
        self.menu_file.addAction(self.act_restart)

        self.menu_file.addSeparator()
        self.act_exit = QAction(tr("act_exit"), self)
        self.act_exit.setShortcut("Alt+F4")
        self.act_exit.triggered.connect(self.close)
        self.menu_file.addAction(self.act_exit)

        # ---- 串口 ----
        self.menu_serial = menubar.addMenu(tr("menu_serial"))
        self.act_refresh_port = QAction(tr("act_refresh_port"), self)
        self.act_refresh_port.setShortcut("F5")
        self.act_refresh_port.triggered.connect(self._refresh_ports)
        self.menu_serial.addAction(self.act_refresh_port)

        self.menu_serial.addSeparator()
        self.act_disconnect = QAction(tr("act_disconnect"), self)
        self.act_disconnect.triggered.connect(self._stop_transmission)
        self.menu_serial.addAction(self.act_disconnect)

        # ---- 预设 ----
        self.menu_preset = menubar.addMenu(tr("menu_preset"))
        self.act_reset_all = QAction(tr("act_reset_all"), self)
        self.act_reset_all.setShortcut("Ctrl+R")
        self.act_reset_all.triggered.connect(self._reset_all_channels)
        self.menu_preset.addAction(self.act_reset_all)

        self.act_set_all_max = QAction(tr("act_set_all_max"), self)
        self.act_set_all_max.triggered.connect(self._set_all_max)
        self.menu_preset.addAction(self.act_set_all_max)

        self.act_invert_all = QAction(tr("act_invert_all"), self)
        self.act_invert_all.triggered.connect(self._invert_all)
        self.menu_preset.addAction(self.act_invert_all)

        # ---- 场景 ----
        self.menu_scene = menubar.addMenu(tr("menu_scene"))
        self.act_scene_library = QAction(tr("act_scene_library"), self)
        self.act_scene_library.setShortcut("Ctrl+L")
        self.act_scene_library.triggered.connect(self._open_scene_library)
        self.menu_scene.addAction(self.act_scene_library)

        self.menu_scene.addSeparator()
        self.act_chaser = QAction(tr("act_chaser"), self)
        self.act_chaser.triggered.connect(self._open_chaser)
        self.menu_scene.addAction(self.act_chaser)

        # ---- 视图 ----
        self.menu_view = menubar.addMenu(tr("menu_view"))
        self.act_show_statusbar = QAction(tr("act_show_statusbar"), self)
        self.act_show_statusbar.setCheckable(True)
        self.act_show_statusbar.setChecked(True)
        self.act_show_statusbar.triggered.connect(
            lambda checked: self.statusBar().setVisible(checked)
        )
        self.menu_view.addAction(self.act_show_statusbar)

        # ---- 语言 ----
        self.menu_language = menubar.addMenu(tr("menu_language"))
        self.act_lang_zh = QAction(tr("lang_chinese"), self)
        self.act_lang_zh.setCheckable(True)
        self.act_lang_zh.setChecked(_lang_mgr().current_language == "zh")
        self.act_lang_zh.setShortcut("Ctrl+Shift+Z")
        self.act_lang_zh.triggered.connect(lambda: set_language("zh"))
        self.menu_language.addAction(self.act_lang_zh)

        self.act_lang_en = QAction(tr("lang_english"), self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setChecked(_lang_mgr().current_language == "en")
        self.act_lang_en.setShortcut("Ctrl+Shift+E")
        self.act_lang_en.triggered.connect(lambda: set_language("en"))
        self.menu_language.addAction(self.act_lang_en)

        # ---- 帮助 ----
        self.menu_help = menubar.addMenu(tr("menu_help"))
        self.act_about_dmx = QAction(tr("act_about_dmx"), self)
        self.act_about_dmx.triggered.connect(self._show_dmx_info)
        self.menu_help.addAction(self.act_about_dmx)

        self.act_usage = QAction(tr("act_usage"), self)
        self.act_usage.triggered.connect(self._show_usage)
        self.menu_help.addAction(self.act_usage)

        self.menu_help.addSeparator()
        self.act_about = QAction(tr("act_about"), self)
        self.act_about.triggered.connect(self._show_about)
        self.menu_help.addAction(self.act_about)

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
            tr("page_label",
               current=self._current_page + 1,
               start=self._current_page * 16 + 1,
               end=(self._current_page + 1) * 16)
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
            tr("rename_channel_title", channel=f"CH{channel + 1:03d}"),
            tr("rename_channel_label"),
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
        self.status_label.setText(tr("status_blackout") if checked else tr("status_stopped"))
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
            self.combo_port.addItem(tr("no_ports_available"), None)

    def _current_port(self):
        return self.combo_port.currentData()

    def _start_transmission(self):
        port = self._current_port()
        if not port:
            QMessageBox.warning(self, tr("serial_error_title"), tr("select_port_first"))
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
            self.status_label.setText(tr("status_sending", port=port))
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
        except serial.SerialException as e:
            QMessageBox.critical(
                self, tr("serial_error_title"),
                tr("cannot_open_port", error=str(e)),
            )
        except OSError as e:
            QMessageBox.critical(
                self, tr("system_error_title"),
                tr("cannot_access_port", error=str(e)),
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
            self.status_label.setText(tr("status_stopped"))
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
            self, tr("confirm_title"), tr("confirm_reset_all"),
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            for i in range(512):
                if i not in self._channel_locks:
                    self.transmitter.update_channel(i, 0)
            self._refresh_all_pages()

    def _set_all_max(self):
        if QMessageBox.question(
            self, tr("confirm_title"), tr("confirm_set_all_max"),
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
            self, tr("confirm_new_scene_title"), tr("confirm_new_scene"),
            QMessageBox.Yes | QMessageBox.No,
        ) == QMessageBox.Yes:
            self._channel_names.clear()
            self._channel_locks.clear()
            self.transmitter.reset_all()
            self._refresh_all_pages()
            self._current_file_path = None
            self.status_label.setText(tr("status_new_scene"))
            self.status_label.setStyleSheet("color: #333;")

    def _open_scene(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr("dialog_open_scene"), "",
            tr("scene_file_filter"),
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            channels = data.get("channels", [])
            if len(channels) != 512:
                QMessageBox.warning(self, tr("format_error_title"), tr("channel_data_incomplete"))
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
            self.status_label.setText(tr("status_loaded", name=os.path.basename(path)))
            self.status_label.setStyleSheet("color: #333;")
        except Exception as e:
            QMessageBox.critical(self, tr("load_failed_title"), str(e))

    def _save_scene(self):
        if self._current_file_path:
            self._save_to_file(self._current_file_path)
        else:
            self._save_scene_as()

    def _save_scene_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, tr("dialog_save_scene"), tr("dialog_default_filename"),
            tr("scene_file_filter"),
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
            self.status_label.setText(tr("status_saved", name=os.path.basename(path)))
            self.status_label.setStyleSheet("color: #333;")
        except Exception as e:
            QMessageBox.critical(self, tr("save_failed_title"), str(e))

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
        self.status_label.setText(tr("status_scene_library_loaded"))
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
            self, tr("dmx_info_title"), tr("dmx_info_text"),
        )

    def _show_usage(self):
        QMessageBox.information(
            self, tr("usage_title"), tr("usage_text"),
        )

    def _show_about(self):
        QMessageBox.about(
            self, tr("about_title"), tr("about_text"),
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
    # Retranslate UI on language switch
    # ----------------------------------------------------------------
    def _retranslate_ui(self):
        self.setWindowTitle(tr("window_title"))

        # Left panel
        self.page_title_label.setText(tr("page_title"))
        self.port_label.setText(tr("port_label"))
        self.btn_refresh_port.setToolTip(tr("refresh_port_tooltip"))
        self.btn_start.setText(tr("btn_start"))
        self.btn_stop.setText(tr("btn_stop"))
        self.btn_blackout.setText(tr("btn_blackout"))
        self.btn_reset.setText(tr("btn_reset"))
        self.master_label.setText(tr("master_label"))
        self.master_value_label.setText(tr("master_value"))

        # Status bar
        if self.transmitter.isRunning():
            self.status_label.setText(tr("status_sending", port=self.combo_port.currentText()))
        elif self.btn_blackout.isChecked():
            self.status_label.setText(tr("status_blackout"))
        else:
            self.status_label.setText(tr("status_ready"))

        # Menus
        self.menu_file.setTitle(tr("menu_file"))
        self.menu_serial.setTitle(tr("menu_serial"))
        self.menu_preset.setTitle(tr("menu_preset"))
        self.menu_scene.setTitle(tr("menu_scene"))
        self.menu_view.setTitle(tr("menu_view"))
        self.menu_language.setTitle(tr("menu_language"))
        self.menu_help.setTitle(tr("menu_help"))

        # Actions
        self.act_new_scene.setText(tr("act_new_scene"))
        self.act_open_scene.setText(tr("act_open_scene"))
        self.act_save_scene.setText(tr("act_save_scene"))
        self.act_save_as.setText(tr("act_save_as"))
        self.act_restart.setText(tr("act_restart"))
        self.act_exit.setText(tr("act_exit"))
        self.act_refresh_port.setText(tr("act_refresh_port"))
        self.act_disconnect.setText(tr("act_disconnect"))
        self.act_reset_all.setText(tr("act_reset_all"))
        self.act_set_all_max.setText(tr("act_set_all_max"))
        self.act_invert_all.setText(tr("act_invert_all"))
        self.act_scene_library.setText(tr("act_scene_library"))
        self.act_chaser.setText(tr("act_chaser"))
        self.act_show_statusbar.setText(tr("act_show_statusbar"))
        self.act_about_dmx.setText(tr("act_about_dmx"))
        self.act_usage.setText(tr("act_usage"))
        self.act_about.setText(tr("act_about"))
        self.act_lang_zh.setText(tr("lang_chinese"))
        self.act_lang_en.setText(tr("lang_english"))

        # Language menu check state
        is_zh = _lang_mgr().current_language == "zh"
        self.act_lang_zh.setChecked(is_zh)
        self.act_lang_en.setChecked(not is_zh)

        # Page display
        self._update_page_display()

        # Port combo placeholder
        if self.combo_port.count() == 1 and self.combo_port.itemData(0) is None:
            self.combo_port.setItemText(0, tr("no_ports_available"))

    # ----------------------------------------------------------------
    # Restart
    # ----------------------------------------------------------------
    def _restart_application(self):
        reply = QMessageBox.question(
            self, tr("confirm_restart_title"), tr("confirm_restart"),
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
