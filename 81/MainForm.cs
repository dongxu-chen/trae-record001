using System.Diagnostics;
using System.Net.Http;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public partial class MainForm : Form
{
    private readonly Config _config;
    private readonly LiveChecker _checker;
    private readonly Notification _notification;
    private readonly Database _database;
    private readonly AutoRecorder _autoRecorder;
    private readonly HttpClient _httpClient;
    private readonly Dictionary<long, DanmakuRecorder> _danmakuRecorders = new();
    private readonly object _recorderLock = new();
    private ContextMenuStrip? _trayMenu;

    private ListView? listViewRooms;
    private ColumnHeader? colStatus;
    private ColumnHeader? colUName;
    private ColumnHeader? colTitle;
    private ColumnHeader? colArea;
    private ColumnHeader? colLastLive;
    private ColumnHeader? colRecord;
    private Panel? panelTop;
    private TextBox? txtRoomId;
    private Label? lblRoomId;
    private Button? btnAdd;
    private Button? btnRefresh;
    private Button? btnOpenRoom;
    private Button? btnRemove;
    private Button? btnStats;
    private Button? btnToggleRecord;
    private Panel? panelBottom;
    private Label? lblStatus;
    private SplitContainer? splitContainer;
    private RichTextBox? txtDanmaku;
    private ListBox? lstRecentDanmaku;
    private ToolStripMenuItem? miAutoRecord;
    private ToolStripMenuItem? miAutoDanmaku;

    private bool _enableAutoDanmaku = true;

    public MainForm()
    {
        _config = Config.Load();
        _database = new Database();
        _httpClient = new HttpClient();
        _checker = new LiveChecker(_config);
        _notification = new Notification(this);
        _autoRecorder = new AutoRecorder(_database);

        InitializeMainForm();
        SetupEvents();
        SetupTrayMenu();
    }

    private void InitializeMainForm()
    {
        this.AutoScaleDimensions = new SizeF(7F, 17F);
        this.AutoScaleMode = AutoScaleMode.Font;
        this.ClientSize = new Size(1100, 650);
        this.MinimumSize = new Size(900, 500);
        this.Name = "MainForm";
        this.StartPosition = FormStartPosition.CenterScreen;
        this.Text = "B站直播监控";
        this.FormClosing += MainForm_FormClosing;
        this.Load += MainForm_Load;
        this.Resize += MainForm_Resize;

        splitContainer = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Horizontal,
            SplitterDistance = 400,
            FixedPanel = FixedPanel.Panel2,
            Panel2MinSize = 150
        };

        panelTop = new Panel
        {
            Dock = DockStyle.Top,
            Height = 60
        };

        panelBottom = new Panel
        {
            Dock = DockStyle.Bottom,
            Height = 30
        };

        lblRoomId = new Label
        {
            Text = "房间号：",
            Location = new Point(12, 21),
            AutoSize = true
        };

        txtRoomId = new TextBox
        {
            Location = new Point(88, 18),
            Width = 180
        };

        btnAdd = new Button
        {
            Text = "添加关注",
            Location = new Point(280, 15),
            Width = 85,
            Height = 30
        };
        btnAdd.Click += BtnAdd_Click;

        btnRefresh = new Button
        {
            Text = "刷新",
            Location = new Point(370, 15),
            Width = 65,
            Height = 30
        };
        btnRefresh.Click += BtnRefresh_Click;

        btnOpenRoom = new Button
        {
            Text = "打开",
            Location = new Point(440, 15),
            Width = 65,
            Height = 30
        };
        btnOpenRoom.Click += BtnOpenRoom_Click;

        btnRemove = new Button
        {
            Text = "移除",
            Location = new Point(510, 15),
            Width = 65,
            Height = 30
        };
        btnRemove.Click += BtnRemove_Click;

        btnStats = new Button
        {
            Text = "礼物统计",
            Location = new Point(580, 15),
            Width = 75,
            Height = 30
        };
        btnStats.Click += BtnStats_Click;

        btnToggleRecord = new Button
        {
            Text = "录制",
            Location = new Point(660, 15),
            Width = 65,
            Height = 30
        };
        btnToggleRecord.Click += BtnToggleRecord_Click;

        listViewRooms = new ListView
        {
            Dock = DockStyle.Fill,
            View = View.Details,
            FullRowSelect = true,
            GridLines = true,
            MultiSelect = false
        };
        listViewRooms.DoubleClick += ListViewRooms_DoubleClick;

        colStatus = new ColumnHeader { Text = "状态", Width = 90 };
        colUName = new ColumnHeader { Text = "主播", Width = 100 };
        colTitle = new ColumnHeader { Text = "标题", Width = 280 };
        colArea = new ColumnHeader { Text = "分区", Width = 120 };
        colLastLive = new ColumnHeader { Text = "上次直播", Width = 140 };
        colRecord = new ColumnHeader { Text = "录制", Width = 80 };

        listViewRooms.Columns.AddRange(new[]
        {
            colStatus, colUName, colTitle, colArea, colLastLive, colRecord
        });

        lstRecentDanmaku = new ListBox
        {
            Dock = DockStyle.Fill,
            IntegralHeight = false,
            HorizontalScrollbar = true
        };

        panelTop.Controls.AddRange(new Control[]
        {
            lblRoomId, txtRoomId, btnAdd, btnRefresh, btnOpenRoom, btnRemove, btnStats, btnToggleRecord
        });

        splitContainer.Panel1.Controls.Add(listViewRooms);
        splitContainer.Panel2.Controls.Add(lstRecentDanmaku);

        lblStatus = new Label
        {
            Text = "就绪",
            Location = new Point(12, 7),
            AutoSize = true
        };
        panelBottom.Controls.Add(lblStatus);

        this.Controls.Add(splitContainer);
        this.Controls.Add(panelBottom);
        this.Controls.Add(panelTop);
    }

    private void SetupEvents()
    {
        _checker.RoomWentLive += Checker_RoomWentLive;
        _checker.RoomStatusChanged += Checker_RoomStatusChanged;
        _checker.CheckCompleted += Checker_CheckCompleted;
        _notification.Click += Notification_Click;

        _autoRecorder.RecordingStarted += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() =>
                {
                    SetStatus($"开始录制：房间 {e.RoomId}");
                    RefreshRoomList();
                }));
                return;
            }
            SetStatus($"开始录制：房间 {e.RoomId}");
            RefreshRoomList();
        };

        _autoRecorder.RecordingStopped += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() =>
                {
                    SetStatus($"录制完成：房间 {e.RoomId}");
                    RefreshRoomList();
                }));
                return;
            }
            SetStatus($"录制完成：房间 {e.RoomId}");
            RefreshRoomList();
        };

        _autoRecorder.RecordingError += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() =>
                {
                    SetStatus($"录制错误：{e.Error}");
                }));
                return;
            }
            SetStatus($"录制错误：{e.Error}");
        };
    }

    private void SetupTrayMenu()
    {
        _trayMenu = new ContextMenuStrip();

        var showItem = new ToolStripMenuItem("显示主窗口");
        showItem.Click += (s, e) => ShowWindow();
        _trayMenu.Items.Add(showItem);

        _trayMenu.Items.Add(new ToolStripSeparator());

        miAutoDanmaku = new ToolStripMenuItem("自动录制弹幕")
        {
            Checked = _enableAutoDanmaku,
            CheckOnClick = true
        };
        miAutoDanmaku.CheckedChanged += (s, e) =>
        {
            _enableAutoDanmaku = miAutoDanmaku.Checked;
        };
        _trayMenu.Items.Add(miAutoDanmaku);

        miAutoRecord = new ToolStripMenuItem("自动录屏")
        {
            Checked = _autoRecorder.Enabled,
            CheckOnClick = true
        };
        miAutoRecord.CheckedChanged += (s, e) =>
        {
            _autoRecorder.Enabled = miAutoRecord.Checked;
            if (!_autoRecorder.Enabled)
            {
                _autoRecorder.StopAll();
            }
            RefreshRoomList();
        };
        _trayMenu.Items.Add(miAutoRecord);

        _trayMenu.Items.Add(new ToolStripSeparator());

        var settingsItem = new ToolStripMenuItem("录屏设置...");
        settingsItem.Click += (s, e) => ShowRecordSettings();
        _trayMenu.Items.Add(settingsItem);

        _trayMenu.Items.Add(new ToolStripSeparator());

        var exitItem = new ToolStripMenuItem("退出");
        exitItem.Click += (s, e) => ExitApplication();
        _trayMenu.Items.Add(exitItem);

        _notification.SetContextMenu(_trayMenu);
    }

    private void MainForm_Load(object sender, EventArgs e)
    {
        RefreshRoomList();
        _checker.Start();
        SetStatus("监控已启动");
    }

    private async void Checker_RoomWentLive(object? sender, LiveRoom room)
    {
        if (InvokeRequired)
        {
            Invoke(new Action(() => Checker_RoomWentLive(sender, room)));
            return;
        }

        if (_config.EnableNotification)
        {
            _notification.ShowLiveNotification(room);
        }

        if (_enableAutoDanmaku)
        {
            await StartDanmakuRecorderAsync(room);
        }

        if (_autoRecorder.Enabled)
        {
            _autoRecorder.StartRecording(room);
        }

        RefreshRoomList();
        SetStatus($"{room.UName} 开播了！");
    }

    private void Checker_RoomStatusChanged(object? sender, LiveRoom room)
    {
        if (InvokeRequired)
        {
            Invoke(new Action(() => Checker_RoomStatusChanged(sender, room)));
            return;
        }

        if (room.LiveStatus != 1)
        {
            StopDanmakuRecorder(room.RoomId);
            _autoRecorder.StopRecording(room.RoomId);
        }

        RefreshRoomList();
    }

    private void Checker_CheckCompleted(object? sender, EventArgs e)
    {
        if (InvokeRequired)
        {
            Invoke(new Action(() => Checker_CheckCompleted(sender, e)));
            return;
        }

        var liveCount = _config.FollowedRooms.Count(r => r.LiveStatus == 1);
        SetStatus($"已检查 {_config.FollowedRooms.Count} 个直播间，{liveCount} 个正在直播");
    }

    private void Notification_Click(object? sender, EventArgs e)
    {
        ShowWindow();
    }

    private void ShowWindow()
    {
        Show();
        WindowState = FormWindowState.Normal;
        Activate();
        BringToFront();
    }

    private void MainForm_Resize(object sender, EventArgs e)
    {
        if (WindowState == FormWindowState.Minimized)
        {
            Hide();
        }
    }

    private void MainForm_FormClosing(object sender, FormClosingEventArgs e)
    {
        if (e.CloseReason == CloseReason.UserClosing)
        {
            e.Cancel = true;
            Hide();
            _notification.ShowMessage("B站直播监控", "程序已最小化到托盘，仍在后台运行");
        }
    }

    private void ExitApplication()
    {
        _checker.Stop();
        _autoRecorder.StopAll();
        StopAllDanmakuRecorders();
        _notification.Dispose();
        _database.Dispose();
        _httpClient.Dispose();
        Environment.Exit(0);
    }

    private async Task StartDanmakuRecorderAsync(LiveRoom room)
    {
        lock (_recorderLock)
        {
            if (_danmakuRecorders.ContainsKey(room.RoomId))
            {
                return;
            }
        }

        var recorder = new DanmakuRecorder(room.RoomId, _database, _httpClient);
        recorder.DanmakuReceived += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => AddDanmakuToList(e)));
                return;
            }
            AddDanmakuToList(e);
        };

        recorder.GiftReceived += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => AddGiftToList(e)));
                return;
            }
            AddGiftToList(e);
        };

        recorder.SuperChatReceived += (s, e) =>
        {
            if (InvokeRequired)
            {
                Invoke(new Action(() => AddSuperChatToList(e)));
                return;
            }
            AddSuperChatToList(e);
        };

        var started = await recorder.StartRecordingAsync(room);
        if (started)
        {
            lock (_recorderLock)
            {
                _danmakuRecorders[room.RoomId] = recorder;
            }
        }
    }

    private void StopDanmakuRecorder(long roomId)
    {
        lock (_recorderLock)
        {
            if (_danmakuRecorders.TryGetValue(roomId, out var recorder))
            {
                recorder.StopRecording();
                recorder.Dispose();
                _danmakuRecorders.Remove(roomId);
            }
        }
    }

    private void StopAllDanmakuRecorders()
    {
        lock (_recorderLock)
        {
            foreach (var recorder in _danmakuRecorders.Values)
            {
                recorder.StopRecording();
                recorder.Dispose();
            }
            _danmakuRecorders.Clear();
        }
    }

    private void AddDanmakuToList(DanmakuMessage msg)
    {
        if (lstRecentDanmaku == null) return;

        var text = $"[{msg.Timestamp:HH:mm:ss}] {msg.Uname}: {msg.Content}";
        lstRecentDanmaku.Items.Add(text);

        while (lstRecentDanmaku.Items.Count > 500)
        {
            lstRecentDanmaku.Items.RemoveAt(0);
        }

        lstRecentDanmaku.TopIndex = lstRecentDanmaku.Items.Count - 1;
    }

    private void AddGiftToList(GiftMessage msg)
    {
        if (lstRecentDanmaku == null) return;

        var text = $"[礼物] {msg.Uname} 赠送 {msg.GiftName} x{msg.Count} (¥{msg.TotalCoin / 1000.0:F2})";
        var item = new ListBoxItem { Text = text, Color = Color.DarkOrange };
        lstRecentDanmaku.Items.Add(item);

        while (lstRecentDanmaku.Items.Count > 500)
        {
            lstRecentDanmaku.Items.RemoveAt(0);
        }

        lstRecentDanmaku.TopIndex = lstRecentDanmaku.Items.Count - 1;
    }

    private void AddSuperChatToList(SuperChatMessage msg)
    {
        if (lstRecentDanmaku == null) return;

        var text = $"[SC ¥{msg.Price}] {msg.Uname}: {msg.Message}";
        var item = new ListBoxItem { Text = text, Color = Color.Red };
        lstRecentDanmaku.Items.Add(item);

        while (lstRecentDanmaku.Items.Count > 500)
        {
            lstRecentDanmaku.Items.RemoveAt(0);
        }

        lstRecentDanmaku.TopIndex = lstRecentDanmaku.Items.Count - 1;
    }

    private async void BtnAdd_Click(object sender, EventArgs e)
    {
        if (txtRoomId == null) return;

        var input = txtRoomId.Text.Trim();
        if (string.IsNullOrWhiteSpace(input))
        {
            MessageBox.Show("请输入房间号", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        if (!long.TryParse(input, out var roomId))
        {
            MessageBox.Show("房间号格式不正确", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        if (_config.FollowedRooms.Any(r => r.RoomId == roomId))
        {
            MessageBox.Show("该直播间已在关注列表中", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        SetStatus("正在获取直播间信息...");
        if (btnAdd != null) btnAdd.Enabled = false;

        var roomInfo = await _checker.GetRoomInfo(roomId);

        if (btnAdd != null) btnAdd.Enabled = true;

        if (roomInfo == null)
        {
            MessageBox.Show("无法获取直播间信息，请检查房间号是否正确", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        if (_config.AddRoom(roomInfo))
        {
            txtRoomId.Clear();
            RefreshRoomList();
            SetStatus($"已添加关注：{roomInfo.UName}");
        }
        else
        {
            MessageBox.Show("添加失败", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void BtnRemove_Click(object sender, EventArgs e)
    {
        if (listViewRooms == null) return;

        if (listViewRooms.SelectedItems.Count == 0)
        {
            MessageBox.Show("请先选择要移除的直播间", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var tag = listViewRooms.SelectedItems[0].Tag;
        if (tag is not long roomId)
        {
            return;
        }

        var room = _config.FollowedRooms.FirstOrDefault(r => r.RoomId == roomId);
        if (room == null) return;

        var result = MessageBox.Show(
            $"确定要移除 {room.UName} 吗？",
            "确认移除",
            MessageBoxButtons.YesNo,
            MessageBoxIcon.Question
        );

        if (result == DialogResult.Yes)
        {
            StopDanmakuRecorder(roomId);
            _autoRecorder.StopRecording(roomId);

            if (_config.RemoveRoom(roomId))
            {
                RefreshRoomList();
                SetStatus($"已移除：{room.UName}");
            }
        }
    }

    private void BtnRefresh_Click(object sender, EventArgs e)
    {
        _checker.Refresh();
        SetStatus("正在刷新...");
    }

    private void BtnOpenRoom_Click(object sender, EventArgs e)
    {
        OpenSelectedRoom();
    }

    private void BtnStats_Click(object sender, EventArgs e)
    {
        if (listViewRooms == null) return;

        if (listViewRooms.SelectedItems.Count == 0)
        {
            MessageBox.Show("请先选择直播间", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var tag = listViewRooms.SelectedItems[0].Tag;
        if (tag is not long roomId) return;

        var room = _config.FollowedRooms.FirstOrDefault(r => r.RoomId == roomId);
        if (room == null) return;

        var sessionId = _database.GetActiveSessionId(roomId);
        if (!sessionId.HasValue)
        {
            MessageBox.Show("该直播间当前没有直播会话", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        var statsForm = new GiftStatsForm(_database, sessionId.Value, room.UName);
        statsForm.ShowDialog(this);
    }

    private void BtnToggleRecord_Click(object sender, EventArgs e)
    {
        if (listViewRooms == null) return;

        if (listViewRooms.SelectedItems.Count == 0)
        {
            MessageBox.Show("请先选择直播间", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var tag = listViewRooms.SelectedItems[0].Tag;
        if (tag is not long roomId) return;

        var room = _config.FollowedRooms.FirstOrDefault(r => r.RoomId == roomId);
        if (room == null) return;

        if (room.LiveStatus != 1)
        {
            MessageBox.Show("该直播间当前未开播", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        if (_autoRecorder.IsRecording(roomId))
        {
            _autoRecorder.StopRecording(roomId);
            SetStatus($"已停止录制：{room.UName}");
        }
        else
        {
            if (_autoRecorder.StartRecording(room))
            {
                SetStatus($"开始录制：{room.UName}");
            }
            else
            {
                MessageBox.Show("启动录屏失败，请检查录屏工具配置", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        RefreshRoomList();
    }

    private void ShowRecordSettings()
    {
        var form = new Form
        {
            Text = "录屏设置",
            Size = new Size(500, 350),
            StartPosition = FormStartPosition.CenterParent,
            FormBorderStyle = FormBorderStyle.FixedDialog,
            MaximizeBox = false,
            MinimizeBox = false
        };

        var lblTool = new Label
        {
            Text = "录屏工具：",
            Location = new Point(20, 20),
            AutoSize = true
        };

        var cmbTool = new ComboBox
        {
            Location = new Point(100, 17),
            Width = 200,
            DropDownStyle = ComboBoxStyle.DropDownList
        };
        cmbTool.Items.AddRange(new[] { "ffmpeg", "streamlink", "自定义命令" });
        cmbTool.SelectedIndex = cmbTool.Items.IndexOf(_autoRecorder.RecordTool);

        var lblQuality = new Label
        {
            Text = "画质(QN)：",
            Location = new Point(20, 60),
            AutoSize = true
        };

        var txtQuality = new TextBox
        {
            Location = new Point(100, 57),
            Width = 200,
            Text = _autoRecorder.Quality
        };

        var lblCmd = new Label
        {
            Text = "自定义命令：",
            Location = new Point(20, 100),
            AutoSize = true
        };

        var txtCmd = new TextBox
        {
            Location = new Point(20, 125),
            Width = 450,
            Multiline = true,
            Height = 80,
            Text = _autoRecorder.CustomCommand ?? string.Empty
        };

        var lblHint = new Label
        {
            Text = "可用变量: {roomId}, {roomName}, {title}, {output}, {quality}",
            Location = new Point(20, 210),
            AutoSize = true,
            ForeColor = Color.Gray
        };

        var btnSave = new Button
        {
            Text = "保存",
            Location = new Point(300, 260),
            Width = 80,
            Height = 30,
            DialogResult = DialogResult.OK
        };

        var btnCancel = new Button
        {
            Text = "取消",
            Location = new Point(390, 260),
            Width = 80,
            Height = 30,
            DialogResult = DialogResult.Cancel
        };

        btnSave.Click += (s, e) =>
        {
            _autoRecorder.RecordTool = cmbTool.SelectedItem?.ToString() ?? "ffmpeg";
            _autoRecorder.Quality = txtQuality.Text;
            _autoRecorder.CustomCommand = string.IsNullOrEmpty(txtCmd.Text) ? null : txtCmd.Text;
            form.DialogResult = DialogResult.OK;
            form.Close();
        };

        form.Controls.AddRange(new Control[]
        {
            lblTool, cmbTool, lblQuality, txtQuality, lblCmd, txtCmd, lblHint, btnSave, btnCancel
        });
        form.AcceptButton = btnSave;
        form.CancelButton = btnCancel;

        form.ShowDialog(this);
    }

    private void ListViewRooms_DoubleClick(object sender, EventArgs e)
    {
        OpenSelectedRoom();
    }

    private void OpenSelectedRoom()
    {
        if (listViewRooms == null || listViewRooms.SelectedItems.Count == 0) return;

        var tag = listViewRooms.SelectedItems[0].Tag;
        if (tag is not long roomId) return;

        var url = $"https://live.bilibili.com/{roomId}";

        try
        {
            Process.Start(new ProcessStartInfo(url)
            {
                UseShellExecute = true
            });
        }
        catch
        {
            MessageBox.Show("无法打开浏览器", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void RefreshRoomList()
    {
        if (listViewRooms == null) return;

        listViewRooms.Items.Clear();

        var sortedRooms = _config.FollowedRooms
            .OrderByDescending(r => r.LiveStatus)
            .ThenBy(r => r.UName);

        foreach (var room in sortedRooms)
        {
            var isRecording = _autoRecorder.IsRecording(room.RoomId);
            var isDanmakuRecording = false;
            lock (_recorderLock)
            {
                isDanmakuRecording = _danmakuRecorders.ContainsKey(room.RoomId);
            }

            var item = new ListViewItem(GetStatusText(room.LiveStatus));
            item.Tag = room.RoomId;
            item.BackColor = room.LiveStatus == 1 ? Color.LightGreen : Color.White;

            item.SubItems.Add(room.UName);
            item.SubItems.Add(room.Title);
            item.SubItems.Add(room.AreaName);
            item.SubItems.Add(room.LastLiveTime == DateTime.MinValue ? "-" : room.LastLiveTime.ToString("yyyy-MM-dd HH:mm"));

            var recordStatus = new List<string>();
            if (isDanmakuRecording) recordStatus.Add("弹幕");
            if (isRecording) recordStatus.Add("录屏");
            item.SubItems.Add(recordStatus.Count > 0 ? string.Join("+", recordStatus) : "-");

            listViewRooms.Items.Add(item);
        }
    }

    private string GetStatusText(int status)
    {
        return status switch
        {
            0 => "未开播",
            1 => "直播中",
            2 => "轮播中",
            _ => "未知"
        };
    }

    private void SetStatus(string text)
    {
        if (lblStatus != null)
        {
            lblStatus.Text = text;
        }
    }
}

public class ListBoxItem
{
    public string Text { get; set; } = string.Empty;
    public Color Color { get; set; } = Color.Black;

    public override string ToString()
    {
        return Text;
    }
}
