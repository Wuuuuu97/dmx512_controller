from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal


class SerialPanel(QWidget):
    """DMX start/stop/reset controls (port selection is in the left panel)."""

    start_requested = pyqtSignal()
    stop_requested = pyqtSignal()
    reset_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        self.btn_start = QPushButton("▶ Start")
        self.btn_start.setStyleSheet(
            "QPushButton { color: #1a7a1a; font-weight: bold; }"
        )

        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet(
            "QPushButton { color: #c00; font-weight: bold; }"
        )

        self.btn_reset = QPushButton("全部归零")

        layout.addWidget(self.btn_start)
        layout.addWidget(self.btn_stop)
        layout.addSpacing(20)
        layout.addWidget(self.btn_reset)
        layout.addStretch()

        self.setLayout(layout)

        self.btn_start.clicked.connect(self.start_requested)
        self.btn_stop.clicked.connect(self.stop_requested)
        self.btn_reset.clicked.connect(self.reset_requested)

    def set_sending_state(self, is_sending):
        self.btn_start.setEnabled(not is_sending)
        self.btn_stop.setEnabled(is_sending)
