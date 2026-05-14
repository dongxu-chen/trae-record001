import wx
import serial
import os
import json

from serial_worker import (
    SerialWorker,
    EVT_SERIAL_DATA,
    EVT_SERIAL_STATUS,
    ScriptDataEvent,
    EVT_SCRIPT_DATA
)
from hex_display import HexDisplay
from log_view import LogView
from script_engine import ScriptEngine


SCRIPT_TEMPLATE = '''-- 示例脚本：定时查询并解析数据
-- send("AT+READ\\n")
-- line = read_line()
-- value = parse_number(match("VAL:([%d.]+)", line))
-- emit("value", value)

print = log

log("脚本引擎已就绪")

for i = 1, 10 do
    sleep(200)
    emit("sine", math.sin(i / 2))
    emit("cos", math.cos(i / 3))
end
'''

SCRIPT_PYTHON_TEMPLATE = '''# 示例脚本（Python 沙盒模式，未安装 Lua 时使用）
from math import sin, cos

log("脚本引擎已就绪")

for i in range(1, 11):
    sleep(200)
    emit("sine", sin(i / 2.0))
    emit("cos", cos(i / 3.0))
'''

DEFAULT_CONFIG = {
    'port': '',
    'baudrate': 115200,
    'parity': '无',
    'stopbit': '1',
    'send_text': '',
    'send_hex': False,
    'append_newline': True,
    'auto_send_text': '',
    'auto_send_hex': False,
    'auto_send_interval': 1000,
    'auto_send_enabled': False,
    'presets': {
        '默认': {
            'baudrate': 115200,
            'parity': '无',
            'stopbit': '1'
        },
        '9600-N-8-1': {
            'baudrate': 9600,
            'parity': '无',
            'stopbit': '1'
        },
        '115200-ESP': {
            'baudrate': 115200,
            'parity': '无',
            'stopbit': '1'
        }
    }
}


class SerialPortFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title='串口调试助手 - 增强版', size=(1400, 900))

        self.serial_worker = SerialWorker(self)
        self._connected = False

        self._config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        self._config = self._load_config()

        self._create_ui()
        self._init_script_engine()
        self._bind_events()
        self._refresh_ports()
        self._load_config_to_ui()
        self._set_ui_state(False)

        self.Centre()
        self.Show()

    def _create_ui(self):
        panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        main_sizer.Add(self._create_top_panel(panel), 0, wx.EXPAND | wx.ALL, 5)

        self._notebook = wx.Notebook(panel)

        data_page = wx.Panel(self._notebook)
        data_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.hex_display = HexDisplay(data_page)
        self.log_view = LogView(data_page)
        data_sizer.Add(self.hex_display, 1, wx.EXPAND)
        data_sizer.Add(self.log_view, 1, wx.EXPAND)
        data_page.SetSizer(data_sizer)
        self._notebook.AddPage(data_page, '数据视图')

        plot_page = wx.Panel(self._notebook)
        plot_sizer = wx.BoxSizer(wx.VERTICAL)
        try:
            from plot_view import PlotView
            self.plot_view = PlotView(plot_page)
            plot_sizer.Add(self.plot_view, 1, wx.EXPAND)
        except Exception as e:
            self.plot_view = None
            err_label = wx.StaticText(plot_page, label=f'波形显示不可用: {e}\n请安装: pip install matplotlib numpy')
            err_label.SetForegroundColour(wx.Colour(200, 50, 50))
            plot_sizer.Add(err_label, 1, wx.ALL | wx.EXPAND, 20)
        plot_page.SetSizer(plot_sizer)
        self._notebook.AddPage(plot_page, '波形显示')

        script_page = wx.Panel(self._notebook)
        script_sizer = wx.BoxSizer(wx.VERTICAL)

        script_toolbar = wx.BoxSizer(wx.HORIZONTAL)
        script_toolbar.Add(wx.StaticText(script_page, label='脚本引擎'), 0, wx.ALL | wx.CENTER, 5)
        self.script_status = wx.StaticText(script_page, label='| 状态: 未运行')
        script_toolbar.Add(self.script_status, 0, wx.ALL | wx.CENTER, 5)
        script_toolbar.AddStretchSpacer(1)
        self.script_run_btn = wx.Button(script_page, label='运行脚本')
        self.script_stop_btn = wx.Button(script_page, label='停止脚本')
        self.script_save_btn = wx.Button(script_page, label='保存脚本')
        self.script_load_btn = wx.Button(script_page, label='加载脚本')
        script_toolbar.Add(self.script_run_btn, 0, wx.ALL, 5)
        script_toolbar.Add(self.script_stop_btn, 0, wx.ALL, 5)
        script_toolbar.Add(self.script_save_btn, 0, wx.ALL, 5)
        script_toolbar.Add(self.script_load_btn, 0, wx.ALL, 5)

        script_sizer.Add(script_toolbar, 0, wx.EXPAND)

        self.script_text = wx.TextCtrl(
            script_page,
            style=wx.TE_MULTILINE | wx.HSCROLL | wx.TE_RICH2
        )
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.script_text.SetFont(font)
        script_sizer.Add(self.script_text, 2, wx.EXPAND | wx.ALL, 5)

        script_log_label = wx.StaticText(script_page, label='脚本输出:')
        script_sizer.Add(script_log_label, 0, wx.ALL, 5)

        self.script_output = wx.TextCtrl(
            script_page,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
        )
        self.script_output.SetFont(font)
        script_sizer.Add(self.script_output, 1, wx.EXPAND | wx.ALL, 5)

        script_page.SetSizer(script_sizer)
        self._notebook.AddPage(script_page, '脚本引擎')

        main_sizer.Add(self._notebook, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self._create_send_panel(panel), 0, wx.EXPAND | wx.ALL, 5)

        panel.SetSizer(main_sizer)

    def _init_script_engine(self):
        try:
            self.script_text.SetValue(SCRIPT_TEMPLATE)
        except Exception:
            self.script_text.SetValue(SCRIPT_PYTHON_TEMPLATE)

        def on_data(key, value):
            wx.CallAfter(self._on_script_data_local, key, value)

        def on_log(msg):
            wx.CallAfter(self._on_script_log_local, msg)

        def on_error(msg):
            wx.CallAfter(self._on_script_error_local, msg)

        self.script_engine = ScriptEngine(
            serial_worker=self.serial_worker,
            on_data=on_data,
            on_log=on_log,
            on_error=on_error
        )

    def _create_top_panel(self, parent):
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        port_box = wx.StaticBox(panel, label='端口设置')
        port_sizer = wx.StaticBoxSizer(port_box, wx.HORIZONTAL)

        port_sizer.Add(wx.StaticText(panel, label='预设:'), 0, wx.ALL | wx.CENTER, 5)
        self.preset_combo = wx.ComboBox(panel, size=(120, -1), style=wx.CB_READONLY)
        port_sizer.Add(self.preset_combo, 0, wx.ALL, 5)

        self.load_preset_btn = wx.Button(panel, label='应用预设')
        port_sizer.Add(self.load_preset_btn, 0, wx.ALL, 5)

        port_sizer.Add(wx.StaticText(panel, label='串口:'), 0, wx.ALL | wx.CENTER, 5)
        self.port_combo = wx.ComboBox(panel, size=(100, -1), style=wx.CB_READONLY)
        port_sizer.Add(self.port_combo, 0, wx.ALL, 5)

        self.refresh_btn = wx.Button(panel, label='刷新')
        port_sizer.Add(self.refresh_btn, 0, wx.ALL, 5)

        port_sizer.Add(wx.StaticText(panel, label='波特率:'), 0, wx.ALL | wx.CENTER, 5)
        self.baud_combo = wx.ComboBox(panel, size=(100, -1), style=wx.CB_READONLY)
        self.baud_combo.SetItems([str(b) for b in SerialWorker.list_baudrates()])
        port_sizer.Add(self.baud_combo, 0, wx.ALL, 5)

        port_sizer.Add(wx.StaticText(panel, label='校验位:'), 0, wx.ALL | wx.CENTER, 5)
        self.parity_combo = wx.ComboBox(panel, size=(70, -1), style=wx.CB_READONLY)
        parities = SerialWorker.list_parities()
        self.parity_labels = [p[0] for p in parities]
        self.parity_values = [p[1] for p in parities]
        self.parity_combo.SetItems(self.parity_labels)
        port_sizer.Add(self.parity_combo, 0, wx.ALL, 5)

        port_sizer.Add(wx.StaticText(panel, label='停止位:'), 0, wx.ALL | wx.CENTER, 5)
        self.stopbit_combo = wx.ComboBox(panel, size=(60, -1), style=wx.CB_READONLY)
        stopbits = SerialWorker.list_stopbits()
        self.stopbit_labels = [s[0] for s in stopbits]
        self.stopbit_values = [s[1] for s in stopbits]
        self.stopbit_combo.SetItems(self.stopbit_labels)
        port_sizer.Add(self.stopbit_combo, 0, wx.ALL, 5)

        sizer.Add(port_sizer, 0, wx.ALL, 5)

        self.connect_btn = wx.Button(panel, label='打开串口', size=(100, 40))
        sizer.Add(self.connect_btn, 0, wx.ALL | wx.EXPAND, 5)

        self.status_text = wx.StaticText(panel, label='状态: 未连接', style=wx.ALIGN_CENTER)
        self.status_text.SetFont(wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        self.status_text.SetForegroundColour(wx.Colour(128, 128, 128))
        sizer.AddStretchSpacer(1)
        sizer.Add(self.status_text, 0, wx.ALL | wx.CENTER, 10)

        return panel

    def _create_send_panel(self, parent):
        panel = wx.Panel(parent)
        sizer = wx.BoxSizer(wx.VERTICAL)

        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        header_sizer.Add(wx.StaticText(panel, label='发送区'), 0, wx.ALL, 5)

        self.send_hex_chk = wx.CheckBox(panel, label='十六进制发送')
        header_sizer.Add(self.send_hex_chk, 0, wx.ALL, 5)

        self.newline_chk = wx.CheckBox(panel, label='追加换行')
        header_sizer.Add(self.newline_chk, 0, wx.ALL, 5)

        header_sizer.AddStretchSpacer(1)

        header_sizer.Add(wx.StaticText(panel, label='| 定时发送:'), 0, wx.ALL | wx.CENTER, 5)
        self.auto_send_chk = wx.CheckBox(panel, label='启用')
        header_sizer.Add(self.auto_send_chk, 0, wx.ALL, 5)

        header_sizer.Add(wx.StaticText(panel, label='周期(ms):'), 0, wx.ALL | wx.CENTER, 5)
        self.auto_send_interval = wx.TextCtrl(panel, value='1000', size=(60, -1))
        header_sizer.Add(self.auto_send_interval, 0, wx.ALL, 5)

        self.auto_send_hex_chk = wx.CheckBox(panel, label='Hex')
        header_sizer.Add(self.auto_send_hex_chk, 0, wx.ALL, 5)

        self.auto_send_text = wx.TextCtrl(panel, value='', size=(160, -1))
        header_sizer.Add(self.auto_send_text, 0, wx.ALL, 5)

        header_sizer.AddStretchSpacer(1)

        self.clear_send_btn = wx.Button(panel, label='清空发送')
        header_sizer.Add(self.clear_send_btn, 0, wx.ALL, 5)

        self.send_btn = wx.Button(panel, label='发送', size=(80, 30))
        header_sizer.Add(self.send_btn, 0, wx.ALL, 5)

        sizer.Add(header_sizer, 0, wx.EXPAND)

        self.send_text = wx.TextCtrl(
            panel,
            style=wx.TE_MULTILINE | wx.HSCROLL | wx.TE_PROCESS_ENTER
        )
        font = wx.Font(10, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.send_text.SetFont(font)
        self.send_text.SetMinSize((-1, 80))
        sizer.Add(self.send_text, 1, wx.EXPAND | wx.ALL, 5)

        self.manual_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_manual_timer, self.manual_timer)

        return panel

    def _bind_events(self):
        self.refresh_btn.Bind(wx.EVT_BUTTON, self._on_refresh)
        self.connect_btn.Bind(wx.EVT_BUTTON, self._on_connect)
        self.send_btn.Bind(wx.EVT_BUTTON, self._on_send)
        self.clear_send_btn.Bind(wx.EVT_BUTTON, self._on_clear_send)
        self.auto_send_chk.Bind(wx.EVT_CHECKBOX, self._on_auto_send_toggle)

        self.load_preset_btn.Bind(wx.EVT_BUTTON, self._on_load_preset)

        self.script_run_btn.Bind(wx.EVT_BUTTON, self._on_script_run)
        self.script_stop_btn.Bind(wx.EVT_BUTTON, self._on_script_stop)
        self.script_save_btn.Bind(wx.EVT_BUTTON, self._on_script_save)
        self.script_load_btn.Bind(wx.EVT_BUTTON, self._on_script_load)

        self.Bind(wx.EVT_CLOSE, self._on_close)

        self.Bind(EVT_SERIAL_DATA, self._on_serial_data)
        self.Bind(EVT_SERIAL_STATUS, self._on_serial_status)
        self.Bind(EVT_SCRIPT_DATA, self._on_script_data_evt)

    def _refresh_ports(self):
        ports = SerialWorker.list_ports()
        self.port_combo.SetItems(ports)
        if ports:
            if self._config.get('port') in ports:
                self.port_combo.SetValue(self._config['port'])
            else:
                self.port_combo.SetValue(ports[0])

        self.preset_combo.SetItems(list(self._config.get('presets', DEFAULT_CONFIG['presets']).keys()))

    def _set_ui_state(self, connected):
        self._connected = connected

        self.port_combo.Enable(not connected)
        self.baud_combo.Enable(not connected)
        self.parity_combo.Enable(not connected)
        self.stopbit_combo.Enable(not connected)
        self.refresh_btn.Enable(not connected)
        self.load_preset_btn.Enable(not connected)
        self.preset_combo.Enable(not connected)

        self.send_btn.Enable(connected)
        self.auto_send_chk.Enable(connected)
        self.auto_send_interval.Enable(connected and self.auto_send_chk.GetValue())
        self.auto_send_text.Enable(connected and self.auto_send_chk.GetValue())
        self.auto_send_hex_chk.Enable(connected and self.auto_send_chk.GetValue())

        if connected:
            self.connect_btn.SetLabel('关闭串口')
            self.connect_btn.SetBackgroundColour(wx.Colour(220, 50, 50))
            self.connect_btn.SetForegroundColour(wx.Colour(255, 255, 255))
            self.status_text.SetLabel('状态: 已连接')
            self.status_text.SetForegroundColour(wx.Colour(0, 180, 0))
        else:
            self.connect_btn.SetLabel('打开串口')
            self.connect_btn.SetBackgroundColour(wx.NullColour)
            self.connect_btn.SetForegroundColour(wx.NullColour)
            self.status_text.SetLabel('状态: 未连接')
            self.status_text.SetForegroundColour(wx.Colour(128, 128, 128))

    def _on_refresh(self, event):
        self._refresh_ports()
        self.log_view.log_info('已刷新端口列表')

    def _on_load_preset(self, event):
        name = self.preset_combo.GetValue()
        if not name:
            return
        presets = self._config.get('presets', DEFAULT_CONFIG['presets'])
        preset = presets.get(name)
        if not preset:
            return

        if 'baudrate' in preset:
            self.baud_combo.SetValue(str(preset['baudrate']))
        if 'parity' in preset:
            self.parity_combo.SetValue(preset['parity'])
        if 'stopbit' in preset:
            self.stopbit_combo.SetValue(preset['stopbit'])

        self.log_view.log_info(f'已应用预设: {name}')

    def _on_connect(self, event):
        if self._connected:
            self.serial_worker.set_auto_send(False)
            self.auto_send_chk.SetValue(False)
            success, msg = self.serial_worker.close_port()
            if success:
                self._set_ui_state(False)
            self.log_view.log_info(msg)
        else:
            if not self.port_combo.GetValue():
                wx.MessageBox('请选择串口', '错误', wx.OK | wx.ICON_ERROR)
                return

            try:
                port = self.port_combo.GetValue()
                baudrate = int(self.baud_combo.GetValue())
                parity = self.parity_values[self.parity_labels.index(self.parity_combo.GetValue())]
                stopbits = self.stopbit_values[self.stopbit_labels.index(self.stopbit_combo.GetValue())]
                bytesize = serial.EIGHTBITS

                success, msg = self.serial_worker.open_port(
                    port=port,
                    baudrate=baudrate,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits
                )

                if success:
                    self._set_ui_state(True)
                    self._save_ui_to_config()
                self.log_view.log_info(msg)

                if not success:
                    wx.MessageBox(msg, '连接失败', wx.OK | wx.ICON_ERROR)
            except Exception as e:
                wx.MessageBox(f'参数错误: {str(e)}', '错误', wx.OK | wx.ICON_ERROR)

    def _on_send(self, event):
        self._do_send()

    def _do_send(self):
        data = self.send_text.GetValue()
        if not data:
            return

        if self.newline_chk.GetValue() and not data.endswith('\n'):
            data += '\n'

        is_hex = self.send_hex_chk.GetValue()
        success, msg = self.serial_worker.send_data(data, is_hex)

        if not success:
            self.log_view.log_error(msg)
            wx.MessageBox(msg, '发送失败', wx.OK | wx.ICON_ERROR)
        else:
            self._save_ui_to_config()

    def _on_clear_send(self, event):
        self.send_text.Clear()

    def _on_manual_timer(self, event):
        self._do_send()

    def _on_auto_send_toggle(self, event):
        enabled = event.IsChecked()
        if not enabled:
            self.serial_worker.set_auto_send(False)
            self.auto_send_interval.Enable(True)
            self.auto_send_text.Enable(True)
            self.auto_send_hex_chk.Enable(True)
            self.log_view.log_info('定时发送已停止')
            return

        text = self.auto_send_text.GetValue()
        if not text:
            self.auto_send_chk.SetValue(False)
            wx.MessageBox('请输入定时发送内容', '错误', wx.OK | wx.ICON_ERROR)
            return

        try:
            interval = int(self.auto_send_interval.GetValue())
        except ValueError:
            self.auto_send_chk.SetValue(False)
            wx.MessageBox('请输入有效的周期值', '错误', wx.OK | wx.ICON_ERROR)
            return

        is_hex = self.auto_send_hex_chk.GetValue()
        success, msg = self.serial_worker.set_auto_send(
            enabled=True,
            data=text,
            interval_ms=max(10, interval),
            is_hex=is_hex
        )

        if success:
            self.auto_send_interval.Enable(False)
            self.auto_send_text.Enable(False)
            self.auto_send_hex_chk.Enable(False)
            self.log_view.log_info(msg)
            self._save_ui_to_config()
        else:
            self.auto_send_chk.SetValue(False)
            wx.MessageBox(msg, '定时发送启动失败', wx.OK | wx.ICON_ERROR)

    def _on_script_run(self, event):
        if self.script_engine.is_running():
            return
        self.script_output.Clear()
        self.script_status.SetLabel('| 状态: 运行中')
        self.script_status.SetForegroundColour(wx.Colour(0, 140, 0))
        self.script_engine.run(self.script_text.GetValue())

    def _on_script_stop(self, event):
        self.script_engine.stop()
        self.script_status.SetLabel('| 状态: 已停止')
        self.script_status.SetForegroundColour(wx.Colour(180, 80, 0))
        self._append_script_log('[系统] 脚本已停止\n')

    def _on_script_save(self, event):
        dlg = wx.FileDialog(
            self,
            message='保存脚本',
            defaultDir=os.getcwd(),
            defaultFile='script.lua',
            wildcard='Lua 脚本 (*.lua)|*.lua|Python 脚本 (*.py)|*.py|所有文件 (*.*)|*.*',
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )
        if dlg.ShowModal() == wx.ID_OK:
            try:
                with open(dlg.GetPath(), 'w', encoding='utf-8') as f:
                    f.write(self.script_text.GetValue())
                wx.MessageBox('脚本已保存', '成功', wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f'保存失败: {e}', '错误', wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def _on_script_load(self, event):
        dlg = wx.FileDialog(
            self,
            message='加载脚本',
            defaultDir=os.getcwd(),
            wildcard='脚本文件 (*.lua;*.py)|*.lua;*.py|所有文件 (*.*)|*.*',
            style=wx.FD_OPEN
        )
        if dlg.ShowModal() == wx.ID_OK:
            try:
                with open(dlg.GetPath(), 'r', encoding='utf-8') as f:
                    self.script_text.SetValue(f.read())
                wx.MessageBox('脚本已加载', '成功', wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f'加载失败: {e}', '错误', wx.OK | wx.ICON_ERROR)
        dlg.Destroy()

    def _on_script_data_local(self, key, value):
        if self.plot_view:
            self.plot_view.add_data(key, float(value))

    def _on_script_data_evt(self, event):
        key = getattr(event, 'key', '')
        value = getattr(event, 'value', 0)
        if self.plot_view and key:
            self.plot_view.add_data(key, float(value))

    def _on_script_log_local(self, msg):
        self._append_script_log(f'[输出] {msg}\n')

    def _on_script_error_local(self, msg):
        self._append_script_log(f'[错误] {msg}\n')
        self.script_status.SetLabel('| 状态: 错误')
        self.script_status.SetForegroundColour(wx.Colour(180, 0, 0))

    def _append_script_log(self, text):
        self.script_output.AppendText(text)
        last = self.script_output.GetLastPosition()
        self.script_output.ShowPosition(last)

    def _on_close(self, event):
        if self.serial_worker.is_connected():
            self.serial_worker.set_auto_send(False)
            self.serial_worker.close_port()

        if self.script_engine.is_running():
            self.script_engine.stop()

        self._save_ui_to_config()
        self._save_config()

        event.Skip()

    def _on_serial_status(self, event):
        status = getattr(event, 'status', '')
        if status == 'connected':
            port = getattr(event, 'port', '')
            baudrate = getattr(event, 'baudrate', 0)
            self.log_view.log_info(f'串口已连接: {port} @ {baudrate} bps')
        elif status == 'disconnected':
            self._set_ui_state(False)
            self.log_view.log_info('串口已断开')
        elif status == 'error':
            message = getattr(event, 'message', '')
            self._set_ui_state(False)
            self.log_view.log_error(f'串口错误: {message}')

    def _on_serial_data(self, event):
        direction = getattr(event, 'direction', 'rx')
        timestamp = getattr(event, 'timestamp', '')
        data = getattr(event, 'data', bytes())

        if direction == 'rx':
            self.script_engine.feed_rx(data)
            self.hex_display.append(data, 'rx')
            self.log_view.log_received(timestamp, data)
        else:
            self.hex_display.append(data, 'tx')
            self.log_view.log_sent(timestamp, data)

    def _load_config(self):
        if os.path.exists(self._config_path):
            try:
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    merged = dict(DEFAULT_CONFIG)
                    merged.update(cfg)
                    if 'presets' not in merged:
                        merged['presets'] = DEFAULT_CONFIG['presets']
                    return merged
            except Exception:
                pass
        return dict(DEFAULT_CONFIG)

    def _save_config(self):
        try:
            with open(self._config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _load_config_to_ui(self):
        cfg = self._config
        if 'baudrate' in cfg:
            self.baud_combo.SetValue(str(cfg['baudrate']))
        if 'parity' in cfg and cfg['parity'] in self.parity_labels:
            self.parity_combo.SetValue(cfg['parity'])
        if 'stopbit' in cfg and cfg['stopbit'] in self.stopbit_labels:
            self.stopbit_combo.SetValue(cfg['stopbit'])
        if 'send_text' in cfg:
            self.send_text.SetValue(cfg['send_text'])
        if 'send_hex' in cfg:
            self.send_hex_chk.SetValue(cfg['send_hex'])
        if 'append_newline' in cfg:
            self.newline_chk.SetValue(cfg['append_newline'])
        if 'auto_send_text' in cfg:
            self.auto_send_text.SetValue(cfg['auto_send_text'])
        if 'auto_send_hex' in cfg:
            self.auto_send_hex_chk.SetValue(cfg['auto_send_hex'])
        if 'auto_send_interval' in cfg:
            self.auto_send_interval.SetValue(str(cfg['auto_send_interval']))
        if 'auto_send_enabled' in cfg:
            self.auto_send_chk.SetValue(False)

    def _save_ui_to_config(self):
        try:
            self._config['port'] = self.port_combo.GetValue()
            self._config['baudrate'] = int(self.baud_combo.GetValue())
            self._config['parity'] = self.parity_combo.GetValue()
            self._config['stopbit'] = self.stopbit_combo.GetValue()
            self._config['send_text'] = self.send_text.GetValue()
            self._config['send_hex'] = self.send_hex_chk.GetValue()
            self._config['append_newline'] = self.newline_chk.GetValue()
            self._config['auto_send_text'] = self.auto_send_text.GetValue()
            self._config['auto_send_hex'] = self.auto_send_hex_chk.GetValue()
            try:
                self._config['auto_send_interval'] = int(self.auto_send_interval.GetValue())
            except ValueError:
                self._config['auto_send_interval'] = 1000
            self._config['auto_send_enabled'] = self.auto_send_chk.GetValue()
        except Exception:
            pass


if __name__ == '__main__':
    app = wx.App(False)
    frame = SerialPortFrame()
    app.MainLoop()
