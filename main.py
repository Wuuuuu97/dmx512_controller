import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow
from src.i18n.translations import current_language


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DMX 调试助手")
    _ = current_language()  # ensure saved language preference is loaded
    app.setWindowIcon(MainWindow._make_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
