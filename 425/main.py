import sys
from PyQt5.QtWidgets import QApplication
from gui.window import BinarizationWindow


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = BinarizationWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()