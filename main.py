import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from PyQt5.QtWidgets import QApplication
from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("DMX 调试助手")
    app.setWindowIcon(MainWindow._make_icon())

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
