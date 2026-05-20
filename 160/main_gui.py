import sys
import numpy as np
from collections import deque
from threading import Thread

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGroupBox, QTabWidget,
    QSpinBox, QCheckBox, QLCDNumber, QGridLayout, QSplitter
)
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QObject
from PyQt5.QtGui import QFont, QColor
import pyqtgraph as pg

from brainflow_acquisition import DataAcquisition, DeviceType, DEVICE_CONFIG
from signal_processing import RealtimePipeline
from lsl_integration import LSLOutput, LSLStreamInfo, BandPowerLSLOutput


class SignalUpdate(QObject):
    update_plot = pyqtSignal()
    update_bandpower = pyqtSignal(dict)
    update_status = pyqtSignal(str)


class EEGToolbox(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.acquisition: DataAcquisition = None
        self.pipeline: RealtimePipeline = None
        self.lsl_output: LSLOutput = None
        self.bandpower_lsl: BandPowerLSLOutput = None
        
        self.signals = SignalUpdate()
        self.signals.update_plot.connect(self._update_plots)
        self.signals.update_bandpower.connect(self._update_bandpower_display)
        
        self.plot_buffer_size = 1000
        self.plot_buffers = []
        self.band_power_history = {
            band: deque(maxlen=100) for band in ['delta', 'theta', 'alpha', 'beta', 'gamma']
        }
        
        self.init_ui()
        self.setup_timer()
        
    def init_ui(self):
        self.setWindowTitle("EEG Processing Toolbox v2.0 - BrainFlow")
        self.setGeometry(50, 50, 1600, 1000)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        left_panel = self._create_control_panel()
        right_panel = self._create_display_panel()
        
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 1200])
        
        main_layout.addWidget(splitter)
        
    def _create_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        device_group = QGroupBox("设备连接")
        device_layout = QVBoxLayout()
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(QLabel("设备类型:"))
        self.device_combo = QComboBox()
        for dev_type, config in DEVICE_CONFIG.items():
            self.device_combo.addItem(config["name"], dev_type.value)
        h_layout.addWidget(self.device_combo)
        device_layout.addLayout(h_layout)
        
        self.connect_btn = QPushButton("连接设备")
        self.connect_btn.clicked.connect(self.toggle_connection)
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        device_layout.addWidget(self.connect_btn)
        
        self.start_stream_btn = QPushButton("开始采集")
        self.start_stream_btn.clicked.connect(self.toggle_stream)
        self.start_stream_btn.setEnabled(False)
        device_layout.addWidget(self.start_stream_btn)
        
        self.status_label = QLabel("状态: 未连接")
        self.status_label.setStyleSheet("color: #666; font-weight: bold;")
        device_layout.addWidget(self.status_label)
        
        device_group.setLayout(device_layout)
        layout.addWidget(device_group)
        
        lsl_group = QGroupBox("LSL 输出")
        lsl_layout = QVBoxLayout()
        
        self.lsl_eeg_btn = QPushButton("启动 EEG LSL 流")
        self.lsl_eeg_btn.clicked.connect(self.toggle_lsl_eeg)
        self.lsl_eeg_btn.setEnabled(False)
        lsl_layout.addWidget(self.lsl_eeg_btn)
        
        self.lsl_band_btn = QPushButton("启动 频段功率 LSL 流")
        self.lsl_band_btn.clicked.connect(self.toggle_lsl_bandpower)
        self.lsl_band_btn.setEnabled(False)
        lsl_layout.addWidget(self.lsl_band_btn)
        
        self.lsl_status_label = QLabel("LSL: 未启动")
        lsl_layout.addWidget(self.lsl_status_label)
        
        lsl_group.setLayout(lsl_layout)
        layout.addWidget(lsl_group)
        
        display_group = QGroupBox("显示设置")
        display_layout = QVBoxLayout()
        
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel("显示通道:"))
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(1, 16)
        self.channel_spin.setValue(4)
        h_layout2.addWidget(self.channel_spin)
        display_layout.addLayout(h_layout2)
        
        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(QLabel("时间窗口(秒):"))
        self.window_spin = QSpinBox()
        self.window_spin.setRange(1, 10)
        self.window_spin.setValue(3)
        h_layout3.addWidget(self.window_spin)
        display_layout.addLayout(h_layout3)
        
        self.show_bandpower_check = QCheckBox("显示频段功率")
        self.show_bandpower_check.setChecked(True)
        display_layout.addWidget(self.show_bandpower_check)
        
        display_group.setLayout(display_layout)
        layout.addWidget(display_group)
        
        bandpower_group = QGroupBox("专注度指标")
        bandpower_layout = QVBoxLayout()
        
        lcd_layout = QGridLayout()
        
        self.alpha_lcd = QLCDNumber()
        self.alpha_lcd.setStyleSheet("color: #00BCD4;")
        lcd_layout.addWidget(QLabel("Alpha:"), 0, 0)
        lcd_layout.addWidget(self.alpha_lcd, 0, 1)
        
        self.beta_lcd = QLCDNumber()
        self.beta_lcd.setStyleSheet("color: #FF9800;")
        lcd_layout.addWidget(QLabel("Beta:"), 1, 0)
        lcd_layout.addWidget(self.beta_lcd, 1, 1)
        
        self.focus_lcd = QLCDNumber()
        self.focus_lcd.setStyleSheet("color: #4CAF50; background-color: #1a1a1a;")
        lcd_layout.addWidget(QLabel("专注度:"), 2, 0)
        lcd_layout.addWidget(self.focus_lcd, 2, 1)
        
        bandpower_layout.addLayout(lcd_layout)
        bandpower_group.setLayout(bandpower_layout)
        layout.addWidget(bandpower_group)
        
        api_group = QGroupBox("REST API")
        api_layout = QVBoxLayout()
        
        self.api_btn = QPushButton("启动 API 服务器 (:8000)")
        self.api_btn.clicked.connect(self.toggle_api_server)
        api_layout.addWidget(self.api_btn)
        
        self.api_status_label = QLabel("API: 未启动")
        api_layout.addWidget(self.api_status_label)
        
        api_group.setLayout(api_layout)
        layout.addWidget(api_group)
        
        layout.addStretch()
        
        return panel
        
    def _create_display_panel(self) -> QWidget:
        panel = QTabWidget()
        
        self.eeg_tab = QWidget()
        eeg_layout = QVBoxLayout(self.eeg_tab)
        self.eeg_plot_widget = pg.PlotWidget(title="实时 EEG 信号")
        self.eeg_plot_widget.setBackground('w')
        self.eeg_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.eeg_plot_widget.setLabel('left', '振幅', 'µV')
        self.eeg_plot_widget.setLabel('bottom', '时间', 's')
        eeg_layout.addWidget(self.eeg_plot_widget)
        panel.addTab(self.eeg_tab, "EEG 信号")
        
        self.bandpower_tab = QWidget()
        band_layout = QVBoxLayout(self.bandpower_tab)
        self.band_plot_widget = pg.PlotWidget(title="频段功率变化")
        self.band_plot_widget.setBackground('w')
        self.band_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.band_plot_widget.addLegend()
        band_layout.addWidget(self.band_plot_widget)
        panel.addTab(self.bandpower_tab, "频段功率")
        
        self.spectrum_tab = QWidget()
        spec_layout = QVBoxLayout(self.spectrum_tab)
        self.spec_plot_widget = pg.PlotWidget(title="功率谱密度")
        self.spec_plot_widget.setBackground('w')
        self.spec_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.spec_plot_widget.setLabel('left', '功率')
        self.spec_plot_widget.setLabel('bottom', '频率', 'Hz')
        spec_layout.addWidget(self.spec_plot_widget)
        panel.addTab(self.spectrum_tab, "频谱")
        
        return panel
        
    def setup_timer(self):
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(lambda: self.signals.update_plot.emit())
        self.plot_timer.start(50)
        
    def toggle_connection(self):
        if self.acquisition is None or not self.acquisition._is_running:
            self._connect_device()
        else:
            self._disconnect_device()
            
    def _connect_device(self):
        device_type = self.device_combo.currentData()
        
        try:
            dev_enum = DeviceType(device_type)
            self.acquisition = DataAcquisition(dev_enum)
            
            connected = self.acquisition.connect()
            
            if connected:
                sampling_rate = self.acquisition.get_sampling_rate()
                num_channels = self.acquisition.get_num_channels()
                
                self.pipeline = RealtimePipeline(sampling_rate, num_channels)
                self.pipeline.add_callback(self._on_bandpower_update)
                
                self.acquisition.add_callback(self.pipeline.process_sample)
                
                self.plot_buffers = [deque(maxlen=self.plot_buffer_size) for _ in range(num_channels)]
                
                self.connect_btn.setText("断开设备")
                self.connect_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
                self.start_stream_btn.setEnabled(True)
                self.lsl_eeg_btn.setEnabled(True)
                self.lsl_band_btn.setEnabled(True)
                
                self.status_label.setText(f"状态: 已连接 ({DEVICE_CONFIG[dev_enum]['name']})")
                self.status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
            else:
                self.status_label.setText("状态: 连接失败")
                self.acquisition = None
                
        except Exception as e:
            self.status_label.setText(f"错误: {str(e)[:50]}")
            
    def _disconnect_device(self):
        if self.acquisition:
            if self.acquisition._is_streaming:
                self.acquisition.stop_stream()
                
            self.acquisition.disconnect()
            self.acquisition = None
            
        self.pipeline = None
        self.plot_buffers = []
        
        self.connect_btn.setText("连接设备")
        self.connect_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.start_stream_btn.setEnabled(False)
        self.start_stream_btn.setText("开始采集")
        self.lsl_eeg_btn.setEnabled(False)
        self.lsl_band_btn.setEnabled(False)
        
        self.status_label.setText("状态: 未连接")
        self.status_label.setStyleSheet("color: #666; font-weight: bold;")
        
    def toggle_stream(self):
        if not self.acquisition:
            return
            
        if not self.acquisition._is_streaming:
            self.acquisition.start_stream()
            self.start_stream_btn.setText("停止采集")
            self.start_stream_btn.setStyleSheet("background-color: #ff9800; color: white; font-weight: bold;")
            self.status_label.setText("状态: 采集中...")
        else:
            self.acquisition.stop_stream()
            self.start_stream_btn.setText("开始采集")
            self.start_stream_btn.setStyleSheet("")
            self.status_label.setText("状态: 已连接 (未采集)")
            
    def _on_bandpower_update(self, data: np.ndarray, band_powers: dict):
        self.signals.update_bandpower.emit(band_powers)
        
    def _update_bandpower_display(self, band_powers: dict):
        for band, value in band_powers.items():
            if band in self.band_power_history:
                self.band_power_history[band].append(value)
                
        if 'alpha' in band_powers:
            self.alpha_lcd.display(f"{band_powers['alpha']:.3f}")
        if 'beta' in band_powers:
            self.beta_lcd.display(f"{band_powers['beta']:.3f}")
            
        if band_powers.get('beta', 0) > 0 and band_powers.get('alpha', 0) > 0:
            focus_score = min(100, band_powers['beta'] / band_powers['alpha'] * 50)
            self.focus_lcd.display(f"{focus_score:.1f}")
            
    def _update_plots(self):
        if not self.pipeline or not self.acquisition:
            return
            
        filtered_data = self.pipeline.get_filtered_data(num_samples=50)
        
        if filtered_data.size == 0:
            return
            
        num_display_ch = min(self.channel_spin.value(), len(self.plot_buffers))
        
        for ch in range(len(self.plot_buffers)):
            if ch < filtered_data.shape[0]:
                self.plot_buffers[ch].extend(filtered_data[ch])
                
        self._update_eeg_plot(num_display_ch)
        
        if self.show_bandpower_check.isChecked():
            self._update_bandpower_plot()
            
        if len(self.plot_buffers[0]) >= 256:
            self._update_spectrum_plot()
            
    def _update_eeg_plot(self, num_channels: int):
        self.eeg_plot_widget.clear()
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
                  
        window_size = int(self.acquisition.get_sampling_rate() * self.window_spin.value())
        
        for ch in range(num_channels):
            if len(self.plot_buffers[ch]) == 0:
                continue
                
            data = np.array(list(self.plot_buffers[ch])[-window_size:])
            time_axis = np.arange(len(data)) / self.acquisition.get_sampling_rate()
            
            offset = ch * 100
            curve = pg.PlotCurveItem(time_axis, data + offset, 
                                     pen=pg.mkPen(colors[ch % len(colors)], width=1.5))
            self.eeg_plot_widget.addItem(curve)
            
    def _update_bandpower_plot(self):
        self.band_plot_widget.clear()
        
        colors = {
            'delta': '#1f77b4',
            'theta': '#9467bd',
            'alpha': '#2ca02c',
            'beta': '#ff7f0e',
            'gamma': '#d62728'
        }
        
        for band, history in self.band_power_history.items():
            if len(history) > 0:
                data = np.array(list(history))
                curve = pg.PlotCurveItem(data, pen=pg.mkPen(colors[band], width=2), name=band)
                self.band_plot_widget.addItem(curve)
                
    def _update_spectrum_plot(self):
        self.spec_plot_widget.clear()
        
        if len(self.plot_buffers) == 0 or len(self.plot_buffers[0]) < 256:
            return
            
        data = np.array(list(self.plot_buffers[0])[-256:])
        
        fft_vals = np.fft.rfft(data * np.hanning(len(data)))
        fft_freq = np.fft.rfftfreq(len(data), 1.0 / self.acquisition.get_sampling_rate())
        power_spectrum = np.abs(fft_vals) ** 2
        
        mask = fft_freq <= 50
        curve = pg.PlotCurveItem(fft_freq[mask], power_spectrum[mask],
                                 pen=pg.mkPen('#1f77b4', width=2))
        self.spec_plot_widget.addItem(curve)
        
    def toggle_lsl_eeg(self):
        if not self.acquisition:
            return
            
        if self.lsl_output is None:
            stream_info = LSLStreamInfo(
                name="EEG_Toolbox",
                type="EEG",
                channel_count=self.acquisition.get_num_channels(),
                sampling_rate=self.acquisition.get_sampling_rate(),
                channel_format="float32"
            )
            self.lsl_output = LSLOutput(stream_info)
            
            if self.lsl_output.create_stream():
                self.lsl_eeg_btn.setText("停止 EEG LSL 流")
                self.lsl_status_label.setText("LSL EEG: 运行中")
            else:
                self.lsl_output = None
        else:
            self.lsl_output.close()
            self.lsl_output = None
            self.lsl_eeg_btn.setText("启动 EEG LSL 流")
            self.lsl_status_label.setText("LSL: 未启动")
            
    def toggle_lsl_bandpower(self):
        if not self.pipeline:
            return
            
        if self.bandpower_lsl is None:
            self.bandpower_lsl = BandPowerLSLOutput()
            
            if self.bandpower_lsl.initialize():
                def lsl_callback(data, band_powers):
                    self.bandpower_lsl.push_band_powers(band_powers)
                    
                self.pipeline.add_callback(lsl_callback)
                self.lsl_band_btn.setText("停止 频段功率 LSL 流")
            else:
                self.bandpower_lsl = None
        else:
            self.bandpower_lsl.close()
            self.bandpower_lsl = None
            self.lsl_band_btn.setText("启动 频段功率 LSL 流")
            
    def toggle_api_server(self):
        if not hasattr(self, '_api_thread') or not self._api_thread.is_alive():
            import rest_api
            
            self._api_thread = Thread(target=rest_api.run_api_server, daemon=True)
            self._api_thread.start()
            
            self.api_btn.setText("停止 API 服务器")
            self.api_status_label.setText("API: 运行中 (http://localhost:8000)")
            self.api_status_label.setStyleSheet("color: #4CAF50;")
        else:
            self.api_btn.setText("启动 API 服务器 (:8000)")
            self.api_status_label.setText("API: 未启动")
            self.api_status_label.setStyleSheet("color: #666;")
            
    def closeEvent(self, event):
        if self.acquisition and self.acquisition._is_streaming:
            self.acquisition.stop_stream()
            
        if self.acquisition:
            self.acquisition.disconnect()
            
        if self.lsl_output:
            self.lsl_output.close()
            
        if self.bandpower_lsl:
            self.bandpower_lsl.close()
            
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    app.setStyle('Fusion')
    
    window = EEGToolbox()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
