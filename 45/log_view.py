import wx
import os
from datetime import datetime


class LogView(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self._max_lines = 1000
        self._show_timestamp = True
        self._show_direction = True

        self._create_ui()
        self._bind_events()

    def _create_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.title_label = wx.StaticText(self, label='通信日志')
        header_sizer.Add(self.title_label, 0, wx.ALL, 5)

        self.timestamp_chk = wx.CheckBox(self, label='显示时间戳')
        self.timestamp_chk.SetValue(True)
        header_sizer.Add(self.timestamp_chk, 0, wx.ALL, 5)

        self.clear_btn = wx.Button(self, label='清空')
        self.save_btn = wx.Button(self, label='保存')
        header_sizer.AddStretchSpacer(1)
        header_sizer.Add(self.clear_btn, 0, wx.ALL, 5)
        header_sizer.Add(self.save_btn, 0, wx.ALL, 5)

        sizer.Add(header_sizer, 0, wx.EXPAND)

        self.text_ctrl = wx.TextCtrl(
            self,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL | wx.TE_RICH2
        )
        font = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        self.text_ctrl.SetFont(font)

        sizer.Add(self.text_ctrl, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

    def _bind_events(self):
        self.clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        self.save_btn.Bind(wx.EVT_BUTTON, self._on_save)
        self.timestamp_chk.Bind(wx.EVT_CHECKBOX, self._on_timestamp_toggle)

    def _on_clear(self, event):
        self.clear()

    def _on_save(self, event):
        wildcard = '日志文件 (*.log)|*.log|文本文件 (*.txt)|*.txt|所有文件 (*.*)|*.*'
        default_name = f'log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

        dlg = wx.FileDialog(
            self,
            message='保存日志文件',
            defaultDir=os.getcwd(),
            defaultFile=default_name,
            wildcard=wildcard,
            style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT
        )

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(self.text_ctrl.GetValue())
                wx.MessageBox(f'日志已保存到: {path}', '保存成功', wx.OK | wx.ICON_INFORMATION)
            except Exception as e:
                wx.MessageBox(f'保存失败: {str(e)}', '错误', wx.OK | wx.ICON_ERROR)

        dlg.Destroy()

    def _on_timestamp_toggle(self, event):
        self._show_timestamp = event.IsChecked()

    def log_received(self, timestamp, data):
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = repr(data)

        parts = []
        if self._show_timestamp:
            parts.append(f'[{timestamp}]')
        if self._show_direction:
            parts.append('[RX]')
        parts.append(text)

        full_line = ' '.join(parts) + '\n'
        self._append_colored_text(full_line, wx.Colour(0, 128, 0))

        self._trim_content()
        self._scroll_to_bottom()

    def log_sent(self, timestamp, data):
        try:
            text = data.decode('utf-8', errors='replace')
        except Exception:
            text = repr(data)

        parts = []
        if self._show_timestamp:
            parts.append(f'[{timestamp}]')
        if self._show_direction:
            parts.append('[TX]')
        parts.append(text)

        full_line = ' '.join(parts) + '\n'
        self._append_colored_text(full_line, wx.Colour(0, 0, 255))

        self._trim_content()
        self._scroll_to_bottom()

    def log_info(self, message):
        full_line = f'[INFO] {message}\n'
        self._append_colored_text(full_line, wx.Colour(0, 0, 0))

        self._trim_content()
        self._scroll_to_bottom()

    def log_error(self, message):
        full_line = f'[ERROR] {message}\n'
        self._append_colored_text(full_line, wx.Colour(255, 0, 0))

        self._trim_content()
        self._scroll_to_bottom()

    def _append_colored_text(self, text, color):
        current_pos = self.text_ctrl.GetLastPosition()
        self.text_ctrl.AppendText(text)
        self.text_ctrl.SetStyle(
            current_pos,
            self.text_ctrl.GetLastPosition(),
            wx.TextAttr(color)
        )

    def _trim_content(self):
        lines = self.text_ctrl.GetNumberOfLines()
        if lines > self._max_lines:
            lines_to_remove = lines - self._max_lines
            pos = 0
            for _ in range(lines_to_remove):
                pos = self.text_ctrl.GetLineLength(pos) + pos + 1
            self.text_ctrl.Remove(0, pos)

    def _scroll_to_bottom(self):
        last_pos = self.text_ctrl.GetLastPosition()
        self.text_ctrl.ShowPosition(last_pos)

    def clear(self):
        self.text_ctrl.Clear()

    def set_max_lines(self, max_lines):
        self._max_lines = max_lines

    def get_content(self):
        return self.text_ctrl.GetValue()
