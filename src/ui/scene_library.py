import json
import os
import sys

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QInputDialog, QMessageBox, QLabel, QListWidgetItem,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont


class SceneLibraryDialog(QDialog):
    """In-app scene library — save/load/rename/delete scenes.

    Scenes are stored in a single local JSON file.
    """

    scene_loaded = pyqtSignal(list, dict, list)  # (channels, names, locked)

    def __init__(self, get_channels_fn, get_names_fn, get_locks_fn=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("场景库")
        self.setMinimumSize(360, 420)
        self._get_channels = get_channels_fn   # callable returning list[512]
        self._get_names = get_names_fn         # callable returning dict
        self._get_locks = get_locks_fn or (lambda: [])
        self._scenes = []                     # list of dicts
        self._data_dir = self._resolve_data_dir()
        self._file_path = os.path.join(self._data_dir, "scenes.json")
        self._init_ui()
        self._load_from_disk()

    @staticmethod
    def _resolve_data_dir():
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base, "scenes")

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("场景库")
        title.setFont(QFont("", 13, QFont.Bold))
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemDoubleClicked.connect(self._load_selected)
        layout.addWidget(self.list_widget, 1)

        # Buttons
        btn_row = QHBoxLayout()
        btn_save = QPushButton("保存当前场景")
        btn_save.clicked.connect(self._save_current)
        btn_load = QPushButton("加载")
        btn_load.clicked.connect(self._load_selected)
        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_load)

        btn_row2 = QHBoxLayout()
        btn_rename = QPushButton("重命名")
        btn_rename.clicked.connect(self._rename_selected)
        btn_del = QPushButton("删除")
        btn_del.clicked.connect(self._delete_selected)
        btn_row2.addWidget(btn_rename)
        btn_row2.addWidget(btn_del)

        btn_close = QPushButton("关闭")
        btn_close.clicked.connect(self.accept)

        layout.addLayout(btn_row)
        layout.addLayout(btn_row2)
        layout.addSpacing(6)
        layout.addWidget(btn_close)

    # ----------------------------------------------------------------
    # Disk I/O
    # ----------------------------------------------------------------
    def _load_from_disk(self):
        if not os.path.exists(self._file_path):
            return
        try:
            with open(self._file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._scenes = data.get("scenes", [])
            self._refresh_list()
        except Exception as e:
            QMessageBox.warning(self, "读取失败", f"无法加载场景库:\n{e}")

    def _save_to_disk(self):
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump({"scenes": self._scenes}, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"无法保存场景库:\n{e}")

    def _refresh_list(self):
        self.list_widget.clear()
        for s in self._scenes:
            item = QListWidgetItem(s["name"])
            item.setData(Qt.UserRole, self._scenes.index(s))
            self.list_widget.addItem(item)

    # ----------------------------------------------------------------
    # Actions
    # ----------------------------------------------------------------
    def _save_current(self):
        name, ok = QInputDialog.getText(
            self, "保存场景", "场景名称:", text=""
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        # Check for duplicate
        for s in self._scenes:
            if s["name"] == name:
                ret = QMessageBox.question(
                    self, "已存在",
                    f"场景「{name}」已存在，是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No,
                )
                if ret != QMessageBox.Yes:
                    return
                s["channels"] = list(self._get_channels())
                s["names"] = self._get_names() or {}
                s["locked"] = self._get_locks()
                self._save_to_disk()
                self._refresh_list()
                return

        self._scenes.append({
            "name": name,
            "channels": list(self._get_channels()),
            "names": self._get_names() or {},
            "locked": self._get_locks(),
        })
        self._save_to_disk()
        self._refresh_list()

    def _load_selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self._scenes):
            return
        scene = self._scenes[idx]
        if len(scene.get("channels", [])) != 512:
            QMessageBox.warning(self, "数据错误", "场景通道数据不完整")
            return
        self.scene_loaded.emit(
            scene["channels"],
            scene.get("names", {}),
            scene.get("locked", []),
        )

    def _rename_selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self._scenes):
            return
        old_name = self._scenes[idx]["name"]
        name, ok = QInputDialog.getText(
            self, "重命名", "新名称:", text=old_name
        )
        if ok and name.strip():
            self._scenes[idx]["name"] = name.strip()
            self._save_to_disk()
            self._refresh_list()

    def _delete_selected(self):
        item = self.list_widget.currentItem()
        if item is None:
            return
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self._scenes):
            return
        ret = QMessageBox.question(
            self, "确认删除",
            f"确定删除场景「{self._scenes[idx]['name']}」吗？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if ret == QMessageBox.Yes:
            self._scenes.pop(idx)
            self._save_to_disk()
            self._refresh_list()
