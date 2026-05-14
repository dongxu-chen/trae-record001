import wx
import matplotlib

matplotlib.use('WXAgg')

from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg as FigureCanvas
from matplotlib.backends.backend_wxagg import NavigationToolbar2WxAgg as NavigationToolbar
from matplotlib.figure import Figure
import numpy as np
import time


class PlotView(wx.Panel):
    def __init__(self, parent):
        super().__init__(parent)

        self._max_points = 200
        self._update_interval = 50
        self._colors = ['#e6194b', '#3cb44b', '#4363d8', '#f58231', '#911eb4', '#46f0f0', '#f032e6', '#bcf60c']

        self._data = {}
        self._lines = {}
        self._update_timer = wx.Timer(self)

        self._figure = Figure(figsize=(4, 3), dpi=96)
        self._canvas = FigureCanvas(self, -1, self._figure)
        self._ax = self._figure.add_subplot(111)

        self._ax.grid(True, alpha=0.3)
        self._ax.set_xlabel('时间 (s)')
        self._ax.set_ylabel('值')
        self._ax.set_title('实时波形')
        self._figure.tight_layout()

        self._create_ui()
        self._bind_events()

    def _create_ui(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.title_label = wx.StaticText(self, label='波形显示')
        toolbar_sizer.Add(self.title_label, 0, wx.ALL | wx.CENTER, 5)

        self.legend_text = wx.StaticText(self, label='曲线: 无')
        toolbar_sizer.Add(self.legend_text, 0, wx.ALL | wx.CENTER, 5)

        toolbar_sizer.AddStretchSpacer(1)

        self.clear_btn = wx.Button(self, label='清空波形')
        toolbar_sizer.Add(self.clear_btn, 0, wx.ALL, 5)

        self.reset_btn = wx.Button(self, label='重置')
        toolbar_sizer.Add(self.reset_btn, 0, wx.ALL, 5)

        sizer.Add(toolbar_sizer, 0, wx.EXPAND)

        toolbar = NavigationToolbar(self._canvas, self)
        toolbar.Realize()
        sizer.Add(toolbar, 0, wx.EXPAND)
        sizer.Add(self._canvas, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

    def _bind_events(self):
        self.clear_btn.Bind(wx.EVT_BUTTON, self._on_clear)
        self.reset_btn.Bind(wx.EVT_BUTTON, self._on_reset)
        self.Bind(wx.EVT_TIMER, self._on_update_timer, self._update_timer)

        self._update_timer.Start(self._update_interval)

    def _on_clear(self, event):
        self.clear()

    def _on_reset(self, event):
        self.reset()

    def _on_update_timer(self, event):
        self._redraw()

    def add_data(self, key, value):
        if key not in self._data:
            self._data[key] = {'t': [], 'v': []}

        now = time.time()
        if not self._data[key]['t']:
            self._data[key]['start'] = now

        t = now - self._data[key]['start']
        self._data[key]['t'].append(t)
        self._data[key]['v'].append(value)

        if len(self._data[key]['t']) > self._max_points:
            self._data[key]['t'] = self._data[key]['t'][-self._max_points:]
            self._data[key]['v'] = self._data[key]['v'][-self._max_points:]

        self._update_legend()

    def clear(self):
        for key in self._data:
            self._data[key]['t'] = []
            self._data[key]['v'] = []
        self._update_legend()

    def reset(self):
        self._data = {}
        self._lines = {}
        self._ax.clear()
        self._ax.grid(True, alpha=0.3)
        self._ax.set_xlabel('时间 (s)')
        self._ax.set_ylabel('值')
        self._ax.set_title('实时波形')
        self._figure.tight_layout()
        self._canvas.draw()
        self._update_legend()

    def _update_legend(self):
        if self._data:
            names = ', '.join(f'{k}' for k in self._data.keys())
            if len(names) > 60:
                names = names[:57] + '...'
            self.legend_text.SetLabel(f'曲线: {names}')
        else:
            self.legend_text.SetLabel('曲线: 无')

    def _redraw(self):
        if not self._data:
            return

        self._ax.clear()
        self._ax.grid(True, alpha=0.3)
        self._ax.set_xlabel('时间 (s)')
        self._ax.set_ylabel('值')
        self._ax.set_title('实时波形')

        all_t = []
        all_v = []
        for idx, (key, series) in enumerate(self._data.items()):
            t = np.array(series['t'])
            v = np.array(series['v'])
            color = self._colors[idx % len(self._colors)]
            if len(t) > 0:
                self._ax.plot(t, v, label=key, color=color, linewidth=1.0)
                all_t.extend(t)
                all_v.extend(v)

        if self._data:
            self._ax.legend(loc='upper left', fontsize=8, ncol=min(4, len(self._data)))

        if all_t:
            x_min, x_max = min(all_t), max(all_t)
            y_min, y_max = min(all_v), max(all_v)
            x_pad = max(0.5, (x_max - x_min) * 0.05) if x_max != x_min else 0.5
            y_pad = max(0.1, (y_max - y_min) * 0.05) if y_max != y_min else 0.1
            self._ax.set_xlim(x_min - x_pad, x_max + x_pad)
            self._ax.set_ylim(y_min - y_pad, y_max + y_pad)

        self._figure.tight_layout()
        self._canvas.draw()

    def set_max_points(self, max_points):
        self._max_points = max_points

    def set_update_interval(self, ms):
        self._update_interval = ms
        if self._update_timer.IsRunning():
            self._update_timer.Stop()
            self._update_timer.Start(self._update_interval)
