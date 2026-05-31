import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
                             QVBoxLayout, QLabel, QStatusBar)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QSurfaceFormat

from gl_widget import WaterGLWidget
from control_panel import ControlPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('水面波浪模拟 - FFT波谱合成')
        self.resize(1200, 800)
        
        self._setup_ui()
        self._setup_status_bar()
    
    def _setup_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.gl_widget = WaterGLWidget()
        self.control_panel = ControlPanel(self.gl_widget)
        
        main_layout.addWidget(self.gl_widget, stretch=1)
        main_layout.addWidget(self.control_panel)
        
        self.setCentralWidget(central_widget)
    
    def _setup_status_bar(self):
        status_bar = QStatusBar()
        status_bar.showMessage('使用鼠标控制相机 | 调节参数实时预览 | 可导出动画视频')
        self.setStatusBar(status_bar)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    format = QSurfaceFormat()
    format.setVersion(3, 3)
    format.setProfile(QSurfaceFormat.CoreProfile)
    format.setDepthBufferSize(24)
    format.setStencilBufferSize(8)
    format.setSamples(4)
    QSurfaceFormat.setDefaultFormat(format)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
