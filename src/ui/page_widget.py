from PyQt5.QtWidgets import QWidget, QGridLayout, QApplication
from PyQt5.QtCore import Qt, pyqtSignal
from .channel_widget import ChannelWidget


class PageWidget(QWidget):
    """A page showing 16 DMX channels in a 2×8 grid.

    Manages channel selection within the page and synchronises
    slider changes across all selected channels (group edit).
    """

    channel_changed = pyqtSignal(int, int)  # channel_index, value

    def __init__(self, page_index, parent=None):
        super().__init__(parent)
        self.page_index = page_index
        self.start_ch = page_index * 16
        self.channel_widgets = []
        self._selected_indices = set()  # absolute channel indices on this page
        self._init_ui()

    def _init_ui(self):
        grid = QGridLayout()
        grid.setSpacing(3)

        for i in range(16):
            ch_index = self.start_ch + i
            widget = ChannelWidget(ch_index)
            widget.value_changed.connect(self._on_value_changed)
            widget.selection_toggled.connect(self._on_selection_toggled)
            self.channel_widgets.append(widget)
            grid.addWidget(widget, i // 8, i % 8)

        self.setLayout(grid)

    # ----------------------------------------------------------------
    # Value change — with group sync
    # ----------------------------------------------------------------
    def _on_value_changed(self, channel, value):
        """Intercept value changes for group sync, then forward."""
        # If this channel is selected AND other channels are also selected,
        # sync the value to all selected siblings.
        if len(self._selected_indices) > 1 and channel in self._selected_indices:
            for idx in self._selected_indices:
                if idx != channel:
                    local = idx - self.start_ch
                    if 0 <= local < 16:
                        w = self.channel_widgets[local]
                        if not w.is_locked():
                            w.set_value(value, block_signals=True)
                            self.channel_changed.emit(idx, value)
        # Forward to MainWindow (updates transmitter)
        self.channel_changed.emit(channel, value)

    # ----------------------------------------------------------------
    # Selection handling
    # ----------------------------------------------------------------
    def _on_selection_toggled(self, channel):
        modifiers = QApplication.keyboardModifiers()
        ctrl = modifiers & Qt.ControlModifier

        if ctrl:
            # Ctrl+click: toggle single channel in multi-selection
            if channel in self._selected_indices:
                self._selected_indices.discard(channel)
            else:
                self._selected_indices.add(channel)
        else:
            # Plain click: clear all, select only this one
            self._clear_selection_visuals()
            self._selected_indices.clear()
            self._selected_indices.add(channel)

        # Update visual for this channel
        local = channel - self.start_ch
        if 0 <= local < 16:
            self.channel_widgets[local].set_selected(
                channel in self._selected_indices
            )

    def clear_selection(self):
        """Deselect all channels on this page."""
        self._clear_selection_visuals()
        self._selected_indices.clear()

    def _clear_selection_visuals(self):
        for idx in list(self._selected_indices):
            local = idx - self.start_ch
            if 0 <= local < 16:
                self.channel_widgets[local].set_selected(False)

    def get_selected_indices(self):
        return self._selected_indices.copy()

    # ----------------------------------------------------------------
    # Batch value updates
    # ----------------------------------------------------------------
    def set_channel_value(self, channel, value, block_signals=True):
        local_idx = channel - self.start_ch
        if 0 <= local_idx < 16:
            self.channel_widgets[local_idx].set_value(value, block_signals)

    def set_values(self, values, block_signals=True):
        """Set all 16 channel values from a 512-element iterable."""
        for widget in self.channel_widgets:
            idx = widget.channel_index
            if idx < len(values):
                widget.set_value(values[idx], block_signals)
                # Also update lock state (persisted names are restored separately)
