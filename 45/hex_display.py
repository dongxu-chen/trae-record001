import wx


class HexDisplay(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)
        self._data = bytes()
        self._max_lines = 500
        self._line_bytes = 16
        self._pending = []
        self._flush_timer = wx.Timer(self)

        self._create_ui()
        self._bind_events()

    def _create_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        header_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.title_label = wx.StaticText(self, label='十六进制数据')
        header_sizer.Add(self.title_label, 0, wx.ALL, 5)

        self.clear_btn = wx.Button(self, label='清空')
        header_sizer.AddStretchSpacer(1)
        header_sizer.Add(self.clear_btn, 0, wx.ALL, 5)

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
        self.Bind(wx.EVT_TIMER, self._on_flush_timer, self._flush_timer)

    def _on_clear(self, event):
        self.clear()

    def append(self, data, direction='rx'):
        if not isinstance(data, bytes):
            return

        self._data += data
        lines = self._format_hex(data)

        if direction == 'rx':
            color = wx.Colour(0, 128, 0)
            prefix = '[RX] '
        else:
            color = wx.Colour(0, 0, 255)
            prefix = '[TX] '

        text = ''.join(prefix + line + '\n' for line in lines)
        self._pending.append((text, color))

        if not self._flush_timer.IsRunning():
            self._flush_timer.Start(30, wx.TIMER_ONE_SHOT)

    def _on_flush_timer(self, event):
        if not self._pending:
            return

        text = ''.join(item[0] for item in self._pending)
        last_color = self._pending[-1][1]

        start = self.text_ctrl.GetLastPosition()
        self.text_ctrl.AppendText(text)
        end = self.text_ctrl.GetLastPosition()

        if self._should_use_single_style():
            self.text_ctrl.SetStyle(start, end, wx.TextAttr(last_color))

        self._pending = []
        self._trim_content()
        self._scroll_to_bottom()

    def _should_use_single_style(self):
        if not self._pending:
            return False
        first_color = self._pending[0][1]
        return all(item[1] == first_color for item in self._pending)

    def _format_hex(self, data):
        lines = []
        for i in range(0, len(data), self._line_bytes):
            chunk = data[i:i + self._line_bytes]
            hex_part = ' '.join(f'{b:02X}' for b in chunk)
            hex_part = hex_part.ljust(self._line_bytes * 3 - 1)
            ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            offset = i + (len(self._data) - len(data))
            lines.append(f'{offset:08X}  {hex_part}  |{ascii_part}|')
        return lines

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
        if self._flush_timer.IsRunning():
            self._flush_timer.Stop()
        self._pending = []
        self._data = bytes()
        self.text_ctrl.Clear()

    def set_max_lines(self, max_lines):
        self._max_lines = max_lines

    def set_bytes_per_line(self, bytes_per_line):
        self._line_bytes = bytes_per_line
