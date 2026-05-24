from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSlider, QLabel, QInputDialog,
    QMenu, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QCursor

from ..i18n.translations import tr


class ChannelWidget(QWidget):
    """Single DMX channel control: label + slider + value + double-click input.

    Supports:
      - Selection (click label) for group operations
      - Lock state with visual feedback
      - Custom channel naming
      - Right-click context menu (rename / lock / reset)
    """

    value_changed = pyqtSignal(int, int)   # channel_index, value
    selection_toggled = pyqtSignal(int)    # channel_index
    lock_changed = pyqtSignal(int, bool)   # channel_index, locked
    rename_requested = pyqtSignal(int)     # channel_index

    def __init__(self, channel_index, parent=None):
        super().__init__(parent)
        self.channel_index = channel_index
        self._selected = False
        self._locked = False
        self._custom_name = None
        self._init_ui()
        self._apply_style()
        self.label_ch.installEventFilter(self)

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(1)
        layout.setContentsMargins(2, 2, 2, 2)

        # Channel number (top, centered) — clickable for selection
        self.label_ch = QLabel(f"CH{self.channel_index + 1:03d}")
        self.label_ch.setAlignment(Qt.AlignCenter)
        self.label_ch.setObjectName("channelLabel")
        self.label_ch.setCursor(Qt.PointingHandCursor)
        ch_font = QFont()
        ch_font.setBold(True)
        ch_font.setPointSize(10)
        self.label_ch.setFont(ch_font)

        # Slider wrapper — centres the slider horizontally
        slider_row = QHBoxLayout()
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.addStretch()

        self.slider = QSlider(Qt.Vertical)
        self.slider.setRange(0, 255)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.NoTicks)
        self.slider.valueChanged.connect(self._on_value_changed)

        slider_row.addWidget(self.slider)
        slider_row.addStretch()

        # Current value (bottom, centered)
        self.label_value = QLabel("0")
        self.label_value.setAlignment(Qt.AlignCenter)
        self.label_value.setObjectName("valueLabel")
        val_font = QFont()
        val_font.setBold(True)
        val_font.setPointSize(11)
        self.label_value.setFont(val_font)

        layout.addWidget(self.label_ch)
        layout.addSpacing(8)
        layout.addLayout(slider_row, 3)
        layout.addWidget(self.label_value)
        layout.addStretch(1)
        self.setLayout(layout)

    # ----------------------------------------------------------------
    # Event handling
    # ----------------------------------------------------------------
    def eventFilter(self, obj, event):
        if obj is self.label_ch and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                self.selection_toggled.emit(self.channel_index)
                return True
        return super().eventFilter(obj, event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        act_rename = menu.addAction(tr("context_rename"))
        menu.addSeparator()
        act_lock = menu.addAction(tr("context_unlock") if self._locked else tr("context_lock"))
        act_reset = menu.addAction(tr("context_reset"))
        menu.addSeparator()
        # Show current name in context for confirmation
        current = self._custom_name or f"CH{self.channel_index + 1:03d}"
        act_info = menu.addAction(tr("context_channel_info", name=current))
        act_info.setEnabled(False)

        action = menu.exec_(QCursor.pos())
        if action == act_rename:
            self.rename_requested.emit(self.channel_index)
        elif action == act_lock:
            self._locked = not self._locked
            self._update_lock_style()
            self.lock_changed.emit(self.channel_index, self._locked)
        elif action == act_reset:
            self.set_value(0, block_signals=False)
            self.value_changed.emit(self.channel_index, 0)

    # ----------------------------------------------------------------
    # Style
    # ----------------------------------------------------------------
    def _apply_style(self):
        """Physical fader style — white knob with horizontal grip lines."""
        self.slider.setStyleSheet("""
            QSlider::groove:vertical {
                width: 28px;
                background: #dedede;
                border-radius: 14px;
            }
            QSlider::sub-page:vertical {
                background: #dedede;
                border-radius: 14px;
            }
            QSlider::add-page:vertical {
                background: #007aff;
                border-radius: 14px;
            }
            QSlider::handle:vertical {
                height: 36px;
                width: 44px;
                margin: -8px -8px -8px -8px;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0     #ffffff,
                    stop: 0.2   #ffffff,
                    stop: 0.25  #b0b0b0,
                    stop: 0.27  #ffffff,
                    stop: 0.37  #ffffff,
                    stop: 0.42  #b0b0b0,
                    stop: 0.44  #ffffff,
                    stop: 0.54  #ffffff,
                    stop: 0.59  #b0b0b0,
                    stop: 0.61  #ffffff,
                    stop: 1     #ffffff);
                border: 1px solid #b0b0b0;
                border-radius: 18px;
            }
            QSlider::handle:vertical:hover {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0     #ffffff,
                    stop: 0.2   #ffffff,
                    stop: 0.25  #999999,
                    stop: 0.27  #ffffff,
                    stop: 0.37  #ffffff,
                    stop: 0.42  #999999,
                    stop: 0.44  #ffffff,
                    stop: 0.54  #ffffff,
                    stop: 0.59  #999999,
                    stop: 0.61  #ffffff,
                    stop: 1     #ffffff);
            }
            QSlider::handle:vertical:pressed {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0     #f5f5f5,
                    stop: 0.2   #f5f5f5,
                    stop: 0.25  #888888,
                    stop: 0.27  #f5f5f5,
                    stop: 0.37  #f5f5f5,
                    stop: 0.42  #888888,
                    stop: 0.44  #f5f5f5,
                    stop: 0.54  #f5f5f5,
                    stop: 0.59  #888888,
                    stop: 0.61  #f5f5f5,
                    stop: 1     #f5f5f5);
            }
        """)
        self._update_widget_style()

    def _update_widget_style(self):
        if self._locked:
            self.setStyleSheet("""
                ChannelWidget {
                    background-color: #f5f0f0;
                    border-radius: 3px;
                }
                #channelLabel {
                    color: #aaaaaa;
                    font-size: 12px;
                }
                #valueLabel {
                    color: #cccccc;
                }
            """)
        elif self._selected:
            self.setStyleSheet("""
                ChannelWidget {
                    background-color: #d6e8ff;
                    border: 1px solid #0078d4;
                    border-radius: 3px;
                }
                #channelLabel {
                    color: #000000;
                    font-size: 12px;
                }
                #valueLabel {
                    color: #444;
                }
            """)
        else:
            self.setStyleSheet("""
                #channelLabel {
                    color: #000000;
                    font-size: 12px;
                }
                #valueLabel {
                    color: #444;
                }
            """)

    def _update_lock_style(self):
        self.slider.setEnabled(not self._locked)
        self._update_widget_style()

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------
    def set_selected(self, selected):
        self._selected = selected
        self._update_widget_style()

    def set_custom_name(self, name):
        self._custom_name = name
        self.label_ch.setText(
            name if name else f"CH{self.channel_index + 1:03d}"
        )

    def set_locked(self, locked):
        self._locked = locked
        self._update_lock_style()

    def is_locked(self):
        return self._locked

    def set_value(self, value, block_signals=True):
        if block_signals:
            self.slider.blockSignals(True)
        self.slider.setValue(value)
        self.label_value.setText(str(value))
        if block_signals:
            self.slider.blockSignals(False)

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------
    def _on_value_changed(self, value):
        self.label_value.setText(str(value))
        if not self._locked:
            self.value_changed.emit(self.channel_index, value)

    def mouseDoubleClickEvent(self, event):
        if self._locked:
            return
        name = self._custom_name or f"CH{self.channel_index + 1:03d}"
        value, ok = QInputDialog.getInt(
            self,
            tr("input_channel_title", name=name),
            tr("input_channel_label"),
            self.slider.value(),
            0,
            255,
        )
        if ok:
            self.set_value(value, block_signals=False)
            self.value_changed.emit(self.channel_index, value)
