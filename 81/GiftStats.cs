using System.Drawing;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public partial class GiftStatsForm : Form
{
    private readonly Database _db;
    private readonly long _sessionId;
    private readonly string _roomName;
    private List<GiftStatsResult> _giftStats = new();
    private List<GiftStatsByUser> _userStats = new();
    private int _danmakuCount;
    private long _totalIncome;

    private Label? _lblTitle;
    private Label? _lblSummary;
    private TabControl? _tabControl;
    private TabPage? _tabGifts;
    private TabPage? _tabUsers;
    private ListView? _lvGifts;
    private ListView? _lvUsers;
    private Panel? _chartPanel;
    private Button? _btnRefresh;

    public GiftStatsForm(Database db, long sessionId, string roomName)
    {
        _db = db;
        _sessionId = sessionId;
        _roomName = roomName;

        InitializeComponent();
        LoadData();
    }

    private void InitializeComponent()
    {
        this.Text = $"礼物统计 - {_roomName}";
        this.Size = new Size(900, 650);
        this.StartPosition = FormStartPosition.CenterParent;
        this.MinimizeBox = false;
        this.MaximizeBox = false;
        this.FormBorderStyle = FormBorderStyle.FixedDialog;

        _lblTitle = new Label
        {
            Text = "礼物统计",
            Location = new Point(20, 15),
            Font = new Font("Microsoft YaHei UI", 14, FontStyle.Bold),
            AutoSize = true
        };

        _lblSummary = new Label
        {
            Location = new Point(20, 45),
            Font = new Font("Microsoft YaHei UI", 10),
            AutoSize = true
        };

        _btnRefresh = new Button
        {
            Text = "刷新",
            Location = new Point(780, 40),
            Size = new Size(80, 30)
        };
        _btnRefresh.Click += (s, e) => LoadData();

        _tabControl = new TabControl
        {
            Location = new Point(20, 80),
            Size = new Size(845, 500)
        };

        _tabGifts = new TabPage("礼物分布");
        _tabUsers = new TabPage("送礼榜");

        _lvGifts = new ListView
        {
            Dock = DockStyle.Fill,
            View = View.Details,
            FullRowSelect = true,
            GridLines = true
        };
        _lvGifts.Columns.Add("礼物名称", 150);
        _lvGifts.Columns.Add("数量", 80);
        _lvGifts.Columns.Add("总价值(金瓜子)", 120);
        _lvGifts.Columns.Add("赠送次数", 80);
        _tabGifts.Controls.Add(_lvGifts);

        _lvUsers = new ListView
        {
            Dock = DockStyle.Fill,
            View = View.Details,
            FullRowSelect = true,
            GridLines = true
        };
        _lvUsers.Columns.Add("排名", 60);
        _lvUsers.Columns.Add("用户名", 150);
        _lvUsers.Columns.Add("总价值(金瓜子)", 120);
        _lvUsers.Columns.Add("送礼次数", 80);
        _tabUsers.Controls.Add(_lvUsers);

        _chartPanel = new Panel
        {
            Location = new Point(20, 80),
            Size = new Size(845, 250),
            BorderStyle = BorderStyle.FixedSingle
        };
        _chartPanel.Paint += ChartPanel_Paint;

        _tabGifts.Controls.Add(_chartPanel);
        _chartPanel.BringToFront();

        var chartLabel = new Label
        {
            Text = "礼物价值分布",
            Location = new Point(30, 90),
            AutoSize = true,
            BackColor = Color.Transparent,
            Font = new Font("Microsoft YaHei UI", 9, FontStyle.Bold)
        };
        _tabGifts.Controls.Add(chartLabel);
        chartLabel.BringToFront();

        _tabControl.TabPages.Add(_tabGifts);
        _tabControl.TabPages.Add(_tabUsers);

        this.Controls.Add(_lblTitle);
        this.Controls.Add(_lblSummary);
        this.Controls.Add(_btnRefresh);
        this.Controls.Add(_tabControl);
    }

    private void LoadData()
    {
        _giftStats = _db.GetGiftStatsBySession(_sessionId);
        _userStats = _db.GetGiftStatsByUser(_sessionId, 20);
        _danmakuCount = _db.GetDanmakuCount(_sessionId);
        _totalIncome = _db.GetTotalIncome(_sessionId);

        UpdateUI();
    }

    private void UpdateUI()
    {
        if (_lblSummary != null)
        {
            _lblSummary.Text = $"弹幕数: {_danmakuCount:N0}  |  礼物总价值: {_totalIncome:N0} 金瓜子 (约 ¥{_totalIncome / 1000:N2})";
        }

        if (_lvGifts != null)
        {
            _lvGifts.Items.Clear();
            foreach (var stat in _giftStats)
            {
                var item = new ListViewItem(stat.GiftName);
                item.SubItems.Add(stat.TotalCount.ToString("N0"));
                item.SubItems.Add(stat.TotalCoin.ToString("N0"));
                item.SubItems.Add(stat.SendCount.ToString("N0"));
                _lvGifts.Items.Add(item);
            }
        }

        if (_lvUsers != null)
        {
            _lvUsers.Items.Clear();
            for (int i = 0; i < _userStats.Count; i++)
            {
                var stat = _userStats[i];
                var item = new ListViewItem((i + 1).ToString());
                item.SubItems.Add(stat.Uname);
                item.SubItems.Add(stat.TotalCoin.ToString("N0"));
                item.SubItems.Add(stat.GiftCount.ToString("N0"));

                if (i == 0) item.BackColor = Color.FromArgb(255, 215, 0);
                else if (i == 1) item.BackColor = Color.FromArgb(192, 192, 192);
                else if (i == 2) item.BackColor = Color.FromArgb(205, 127, 50);

                _lvUsers.Items.Add(item);
            }
        }

        _chartPanel?.Invalidate();
    }

    private void ChartPanel_Paint(object? sender, PaintEventArgs e)
    {
        if (_chartPanel == null || e.Graphics == null) return;

        var g = e.Graphics;
        g.Clear(Color.White);

        if (_giftStats.Count == 0)
        {
            using var font = new Font("Microsoft YaHei UI", 12);
            g.DrawString("暂无礼物数据", font, Brushes.Gray, _chartPanel.Width / 2 - 60, _chartPanel.Height / 2 - 10);
            return;
        }

        var margin = 50;
        var chartWidth = _chartPanel.Width - margin * 2;
        var chartHeight = _chartPanel.Height - margin * 2;
        var barWidth = Math.Min(60, chartWidth / Math.Max(_giftStats.Count, 1) - 10);
        var maxValue = _giftStats.Max(s => s.TotalCoin);
        if (maxValue == 0) maxValue = 1;

        using var pen = new Pen(Color.LightGray) { DashStyle = System.Drawing.Drawing2D.DashStyle.Dash };
        for (int i = 0; i <= 5; i++)
        {
            var y = margin + chartHeight - (chartHeight * i / 5);
            g.DrawLine(pen, margin, y, margin + chartWidth, y);

            var value = maxValue * i / 5;
            using var font = new Font("Microsoft YaHei UI", 8);
            g.DrawString(value.ToString("N0"), font, Brushes.Gray, 5, y - 8);
        }

        var colors = new[]
        {
            Color.FromArgb(52, 152, 219),
            Color.FromArgb(46, 204, 113),
            Color.FromArgb(155, 89, 182),
            Color.FromArgb(241, 196, 15),
            Color.FromArgb(230, 126, 34),
            Color.FromArgb(231, 76, 60),
            Color.FromArgb(26, 188, 156),
            Color.FromArgb(52, 73, 94)
        };

        for (int i = 0; i < _giftStats.Count && i < 8; i++)
        {
            var stat = _giftStats[i];
            var barHeight = (int)(chartHeight * (double)stat.TotalCoin / maxValue);
            var x = margin + (chartWidth / Math.Max(_giftStats.Count, 1)) * i + (chartWidth / Math.Max(_giftStats.Count, 1) - barWidth) / 2;
            var y = margin + chartHeight - barHeight;

            using var brush = new SolidBrush(colors[i % colors.Length]);
            g.FillRectangle(brush, x, y, barWidth, barHeight);

            using var penBorder = new Pen(Color.FromArgb(200, colors[i % colors.Length]));
            g.DrawRectangle(penBorder, x, y, barWidth, barHeight);

            using var font = new Font("Microsoft YaHei UI", 7);
            var labelRect = new RectangleF(x - 10, y - 18, barWidth + 20, 16);
            var sf = new StringFormat { Alignment = StringAlignment.Center };
            g.DrawString(stat.TotalCoin.ToString("N0"), font, Brushes.Black, labelRect, sf);

            var nameFont = new Font("Microsoft YaHei UI", 7);
            var nameRect = new RectangleF(x - 30, margin + chartHeight + 2, barWidth + 60, 30);
            g.DrawString(TruncateString(stat.GiftName, 6), nameFont, Brushes.Black, nameRect, sf);
        }
    }

    private string TruncateString(string str, int maxLength)
    {
        if (string.IsNullOrEmpty(str)) return str;
        return str.Length <= maxLength ? str : str.Substring(0, maxLength) + "...";
    }
}
