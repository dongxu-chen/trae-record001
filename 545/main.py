import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HDR Tone Mapping Tool")
    app.setOrganizationName("HDRTools")

    font = QFont("Segoe UI", 9)
    app.setFont(font)

    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
