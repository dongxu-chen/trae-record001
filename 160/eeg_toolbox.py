import sys
import numpy as np
from collections import deque
import time
import mne
from mne.preprocessing import ICA
from mne.minimum_norm import make_inverse_operator, apply_inverse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QComboBox, 
                             QSpinBox, QDoubleSpinBox, QGroupBox, QFileDialog,
                             QTabWidget, QListWidget, QCheckBox, QProgressBar,
                             QListWidgetItem, QSlider, LCDNumber)
from PyQt5.QtCore import QTimer, Qt, QThread, pyqtSignal, QMutex
from PyQt5.QtGui import QFont, QColor, QPalette
import pyqtgraph as pg
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.cm as cm

try:
    from pylsl import StreamInlet, resolve_stream, StreamInfo, StreamOutlet
    LSL_AVAILABLE = True
except ImportError:
    LSL_AVAILABLE = False


class LSLReceiverThread(QThread):
    data_received = pyqtSignal(np.ndarray, float)
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, stream_type='EEG'):
        super().__init__()
        self.stream_type = stream_type
        self.running = False
        self.inlet = None
        self.mutex = QMutex()
        
    def run(self):
        self.running = True
        try:
            streams = resolve_stream('type', self.stream_type)
            if len(streams) > 0:
                self.mutex.lock()
                self.inlet = StreamInlet(streams[0])
                info = self.inlet.info()
                self.mutex.unlock()
                self.connection_status.emit(True, f'已连接: {info.name()} ({info.channel_count()}通道)')
                
                while self.running:
                    sample, timestamp = self.inlet.pull_sample(timeout=0.1)
                    if sample is not None:
                        self.data_received.emit(np.array(sample), timestamp)
            else:
                self.connection_status.emit(False, '未找到LSL流')
        except Exception as e:
            self.connection_status.emit(False, f'连接错误: {str(e)}')
            
    def stop(self):
        self.running = False
        self.mutex.lock()
        if self.inlet:
            self.inlet.close_stream()
        self.mutex.unlock()
        self.wait()


class DataAcquisitionThread(QThread):
    data_ready = pyqtSignal(np.ndarray, np.ndarray)
    
    def __init__(self, raw_data, sfreq, buffer_size=1000):
        super().__init__()
        self.raw_data = raw_data
        self.sfreq = sfreq
        self.buffer_size = buffer_size
        self.running = False
        self.index = 0
        
    def run(self):
        self.running = True
        while self.running:
            chunk_size = int(self.sfreq * 0.02)
            end_idx = min(self.index + chunk_size, len(self.raw_data))
            
            if end_idx > self.index:
                chunk = self.raw_data[self.index:end_idx]
                time_chunk = np.arange(len(chunk)) / self.sfreq
                self.data_ready.emit(chunk, time_chunk)
                self.index = end_idx
                
                if self.index >= len(self.raw_data):
                    self.index = 0
            
            self.msleep(20)
            
    def stop(self):
        self.running = False
        self.wait()


class NeuroFeedback:
    def __init__(self, sfreq):
        self.sfreq = sfreq
        self.window_size = int(sfreq * 2)
        self.alpha_power_history = deque(maxlen=50)
        self.baseline_alpha = None
        self.focus_score = 0
        
    def calculate_alpha_power(self, data):
        if len(data) < self.window_size:
            return 0
            
        recent_data = np.array(data[-self.window_size:])
        n = len(recent_data)
        
        fft_vals = np.fft.rfft(recent_data * np.hanning(n))
        fft_freq = np.fft.rfftfreq(n, 1/self.sfreq)
        
        alpha_mask = (fft_freq >= 8) & (fft_freq <= 13)
        alpha_power = np.mean(np.abs(fft_vals[alpha_mask])**2)
        
        return alpha_power
        
    def update(self, data):
        alpha_power = self.calculate_alpha_power(data)
        
        if len(self.alpha_power_history) < 10:
            self.alpha_power_history.append(alpha_power)
            self.baseline_alpha = np.mean(self.alpha_power_history)
            return 50
            
        self.alpha_power_history.append(alpha_power)
        
        if self.baseline_alpha > 0:
            ratio = alpha_power / self.baseline_alpha
            self.focus_score = np.clip(100 - (ratio * 50), 0, 100)
        else:
            self.focus_score = 50
            
        return self.focus_score


class EEGToolbox(QMainWindow):
    def __init__(self):
        super().__init__()
        self.raw = None
        self.raw_original = None
        self.ica = None
        self.epochs = None
        self.evoked = None
        self.inverse_operator = None
        self.stc = None
        self.bad_channels = []
        
        self.acquisition_thread = None
        self.lsl_thread = None
        self.neurofeedback = None
        
        self.buffer_size = 5000
        self.data_buffer = deque(maxlen=self.buffer_size)
        self.time_buffer = deque(maxlen=self.buffer_size)
        self.display_buffer = deque(maxlen=self.buffer_size)
        self.display_time_buffer = deque(maxlen=self.buffer_size)
        
        self.lsl_buffer = []
        self.lsl_sfreq = 250
        self.lsl_channel_names = []
        
        self.artifact_threshold = 100
        self.artifact_rejection_enabled = False
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle('脑电信号实时处理工具箱 v3.0')
        self.setGeometry(50, 50, 1800, 1000)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel, 1)
        
        display_panel = self.create_display_panel()
        main_layout.addWidget(display_panel, 4)
        
    def create_control_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        lsl_group = QGroupBox('LSL设备连接')
        lsl_layout = QVBoxLayout()
        self.lsl_status = QLabel('状态: 未连接')
        lsl_layout.addWidget(self.lsl_status)
        
        h_layout_lsl = QHBoxLayout()
        self.lsl_stream_type = QComboBox()
        self.lsl_stream_type.addItems(['EEG', 'EEG_256', 'EEG_128'])
        h_layout_lsl.addWidget(QLabel('流类型:'))
        h_layout_lsl.addWidget(self.lsl_stream_type)
        lsl_layout.addLayout(h_layout_lsl)
        
        self.connect_lsl_btn = QPushButton('连接LSL流')
        self.connect_lsl_btn.clicked.connect(self.toggle_lsl_connection)
        lsl_layout.addWidget(self.connect_lsl_btn)
        
        if not LSL_AVAILABLE:
            self.lsl_status.setText('状态: pylsl未安装')
            self.connect_lsl_btn.setEnabled(False)
        lsl_group.setLayout(lsl_layout)
        layout.addWidget(lsl_group)
        
        file_group = QGroupBox('数据加载')
        file_layout = QVBoxLayout()
        self.load_btn = QPushButton('加载EEG数据 (.fif)')
        self.load_btn.clicked.connect(self.load_data)
        self.sample_btn = QPushButton('加载示例数据')
        self.sample_btn.clicked.connect(self.load_sample_data)
        self.file_label = QLabel('未加载数据')
        file_layout.addWidget(self.load_btn)
        file_layout.addWidget(self.sample_btn)
        file_layout.addWidget(self.file_label)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        artifact_group = QGroupBox('伪迹自动拒绝')
        artifact_layout = QVBoxLayout()
        
        self.artifact_enabled = QCheckBox('启用伪迹自动拒绝')
        self.artifact_enabled.stateChanged.connect(self.toggle_artifact_rejection)
        artifact_layout.addWidget(self.artifact_enabled)
        
        h_layout_art = QHBoxLayout()
        h_layout_art.addWidget(QLabel('阈值 (µV):'))
        self.artifact_threshold_spin = QDoubleSpinBox()
        self.artifact_threshold_spin.setRange(10, 500)
        self.artifact_threshold_spin.setValue(100)
        h_layout_art.addWidget(self.artifact_threshold_spin)
        artifact_layout.addLayout(h_layout_art)
        
        self.auto_threshold_btn = QPushButton('自适应阈值校准')
        self.auto_threshold_btn.clicked.connect(self.calibrate_threshold)
        artifact_layout.addWidget(self.auto_threshold_btn)
        
        self.artifact_count_label = QLabel('检测到伪迹: 0')
        artifact_layout.addWidget(self.artifact_count_label)
        artifact_group.setLayout(artifact_layout)
        layout.addWidget(artifact_group)
        
        bad_channel_group = QGroupBox('坏导检测与插值')
        bad_channel_layout = QVBoxLayout()
        self.detect_bad_btn = QPushButton('自动检测坏导')
        self.detect_bad_btn.clicked.connect(self.detect_bad_channels)
        bad_channel_layout.addWidget(self.detect_bad_btn)
        
        self.bad_channel_list = QListWidget()
        self.bad_channel_list.setMaximumHeight(60)
        bad_channel_layout.addWidget(self.bad_channel_list)
        
        self.interpolate_btn = QPushButton('球形插值修复坏导')
        self.interpolate_btn.clicked.connect(self.interpolate_bad_channels)
        bad_channel_layout.addWidget(self.interpolate_btn)
        
        self.bad_channel_label = QLabel('未检测到坏导')
        bad_channel_layout.addWidget(self.bad_channel_label)
        bad_channel_group.setLayout(bad_channel_layout)
        layout.addWidget(bad_channel_group)
        
        filter_group = QGroupBox('EEG滤波')
        filter_layout = QVBoxLayout()
        
        h_layout1 = QHBoxLayout()
        h_layout1.addWidget(QLabel('低通 (Hz):'))
        self.low_pass = QDoubleSpinBox()
        self.low_pass.setRange(0.1, 100)
        self.low_pass.setValue(40)
        h_layout1.addWidget(self.low_pass)
        filter_layout.addLayout(h_layout1)
        
        h_layout2 = QHBoxLayout()
        h_layout2.addWidget(QLabel('高通 (Hz):'))
        self.high_pass = QDoubleSpinBox()
        self.high_pass.setRange(0.01, 50)
        self.high_pass.setValue(0.1)
        h_layout2.addWidget(self.high_pass)
        filter_layout.addLayout(h_layout2)
        
        self.filter_btn = QPushButton('应用滤波')
        self.filter_btn.clicked.connect(self.apply_filter)
        filter_layout.addWidget(self.filter_btn)
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        ica_group = QGroupBox('ICA伪迹去除')
        ica_layout = QVBoxLayout()
        
        h_layout3 = QHBoxLayout()
        h_layout3.addWidget(QLabel('ICA成分数:'))
        self.n_components = QSpinBox()
        self.n_components.setRange(1, 64)
        self.n_components.setValue(15)
        h_layout3.addWidget(self.n_components)
        ica_layout.addLayout(h_layout3)
        
        h_layout_eog = QHBoxLayout()
        h_layout_eog.addWidget(QLabel('EOG阈值:'))
        self.eog_threshold = QDoubleSpinBox()
        self.eog_threshold.setRange(0.1, 1.0)
        self.eog_threshold.setValue(0.4)
        self.eog_threshold.setSingleStep(0.05)
        h_layout_eog.addWidget(self.eog_threshold)
        ica_layout.addLayout(h_layout_eog)
        
        self.fit_ica_btn = QPushButton('拟合ICA')
        self.fit_ica_btn.clicked.connect(self.fit_ica)
        ica_layout.addWidget(self.fit_ica_btn)
        
        self.auto_detect_ica_btn = QPushButton('自动识别EOG伪迹')
        self.auto_detect_ica_btn.clicked.connect(self.auto_detect_eog_artifacts)
        ica_layout.addWidget(self.auto_detect_ica_btn)
        
        self.ica_list = QListWidget()
        self.ica_list.setMaximumHeight(80)
        ica_layout.addWidget(self.ica_list)
        
        self.apply_ica_btn = QPushButton('去除选中成分')
        self.apply_ica_btn.clicked.connect(self.apply_ica)
        ica_layout.addWidget(self.apply_ica_btn)
        
        self.ica_label = QLabel('')
        ica_layout.addWidget(self.ica_label)
        ica_group.setLayout(ica_layout)
        layout.addWidget(ica_group)
        
        source_group = QGroupBox('源定位 (MNE)')
        source_layout = QVBoxLayout()
        
        self.source_method = QComboBox()
        self.source_method.addItems(['MNE', 'sLORETA', 'dSPM'])
        source_layout.addWidget(QLabel('反演方法:'))
        source_layout.addWidget(self.source_method)
        
        self.compute_inverse_btn = QPushButton('计算逆算子')
        self.compute_inverse_btn.clicked.connect(self.compute_inverse_operator)
        source_layout.addWidget(self.compute_inverse_btn)
        
        self.apply_source_btn = QPushButton('源定位反演')
        self.apply_source_btn.clicked.connect(self.apply_source_localization)
        source_layout.addWidget(self.apply_source_btn)
        
        self.source_label = QLabel('')
        source_layout.addWidget(self.source_label)
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        epoch_group = QGroupBox('事件电位提取')
        epoch_layout = QVBoxLayout()
        
        h_layout4 = QHBoxLayout()
        h_layout4.addWidget(QLabel('时间窗 (s):'))
        self.tmin = QDoubleSpinBox()
        self.tmin.setRange(-2, 0)
        self.tmin.setValue(-0.2)
        h_layout4.addWidget(self.tmin)
        self.tmax = QDoubleSpinBox()
        self.tmax.setRange(0, 2)
        self.tmax.setValue(0.5)
        h_layout4.addWidget(self.tmax)
        epoch_layout.addLayout(h_layout4)
        
        h_layout5 = QHBoxLayout()
        h_layout5.addWidget(QLabel('基线校正 (-200ms~0ms):'))
        self.baseline_check = QCheckBox()
        self.baseline_check.setChecked(True)
        h_layout5.addWidget(self.baseline_check)
        epoch_layout.addLayout(h_layout5)
        
        self.event_ids = QComboBox()
        epoch_layout.addWidget(QLabel('选择事件ID:'))
        epoch_layout.addWidget(self.event_ids)
        
        self.extract_epochs_btn = QPushButton('提取事件电位')
        self.extract_epochs_btn.clicked.connect(self.extract_epochs)
        epoch_layout.addWidget(self.extract_epochs_btn)
        epoch_group.setLayout(epoch_layout)
        layout.addWidget(epoch_group)
        
        feedback_group = QGroupBox('神经反馈训练 (Alpha波)')
        feedback_layout = QVBoxLayout()
        
        self.feedback_channel = QComboBox()
        feedback_layout.addWidget(QLabel('反馈通道:'))
        feedback_layout.addWidget(self.feedback_channel)
        
        self.start_feedback_btn = QPushButton('开始反馈训练')
        self.start_feedback_btn.setCheckable(True)
        self.start_feedback_btn.clicked.connect(self.toggle_neurofeedback)
        feedback_layout.addWidget(self.start_feedback_btn)
        
        self.focus_lcd = LCDNumber()
        self.focus_lcd.setDigitCount(3)
        self.focus_lcd.display(50)
        self.focus_lcd.setStyleSheet('background-color: #333; color: #0f0;')
        feedback_layout.addWidget(QLabel('专注度分数:'))
        feedback_layout.addWidget(self.focus_lcd)
        
        self.feedback_status = QLabel('就绪')
        feedback_layout.addWidget(self.feedback_status)
        feedback_group.setLayout(feedback_layout)
        layout.addWidget(feedback_group)
        
        realtime_group = QGroupBox('实时显示')
        realtime_layout = QVBoxLayout()
        self.start_realtime_btn = QPushButton('开始实时显示')
        self.start_realtime_btn.setCheckable(True)
        self.start_realtime_btn.clicked.connect(self.toggle_realtime)
        realtime_layout.addWidget(self.start_realtime_btn)
        
        h_layout6 = QHBoxLayout()
        h_layout6.addWidget(QLabel('窗口大小 (s):'))
        self.window_size_spin = QDoubleSpinBox()
        self.window_size_spin.setRange(1, 10)
        self.window_size_spin.setValue(3)
        h_layout6.addWidget(self.window_size_spin)
        realtime_layout.addLayout(h_layout6)
        
        self.channel_select = QComboBox()
        realtime_layout.addWidget(QLabel('选择通道:'))
        realtime_layout.addWidget(self.channel_select)
        
        self.latency_label = QLabel('延迟: -- ms')
        realtime_layout.addWidget(self.latency_label)
        realtime_group.setLayout(realtime_layout)
        layout.addWidget(realtime_group)
        
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        layout.addStretch()
        return panel
        
    def create_display_panel(self):
        panel = QTabWidget()
        
        self.raw_tab = QWidget()
        raw_layout = QVBoxLayout(self.raw_tab)
        self.raw_figure = Figure(figsize=(12, 7))
        self.raw_canvas = FigureCanvas(self.raw_figure)
        raw_layout.addWidget(self.raw_canvas)
        panel.addTab(self.raw_tab, '原始数据')
        
        self.bad_channel_tab = QWidget()
        bad_channel_layout = QVBoxLayout(self.bad_channel_tab)
        self.bad_channel_figure = Figure(figsize=(12, 6))
        self.bad_channel_canvas = FigureCanvas(self.bad_channel_figure)
        bad_channel_layout.addWidget(self.bad_channel_canvas)
        panel.addTab(self.bad_channel_tab, '坏导检测')
        
        self.filter_tab = QWidget()
        filter_layout = QVBoxLayout(self.filter_tab)
        self.filter_figure = Figure(figsize=(12, 6))
        self.filter_canvas = FigureCanvas(self.filter_figure)
        filter_layout.addWidget(self.filter_canvas)
        panel.addTab(self.filter_tab, '滤波结果')
        
        self.ica_tab = QWidget()
        ica_layout = QVBoxLayout(self.ica_tab)
        self.ica_figure = Figure(figsize=(12, 8))
        self.ica_canvas = FigureCanvas(self.ica_figure)
        ica_layout.addWidget(self.ica_canvas)
        panel.addTab(self.ica_tab, 'ICA成分')
        
        self.source_tab = QWidget()
        source_layout = QVBoxLayout(self.source_tab)
        self.source_figure = Figure(figsize=(12, 8))
        self.source_canvas = FigureCanvas(self.source_figure)
        source_layout.addWidget(self.source_canvas)
        panel.addTab(self.source_tab, '源定位')
        
        self.epoch_tab = QWidget()
        epoch_layout = QVBoxLayout(self.epoch_tab)
        self.epoch_figure = Figure(figsize=(12, 6))
        self.epoch_canvas = FigureCanvas(self.epoch_figure)
        epoch_layout.addWidget(self.epoch_canvas)
        panel.addTab(self.epoch_tab, '事件电位')
        
        self.realtime_tab = QWidget()
        realtime_layout = QVBoxLayout(self.realtime_tab)
        self.realtime_plot = pg.PlotWidget(title='实时波形显示 (双缓冲)')
        self.realtime_curve = self.realtime_plot.plot(pen=pg.mkPen('g', width=1.5))
        self.realtime_plot.setLabel('left', '振幅', 'µV')
        self.realtime_plot.setLabel('bottom', '时间', 's')
        self.realtime_plot.showGrid(x=True, y=True, alpha=0.3)
        realtime_layout.addWidget(self.realtime_plot)
        panel.addTab(self.realtime_tab, '实时波形')
        
        self.feedback_tab = QWidget()
        feedback_layout = QVBoxLayout(self.feedback_tab)
        
        feedback_container = QWidget()
        fb_hbox = QHBoxLayout(feedback_container)
        
        self.alpha_plot = pg.PlotWidget(title='Alpha波功率变化')
        self.alpha_curve = self.alpha_plot.plot(pen=pg.mkPen('c', width=2))
        self.alpha_plot.setLabel('left', '功率')
        self.alpha_plot.setLabel('bottom', '时间', 'samples')
        self.alpha_plot.showGrid(x=True, y=True, alpha=0.3)
        fb_hbox.addWidget(self.alpha_plot, 2)
        
        gauge_widget = QWidget()
        gauge_layout = QVBoxLayout(gauge_widget)
        
        self.gauge_figure = Figure(figsize=(4, 4))
        self.gauge_canvas = FigureCanvas(self.gauge_figure)
        gauge_layout.addWidget(self.gauge_canvas)
        
        self.feedback_message = QLabel('准备开始...')
        self.feedback_message.setAlignment(Qt.AlignCenter)
        self.feedback_message.setFont(QFont('Arial', 14, QFont.Bold))
        gauge_layout.addWidget(self.feedback_message)
        
        fb_hbox.addWidget(gauge_widget, 1)
        feedback_layout.addWidget(feedback_container)
        panel.addTab(self.feedback_tab, '神经反馈')
        
        self.display_timer = QTimer()
        self.display_timer.timeout.connect(self.swap_buffers_and_display)
        self.feedback_timer = QTimer()
        self.feedback_timer.timeout.connect(self.update_feedback)
        self.realtime_index = 0
        self.last_update_time = 0
        self.artifact_count = 0
        self.alpha_history = deque(maxlen=100)
        self.focus_history = deque(maxlen=100)
        
        return panel
        
    def toggle_lsl_connection(self):
        if self.lsl_thread is None:
            self.connect_lsl_btn.setText('断开LSL流')
            self.start_lsl_stream()
        else:
            self.connect_lsl_btn.setText('连接LSL流')
            self.stop_lsl_stream()
            
    def start_lsl_stream(self):
        stream_type = self.lsl_stream_type.currentText()
        self.lsl_thread = LSLReceiverThread(stream_type)
        self.lsl_thread.connection_status.connect(self.on_lsl_status)
        self.lsl_thread.data_received.connect(self.on_lsl_data)
        self.lsl_thread.start()
        
    def stop_lsl_stream(self):
        if self.lsl_thread is not None:
            self.lsl_thread.stop()
            self.lsl_thread = None
        self.lsl_status.setText('状态: 未连接')
        
    def on_lsl_status(self, connected, message):
        if connected:
            self.lsl_status.setText(f'状态: {message}')
            self.neurofeedback = NeuroFeedback(self.lsl_sfreq)
        else:
            self.lsl_status.setText(f'状态: {message}')
            
    def on_lsl_data(self, sample, timestamp):
        data_uv = sample * 1e6
        
        if self.artifact_rejection_enabled:
            if np.any(np.abs(data_uv) > self.artifact_threshold):
                self.artifact_count += 1
                self.artifact_count_label.setText(f'检测到伪迹: {self.artifact_count}')
                return
        
        self.lsl_buffer.extend(data_uv)
        if len(self.lsl_buffer) > self.buffer_size:
            self.lsl_buffer = self.lsl_buffer[-self.buffer_size:]
            
        self.data_buffer.extend(data_uv[:1])
        if len(self.data_buffer) > self.buffer_size:
            self.data_buffer = deque(list(self.data_buffer)[-self.buffer_size:], maxlen=self.buffer_size)
            
    def toggle_artifact_rejection(self, state):
        self.artifact_rejection_enabled = (state == Qt.Checked)
        
    def calibrate_threshold(self):
        if len(self.data_buffer) < 500:
            self.artifact_count_label.setText('数据不足，请先采集数据')
            return
            
        data = np.array(self.data_buffer)
        mean_amp = np.mean(np.abs(data))
        std_amp = np.std(data)
        
        adaptive_threshold = mean_amp + 3 * std_amp
        self.artifact_threshold_spin.setValue(adaptive_threshold)
        self.artifact_threshold = adaptive_threshold
        self.artifact_count_label.setText(f'校准完成: 阈值={adaptive_threshold:.1f}µV')
        
    def load_data(self):
        fname, _ = QFileDialog.getOpenFileName(self, '加载EEG数据', '', 'FIF文件 (*.fif)')
        if fname:
            self.raw = mne.io.read_raw_fif(fname, preload=True)
            self.raw_original = self.raw.copy()
            self.file_label.setText(f'已加载: {fname.split("/")[-1]}')
            self.update_channel_list()
            self.update_event_ids()
            self.plot_raw_data()
            
    def load_sample_data(self):
        self.file_label.setText('加载中...')
        QApplication.processEvents()
        
        sample_data_folder = mne.datasets.sample.data_path()
        sample_data_raw_file = (sample_data_folder / 'MEG' / 'sample' /
                                'sample_audvis_filt-0-40_raw.fif')
        self.raw = mne.io.read_raw_fif(sample_data_raw_file, preload=True)
        self.raw.pick_types(eeg=True, meg=False, eog=True, stim=True)
        self.raw_original = self.raw.copy()
        
        self.file_label.setText('已加载: 示例数据 (sample)')
        self.update_channel_list()
        self.update_event_ids()
        self.plot_raw_data()
        
    def update_channel_list(self):
        if self.raw is not None:
            eeg_channels = [ch for ch, ch_type in zip(self.raw.ch_names, self.raw.get_channel_types()) 
                          if ch_type == 'eeg']
            self.channel_select.clear()
            self.channel_select.addItems(eeg_channels)
            self.feedback_channel.clear()
            self.feedback_channel.addItems(eeg_channels)
            
    def update_event_ids(self):
        if self.raw is not None:
            events = mne.find_events(self.raw, verbose=False)
            if len(events) > 0:
                event_ids = np.unique(events[:, 2])
                self.event_ids.clear()
                self.event_ids.addItems([str(eid) for eid in event_ids])
                
    def plot_raw_data(self):
        if self.raw is None:
            return
            
        self.raw_figure.clear()
        ax = self.raw_figure.add_subplot(111)
        
        eeg_indices = [i for i, ch_type in enumerate(self.raw.get_channel_types()) if ch_type == 'eeg']
        data, times = self.raw[eeg_indices[:8], :1000]
        
        for i, channel_data in enumerate(data):
            ch_name = self.raw.ch_names[eeg_indices[i]]
            ax.plot(times, channel_data * 1e6 + i * 80, 
                    label=ch_name, alpha=0.8)
        
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('振幅 (µV)')
        ax.set_title('原始EEG数据 (前8通道)')
        ax.legend(loc='upper right', fontsize=7)
        self.raw_canvas.draw()
        
    def detect_bad_channels(self):
        if self.raw is None:
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        raw_copy = self.raw.copy()
        raw_copy.pick_types(eeg=True)
        
        data = raw_copy.get_data()
        
        variances = np.var(data, axis=1)
        mean_var = np.mean(variances)
        std_var = np.std(variances)
        
        bad_by_variance = np.where(variances > mean_var + 3 * std_var)[0]
        
        correlations = np.zeros(data.shape[0])
        for i in range(data.shape[0]):
            other_channels = np.delete(data, i, axis=0)
            corr = np.corrcoef(data[i], np.mean(other_channels, axis=0))[0, 1]
            correlations[i] = abs(corr)
        
        mean_corr = np.mean(correlations)
        std_corr = np.std(correlations)
        bad_by_correlation = np.where(correlations < mean_corr - 2 * std_corr)[0]
        
        bad_indices = np.union1d(bad_by_variance, bad_by_correlation)
        eeg_channels = [ch for ch, ch_type in zip(self.raw.ch_names, self.raw.get_channel_types()) 
                       if ch_type == 'eeg']
        self.bad_channels = [eeg_channels[i] for i in bad_indices]
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.bad_channel_list.clear()
        for ch in self.bad_channels:
            item = QListWidgetItem(ch)
            item.setCheckState(Qt.Checked)
            self.bad_channel_list.addItem(item)
            
        if self.bad_channels:
            self.bad_channel_label.setText(f'检测到 {len(self.bad_channels)} 个坏导')
        else:
            self.bad_channel_label.setText('未检测到坏导')
            
        self.bad_channel_figure.clear()
        ax = self.bad_channel_figure.add_subplot(121)
        ax.bar(range(len(variances)), variances * 1e12)
        ax.axhline(y=(mean_var + 3 * std_var) * 1e12, color='r', linestyle='--', label='阈值')
        ax.set_xlabel('通道索引')
        ax.set_ylabel('方差 (µV²)')
        ax.set_title('方差检测')
        ax.legend()
        
        ax2 = self.bad_channel_figure.add_subplot(122)
        ax2.bar(range(len(correlations)), correlations)
        ax2.axhline(y=mean_corr - 2 * std_corr, color='r', linestyle='--', label='阈值')
        ax2.set_xlabel('通道索引')
        ax2.set_ylabel('相关系数')
        ax2.set_title('相关性检测')
        ax2.legend()
        self.bad_channel_canvas.draw()
        
        self.progress.setValue(100)
        
    def interpolate_bad_channels(self):
        if self.raw is None:
            return
            
        selected_bads = []
        for i in range(self.bad_channel_list.count()):
            item = self.bad_channel_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_bads.append(item.text())
        
        if not selected_bads:
            self.bad_channel_label.setText('未选择要插值的通道')
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        self.raw.info['bads'] = selected_bads
        
        if not self.raw.info.get('dig'):
            montage = mne.channels.make_standard_montage('standard_1020')
            self.raw.set_montage(montage, match_case=False, on_missing='warn')
        
        self.raw.interpolate_bads(reset_bads=True, mode='accurate')
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.bad_channel_label.setText(f'已球形插值修复 {len(selected_bads)} 个坏导')
        self.plot_raw_data()
        
        self.progress.setValue(100)
        
    def apply_filter(self):
        if self.raw is None:
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        l_freq = self.high_pass.value()
        h_freq = self.low_pass.value()
        
        raw_filtered = self.raw.copy().filter(l_freq=l_freq, h_freq=h_freq, n_jobs=1)
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.filter_figure.clear()
        ax = self.filter_figure.add_subplot(111)
        
        eeg_indices = [i for i, ch_type in enumerate(self.raw.get_channel_types()) if ch_type == 'eeg']
        data_orig, times = self.raw[eeg_indices[0], :1000]
        data_filt, _ = raw_filtered[eeg_indices[0], :1000]
        
        ax.plot(times, data_orig[0] * 1e6, label='原始', alpha=0.5)
        ax.plot(times, data_filt[0] * 1e6, label=f'滤波后 ({l_freq}-{h_freq} Hz)')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('振幅 (µV)')
        ax.set_title(f'滤波效果对比 ({self.raw.ch_names[eeg_indices[0]]})')
        ax.legend()
        self.filter_canvas.draw()
        
        self.raw = raw_filtered
        self.progress.setValue(100)
        
    def fit_ica(self):
        if self.raw is None:
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        n_components = self.n_components.value()
        self.ica = ICA(n_components=n_components, random_state=97, max_iter=800, method='fastica')
        
        raw_for_ica = self.raw.copy().pick_types(eeg=True, eog=True)
        self.ica.fit(raw_for_ica)
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.ica_list.clear()
        for i in range(n_components):
            item = QListWidgetItem(f'ICA成分 {i:02d}')
            self.ica_list.addItem(item)
            
        self.ica_figure.clear()
        self.ica.plot_components(inst=self.raw, picks=range(min(10, n_components)), 
                                 figure=self.ica_figure, show=False)
        self.ica_canvas.draw()
        
        self.ica_label.setText('ICA拟合完成，可手动选择或自动检测伪迹')
        self.progress.setValue(100)
        
    def auto_detect_eog_artifacts(self):
        if self.raw is None or self.ica is None:
            self.ica_label.setText('请先加载数据并拟合ICA')
            return
            
        eog_channels = [ch for ch, ch_type in zip(self.raw.ch_names, self.raw.get_channel_types()) 
                       if ch_type == 'eog']
        
        if not eog_channels:
            self.ica_label.setText('未检测到EOG通道，使用相关通道替代')
            eog_channels = self.raw.ch_names[:2]
        
        self.progress.setValue(0)
        QApplication.processEvents()
        
        eog_idx, scores = self.ica.find_bads_eog(self.raw, ch_name=eog_channels[0] if eog_channels else None,
                                                  threshold=self.eog_threshold.value())
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        for i in range(self.ica_list.count()):
            item = self.ica_list.item(i)
            if i in eog_idx:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
        
        if eog_idx:
            self.ica_label.setText(f'自动检测到 {len(eog_idx)} 个EOG相关伪迹成分 (相关系数≥{self.eog_threshold.value()})')
        else:
            self.ica_label.setText('未检测到显著的EOG相关伪迹')
            
        self.progress.setValue(100)
        
    def apply_ica(self):
        if self.raw is None or self.ica is None:
            return
            
        selected_items = []
        for i in range(self.ica_list.count()):
            item = self.ica_list.item(i)
            if item.checkState() == Qt.Checked:
                selected_items.append(i)
                
        if not selected_items:
            self.ica_label.setText('未选择要去除的成分')
            return
            
        exclude = selected_items
        self.ica.apply(self.raw, exclude=exclude)
        
        self.ica_label.setText(f'已去除 {len(exclude)} 个ICA成分')
        self.plot_raw_data()
        
    def compute_inverse_operator(self):
        if self.raw is None:
            self.source_label.setText('请先加载EEG数据')
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        try:
            subjects_dir = mne.datasets.sample.data_path() / 'subjects'
            
            raw = self.raw.copy().pick_types(eeg=True)
            
            if not raw.info.get('dig'):
                montage = mne.channels.make_standard_montage('standard_1020')
                raw.set_montage(montage, match_case=False, on_missing='warn')
            
            fwd = mne.make_forward_solution(raw.info, trans='fsaverage',
                                            src='fsaverage', bem='fsaverage',
                                            subjects_dir=subjects_dir,
                                            verbose=False)
            
            noise_cov = mne.compute_raw_covariance(raw, tmin=0, tmax=None, verbose=False)
            
            self.inverse_operator = make_inverse_operator(raw.info, fwd, noise_cov,
                                                          loose=0.2, depth=0.8,
                                                          verbose=False)
            
            self.source_label.setText('逆算子计算完成')
            self.progress.setValue(100)
            
        except Exception as e:
            self.source_label.setText(f'计算失败: {str(e)[:50]}')
            self.progress.setValue(0)
            
    def apply_source_localization(self):
        if self.raw is None or self.inverse_operator is None:
            self.source_label.setText('请先计算逆算子')
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        method = self.source_method.currentText().lower()
        lambda2 = 1 / 9
        
        raw = self.raw.copy().pick_types(eeg=True)
        
        start_idx = int(raw.info['sfreq'] * 1)
        end_idx = int(raw.info['sfreq'] * 2)
        evoked_data = np.mean(raw[:, start_idx:end_idx][0], axis=1, keepdims=True)
        
        evoked = mne.EvokedArray(evoked_data, raw.info, tmin=0)
        
        self.stc = apply_inverse(evoked, self.inverse_operator, lambda2,
                                method=method, pick_ori=None, verbose=False)
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.source_figure.clear()
        
        ax1 = self.source_figure.add_subplot(211)
        source_data = self.stc.data
        times = np.arange(source_data.shape[1]) / raw.info['sfreq']
        
        for i in range(min(5, source_data.shape[0])):
            ax1.plot(times, source_data[i], alpha=0.6)
        ax1.set_xlabel('时间 (s)')
        ax1.set_ylabel('源强度')
        ax1.set_title(f'脑源活动时间进程 ({method.upper()})')
        
        ax2 = self.source_figure.add_subplot(212)
        mean_activity = np.mean(source_data, axis=1)
        ax2.bar(range(len(mean_activity)), mean_activity)
        ax2.set_xlabel('源索引')
        ax2.set_ylabel('平均源强度')
        ax2.set_title('各源点平均激活强度')
        
        self.source_canvas.draw()
        
        self.source_label.setText(f'源定位完成 ({method.upper()})')
        self.progress.setValue(100)
        
    def extract_epochs(self):
        if self.raw is None:
            return
            
        self.progress.setValue(0)
        QApplication.processEvents()
        
        events = mne.find_events(self.raw, verbose=False)
        if len(events) == 0:
            return
            
        tmin = self.tmin.value()
        tmax = self.tmax.value()
        baseline = (-0.2, 0) if self.baseline_check.isChecked() else None
        
        event_id = None
        if self.event_ids.currentText():
            event_id = int(self.event_ids.currentText())
            events = events[events[:, 2] == event_id]
        
        self.epochs = mne.Epochs(self.raw, events, tmin=tmin, tmax=tmax,
                                 baseline=baseline, preload=True, verbose=False)
        self.evoked = self.epochs.average()
        
        self.progress.setValue(50)
        QApplication.processEvents()
        
        self.epoch_figure.clear()
        ax = self.epoch_figure.add_subplot(111)
        
        times = self.evoked.times
        eeg_indices = [i for i, ch_type in enumerate(self.evoked.get_channel_types()) if ch_type == 'eeg']
        data = self.evoked.data[eeg_indices[:5]] * 1e6
        
        for i in range(len(data)):
            ax.plot(times, data[i], label=self.evoked.ch_names[eeg_indices[i]], alpha=0.8)
        
        ax.axvline(0, color='k', linestyle='--', alpha=0.5, label='刺激 onset')
        ax.axhline(0, color='k', linestyle='-', alpha=0.3)
        if baseline:
            ax.axvspan(-0.2, 0, alpha=0.2, color='gray', label='基线窗口')
        ax.set_xlabel('时间 (s)')
        ax.set_ylabel('振幅 (µV)')
        ax.set_title('事件相关电位 (前5通道)')
        ax.legend(loc='upper right', fontsize=7)
        self.epoch_canvas.draw()
        
        self.progress.setValue(100)
        
    def toggle_neurofeedback(self):
        if self.start_feedback_btn.isChecked():
            self.start_feedback_btn.setText('停止反馈训练')
            self.start_neurofeedback()
        else:
            self.start_feedback_btn.setText('开始反馈训练')
            self.stop_neurofeedback()
            
    def start_neurofeedback(self):
        if self.raw is None and self.lsl_thread is None:
            self.feedback_status.setText('请先加载数据或连接LSL设备')
            self.start_feedback_btn.setChecked(False)
            self.start_feedback_btn.setText('开始反馈训练')
            return
            
        sfreq = self.raw.info['sfreq'] if self.raw else self.lsl_sfreq
        self.neurofeedback = NeuroFeedback(sfreq)
        self.alpha_history.clear()
        self.focus_history.clear()
        self.feedback_status.setText('反馈训练进行中...')
        self.feedback_timer.start(100)
        
    def stop_neurofeedback(self):
        self.feedback_timer.stop()
        self.feedback_status.setText('反馈训练已停止')
        
    def update_feedback(self):
        data_source = None
        
        if len(self.data_buffer) > 100:
            data_source = list(self.data_buffer)
        elif len(self.lsl_buffer) > 100:
            data_source = self.lsl_buffer
        
        if data_source is not None and self.neurofeedback is not None:
            focus_score = self.neurofeedback.update(data_source)
            
            self.focus_lcd.display(int(focus_score))
            self.focus_history.append(focus_score)
            self.alpha_history.append(self.neurofeedback.alpha_power_history[-1] if self.neurofeedback.alpha_power_history else 0)
            
            if len(self.alpha_history) > 10:
                self.alpha_curve.setData(np.array(list(self.alpha_history)))
            
            self.update_gauge(focus_score)
            
            if focus_score > 70:
                self.feedback_message.setText('优秀！保持专注！')
                self.feedback_message.setStyleSheet('color: green; font-weight: bold;')
            elif focus_score > 50:
                self.feedback_message.setText('良好，继续保持')
                self.feedback_message.setStyleSheet('color: blue; font-weight: bold;')
            else:
                self.feedback_message.setText('请放松，专注呼吸...')
                self.feedback_message.setStyleSheet('color: orange; font-weight: bold;')
                
    def update_gauge(self, value):
        self.gauge_figure.clear()
        ax = self.gauge_figure.add_subplot(111, projection='polar')
        
        theta = np.linspace(0, np.pi, 100)
        r = np.ones_like(theta)
        
        norm_value = value / 100
        color_idx = int(norm_value * 255)
        cmap = cm.get_cmap('RdYlGn')
        color = cmap(norm_value)
        
        ax.bar(np.pi/2, 1, width=np.pi * norm_value, bottom=0, color=color, alpha=0.8)
        ax.bar(np.pi/2, 1, width=np.pi, bottom=0, color='lightgray', alpha=0.3)
        
        ax.set_ylim(0, 1)
        ax.set_yticks([])
        ax.set_xticks([0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi])
        ax.set_xticklabels(['0', '25', '50', '75', '100'])
        ax.set_title(f'专注度: {int(value)}', y=1.1)
        
        self.gauge_canvas.draw()
        
    def toggle_realtime(self):
        if self.start_realtime_btn.isChecked():
            self.start_realtime_btn.setText('停止实时显示')
            self.start_realtime_display()
        else:
            self.start_realtime_btn.setText('开始实时显示')
            self.stop_realtime_display()
            
    def start_realtime_display(self):
        if self.raw is None and self.lsl_thread is None:
            self.start_realtime_btn.setChecked(False)
            self.start_realtime_btn.setText('开始实时显示')
            return
            
        self.data_buffer.clear()
        self.display_buffer.clear()
        self.realtime_index = 0
        
        if self.raw is not None:
            channel_name = self.channel_select.currentText()
            channel_idx = self.raw.ch_names.index(channel_name)
            raw_data = self.raw[channel_idx, :][0][0] * 1e6
            
            self.acquisition_thread = DataAcquisitionThread(raw_data, self.raw.info['sfreq'])
            self.acquisition_thread.data_ready.connect(self.buffer_data)
            self.acquisition_thread.start()
        
        self.display_timer.start(20)
        
    def stop_realtime_display(self):
        self.display_timer.stop()
        if self.acquisition_thread is not None:
            self.acquisition_thread.stop()
            self.acquisition_thread = None
            
    def buffer_data(self, data_chunk, time_chunk):
        self.data_buffer.extend(data_chunk)
        
    def swap_buffers_and_display(self):
        current_time = time.time() * 1000
        
        if len(self.data_buffer) > 0:
            self.display_buffer.extend(self.data_buffer)
            self.data_buffer.clear()
        
        if self.raw is not None:
            window_size = int(self.raw.info['sfreq'] * self.window_size_spin.value())
        else:
            window_size = int(250 * self.window_size_spin.value())
            
        display_data = np.array(list(self.display_buffer))[-window_size:]
        display_time = np.arange(len(display_data)) / 250
        
        if len(display_data) > 0:
            self.realtime_curve.setData(display_time, display_data)
            
            if self.last_update_time > 0:
                latency = current_time - self.last_update_time
                self.latency_label.setText(f'延迟: {latency:.1f} ms')
            self.last_update_time = current_time


if __name__ == '__main__':
    app = QApplication(sys.argv)
    toolbox = EEGToolbox()
    toolbox.show()
    sys.exit(app.exec_())
