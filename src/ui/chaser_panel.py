from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QSpinBox, QMessageBox, QListWidgetItem,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from ..engine.chaser import ChaserEngine


class ChaserDialog(QDialog):
    """Scene chaser control panel.

    Allows selecting scenes from the library, setting timing,
    and starting/stopping the chase sequence.
    """

    chaser_values = pyqtSignal(list)   # 512 ints for UI + transmitter update

    def __init__(self, scene_library_scenes, parent=None):
        """scene_library_scenes: list of {"name": str, "channels": list[512]}"""
        super().__init__(parent)
        self.setWindowTitle("场景轮巡")
        self.setMinimumSize(380, 460)
        self._all_scenes = list(scene_library_scenes)
        self._engine = ChaserEngine(self)
        self._engine.values_updated.connect(self._on_engine_values)
        self._engine.finished.connect(self._on_engine_finished)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("场景轮巡")
        title.setFont(QFont("", 13, QFont.Bold))
        layout.addWidget(title)

        help_text = QLabel("勾选参与轮巡的场景，设置时间后点击 ▶ 开始")
        help_text.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(help_text)

        # Scene checklist
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        for s in self._all_scenes:
            item = QListWidgetItem(s["name"])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

        layout.addWidget(self.list_widget, 1)

        # Timing controls
        timing_layout = QHBoxLayout()
        timing_layout.addWidget(QLabel("停留时间:"))
        self.spin_interval = QSpinBox()
        self.spin_interval.setRange(500, 60000)
        self.spin_interval.setValue(3000)
        self.spin_interval.setSuffix(" ms")
        self.spin_interval.setSingleStep(500)
        timing_layout.addWidget(self.spin_interval)

        timing_layout.addSpacing(12)
        timing_layout.addWidget(QLabel("淡入:"))
        self.spin_fade = QSpinBox()
        self.spin_fade.setRange(0, 10000)
        self.spin_fade.setValue(500)
        self.spin_fade.setSuffix(" ms")
        self.spin_fade.setSingleStep(100)
        timing_layout.addWidget(self.spin_fade)

        layout.addLayout(timing_layout)

        # Control buttons
        btn_row = QHBoxLayout()
        self.btn_start = QPushButton("▶ 开始")
        self.btn_start.setStyleSheet(
            "QPushButton { color: #1a7a1a; font-weight: bold; }"
        )
        self.btn_start.clicked.connect(self._start_chaser)

        self.btn_stop = QPushButton("■ 停止")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { color: #c00; font-weight: bold; }"
        )
        self.btn_stop.clicked.connect(self._stop_chaser)

        btn_row.addWidget(self.btn_start)
        btn_row.addWidget(self.btn_stop)
        layout.addLayout(btn_row)

        # Status
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self.status_label)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _get_selected_scenes(self):
        """Return list of checked scenes from the list."""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item.checkState() == Qt.Checked and i < len(self._all_scenes):
                selected.append(self._all_scenes[i])
        return selected

    def _start_chaser(self):
        scenes = self._get_selected_scenes()
        if not scenes:
            QMessageBox.information(self, "提示", "请至少勾选一个场景")
            return

        self._engine.set_scenes(scenes)
        self._engine.interval_ms = self.spin_interval.value()
        self._engine.fade_ms = self.spin_fade.value()
        self._engine.loop = True
        self._engine.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.list_widget.setEnabled(False)
        self.spin_interval.setEnabled(False)
        self.spin_fade.setEnabled(False)
        self.status_label.setText("轮巡中...")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")

    def _stop_chaser(self):
        self._engine.stop()
        self._engine.wait(2000)

    def _on_engine_values(self, values):
        self.chaser_values.emit(values)

    def _on_engine_finished(self):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.list_widget.setEnabled(True)
        self.spin_interval.setEnabled(True)
        self.spin_fade.setEnabled(True)
        self.status_label.setText("已停止")
        self.status_label.setStyleSheet("color: #888;")

    def closeEvent(self, event):
        self._engine.stop()
        self._engine.wait(2000)
        event.accept()
