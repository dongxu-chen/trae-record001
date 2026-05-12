using System.Drawing.Imaging;

namespace ImageBatchTool;

public partial class MainForm : Form
{
    private readonly List<string> _imageFiles = new();
    private Panel? _dragDropPanel;
    private ListBox? _fileListBox;
    private TabControl? _mainTabControl;
    private Button? _processBtn;
    private ProgressBar? _progressBar;
    private Label? _statusLabel;

    private NumericUpDown? _resizeWidth;
    private NumericUpDown? _resizeHeight;
    private CheckBox? _resizeKeepRatio;

    private TextBox? _watermarkText;
    private ComboBox? _watermarkPosition;
    private NumericUpDown? _watermarkOpacity;

    private ComboBox? _formatCombo;
    private TextBox? _formatOutputDir;

    private TextBox? _renamePrefix;
    private TextBox? _renameSuffix;
    private CheckBox? _renameUseNumber;
    private NumericUpDown? _renameStartNum;
    private NumericUpDown? _renamePad;
    private CheckBox? _renameUseRegex;
    private TextBox? _renamePattern;
    private TextBox? _renameReplacement;
    private CheckBox? _renameCopyMode;
    private TextBox? _renameOutputDir;
    private ListBox? _renamePreview;

    private CheckBox? _exifRemoveAll;
    private CheckBox? _exifRemoveIptc;
    private CheckBox? _exifRemoveXmp;
    private CheckBox? _exifRemoveProfile;
    private TextBox? _exifOutputDir;
    private Label? _exifInfoLabel;

    public MainForm()
    {
        InitializeCustomComponents();
    }

    private void InitializeCustomComponents()
    {
        Text = "图片批量处理工具";
        Size = new Size(1100, 750);
        StartPosition = FormStartPosition.CenterScreen;
        MinimumSize = new Size(1000, 650);

        var mainSplit = new SplitContainer
        {
            Dock = DockStyle.Fill,
            Orientation = Orientation.Vertical,
            SplitterDistance = 380,
            FixedPanel = FixedPanel.Panel1
        };

        _dragDropPanel = new Panel
        {
            Dock = DockStyle.Fill,
            BackColor = Color.FromArgb(240, 240, 250),
            BorderStyle = BorderStyle.FixedSingle,
            AllowDrop = true
        };

        var dragLabel = new Label
        {
            Text = "拖拽图片文件或文件夹到此处\n\n点击选择文件",
            TextAlign = ContentAlignment.MiddleCenter,
            Dock = DockStyle.Fill,
            Font = new Font("Microsoft YaHei", 14, FontStyle.Bold),
            ForeColor = Color.Gray,
            Cursor = Cursors.Hand
        };

        dragLabel.Click += (s, e) => SelectFiles();
        _dragDropPanel.DragEnter += DragDropPanel_DragEnter;
        _dragDropPanel.DragDrop += DragDropPanel_DragDrop;
        _dragDropPanel.Controls.Add(dragLabel);

        var filePanel = new Panel
        {
            Dock = DockStyle.Bottom,
            Height = 220
        };

        var fileHeader = new Panel
        {
            Dock = DockStyle.Top,
            Height = 35
        };

        var fileLabel = new Label
        {
            Text = "已添加的图片（双击移除）:",
            Dock = DockStyle.Left,
            Width = 180,
            Padding = new Padding(5, 10, 5, 5)
        };

        var fileCountLabel = new Label
        {
            Name = "fileCountLabel",
            Text = "共 0 个文件",
            Dock = DockStyle.Left,
            Width = 100,
            Padding = new Padding(5, 10, 5, 5),
            ForeColor = Color.DimGray
        };

        var clearBtn = new Button
        {
            Text = "清空",
            Dock = DockStyle.Right,
            Width = 60,
            Margin = new Padding(5)
        };
        clearBtn.Click += (s, e) => ClearFiles();

        fileHeader.Controls.Add(fileLabel);
        fileHeader.Controls.Add(fileCountLabel);
        fileHeader.Controls.Add(clearBtn);

        _fileListBox = new ListBox
        {
            Dock = DockStyle.Fill,
            SelectionMode = SelectionMode.MultiExtended
        };
        _fileListBox.DoubleClick += (s, e) => RemoveSelectedFiles();

        filePanel.Controls.Add(_fileListBox);
        filePanel.Controls.Add(fileHeader);

        mainSplit.Panel1.Controls.Add(_dragDropPanel);
        mainSplit.Panel1.Controls.Add(filePanel);

        _mainTabControl = new TabControl
        {
            Dock = DockStyle.Fill,
            Padding = new Point(15, 5)
        };

        var processTab = new TabPage("图片处理");
        var renameTab = new TabPage("批量重命名");
        var exifTab = new TabPage("EXIF 删除");

        processTab.Controls.Add(CreateProcessTab());
        renameTab.Controls.Add(CreateRenameTab());
        exifTab.Controls.Add(CreateExifTab());

        _mainTabControl.TabPages.Add(processTab);
        _mainTabControl.TabPages.Add(renameTab);
        _mainTabControl.TabPages.Add(exifTab);

        mainSplit.Panel2.Controls.Add(_mainTabControl);

        var bottomPanel = new Panel
        {
            Dock = DockStyle.Bottom,
            Height = 90
        };

        _processBtn = new Button
        {
            Text = "开始处理",
            Dock = DockStyle.Top,
            Height = 40,
            Font = new Font("Microsoft YaHei", 12, FontStyle.Bold),
            BackColor = Color.FromArgb(100, 149, 237),
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat
        };
        _processBtn.Click += async (s, e) => await ProcessCurrentTab();

        _progressBar = new ProgressBar
        {
            Dock = DockStyle.Top,
            Height = 20,
            Style = ProgressBarStyle.Continuous,
            Margin = new Padding(5)
        };

        _statusLabel = new Label
        {
            Text = "准备就绪",
            Dock = DockStyle.Fill,
            Padding = new Padding(10, 5, 10, 5),
            AutoSize = false,
            BackColor = Color.FromArgb(245, 245, 245)
        };

        bottomPanel.Controls.Add(_progressBar);
        bottomPanel.Controls.Add(_processBtn);
        bottomPanel.Controls.Add(_statusLabel);

        Controls.Add(mainSplit);
        Controls.Add(bottomPanel);
    }

    private Panel CreateProcessTab()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(15), AutoScroll = true };

        var resizeGroup = new GroupBox
        {
            Text = "图片缩放",
            Dock = DockStyle.Top,
            Height = 110,
            Padding = new Padding(10)
        };

        var widthLabel = new Label { Text = "宽度:", Location = new Point(15, 30), Width = 50 };
        _resizeWidth = new NumericUpDown
        {
            Location = new Point(70, 28),
            Width = 100,
            Maximum = 10000,
            Value = 800
        };

        var heightLabel = new Label { Text = "高度:", Location = new Point(190, 30), Width = 50 };
        _resizeHeight = new NumericUpDown
        {
            Location = new Point(245, 28),
            Width = 100,
            Maximum = 10000,
            Value = 600
        };

        _resizeKeepRatio = new CheckBox
        {
            Text = "保持宽高比",
            Location = new Point(15, 65),
            Checked = true
        };

        resizeGroup.Controls.Add(widthLabel);
        resizeGroup.Controls.Add(_resizeWidth);
        resizeGroup.Controls.Add(heightLabel);
        resizeGroup.Controls.Add(_resizeHeight);
        resizeGroup.Controls.Add(_resizeKeepRatio);

        var watermarkGroup = new GroupBox
        {
            Text = "水印设置",
            Dock = DockStyle.Top,
            Height = 130,
            Padding = new Padding(10)
        };

        var watermarkLabel = new Label { Text = "水印文字:", Location = new Point(15, 30), Width = 70 };
        _watermarkText = new TextBox
        {
            Location = new Point(90, 27),
            Width = 280,
            Text = "© 2026"
        };

        var positionLabel = new Label { Text = "位置:", Location = new Point(15, 65), Width = 50 };
        _watermarkPosition = new ComboBox
        {
            Location = new Point(70, 62),
            Width = 140,
            DropDownStyle = ComboBoxStyle.DropDownList
        };
        _watermarkPosition.Items.AddRange(new object[] { "右下角", "右上角", "左下角", "左上角", "居中" });
        _watermarkPosition.SelectedIndex = 0;

        var opacityLabel = new Label { Text = "透明度:", Location = new Point(230, 65), Width = 60 };
        _watermarkOpacity = new NumericUpDown
        {
            Location = new Point(295, 62),
            Width = 80,
            Minimum = 10,
            Maximum = 100,
            Value = 50
        };

        watermarkGroup.Controls.Add(watermarkLabel);
        watermarkGroup.Controls.Add(_watermarkText);
        watermarkGroup.Controls.Add(positionLabel);
        watermarkGroup.Controls.Add(_watermarkPosition);
        watermarkGroup.Controls.Add(opacityLabel);
        watermarkGroup.Controls.Add(_watermarkOpacity);

        var formatGroup = new GroupBox
        {
            Text = "格式转换",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        var formatLabel = new Label { Text = "输出格式:", Location = new Point(15, 35), Width = 70 };
        _formatCombo = new ComboBox
        {
            Location = new Point(90, 32),
            Width = 150,
            DropDownStyle = ComboBoxStyle.DropDownList
        };
        _formatCombo.Items.AddRange(new object[] { "保持原格式", "JPEG", "PNG", "BMP", "GIF", "TIFF", "WebP" });
        _formatCombo.SelectedIndex = 0;

        formatGroup.Controls.Add(formatLabel);
        formatGroup.Controls.Add(_formatCombo);

        var outputGroup = new GroupBox
        {
            Text = "输出目录",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        _formatOutputDir = new TextBox
        {
            Location = new Point(15, 32),
            Width = 340
        };
        _formatOutputDir.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "ProcessedImages");

        var browseBtn = new Button
        {
            Text = "浏览...",
            Location = new Point(360, 30),
            Width = 80
        };
        browseBtn.Click += (s, e) => BrowseOutputDir(_formatOutputDir);

        outputGroup.Controls.Add(_formatOutputDir);
        outputGroup.Controls.Add(browseBtn);

        panel.Controls.Add(outputGroup);
        panel.Controls.Add(formatGroup);
        panel.Controls.Add(watermarkGroup);
        panel.Controls.Add(resizeGroup);

        return panel;
    }

    private Panel CreateRenameTab()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(15), AutoScroll = true };

        var previewPanel = new GroupBox
        {
            Text = "重命名预览（点击刷新）",
            Dock = DockStyle.Bottom,
            Height = 180,
            Padding = new Padding(10)
        };

        _renamePreview = new ListBox
        {
            Dock = DockStyle.Fill,
            HorizontalScrollbar = true
        };

        var refreshBtn = new Button
        {
            Text = "刷新预览",
            Dock = DockStyle.Bottom,
            Height = 30
        };
        refreshBtn.Click += (s, e) => RefreshRenamePreview();

        previewPanel.Controls.Add(_renamePreview);
        previewPanel.Controls.Add(refreshBtn);

        var numberGroup = new GroupBox
        {
            Text = "数字编号",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        _renameUseNumber = new CheckBox
        {
            Text = "启用数字编号",
            Location = new Point(15, 30),
            Checked = true
        };

        var startLabel = new Label { Text = "起始数字:", Location = new Point(150, 32), Width = 70 };
        _renameStartNum = new NumericUpDown
        {
            Location = new Point(225, 30),
            Width = 80,
            Minimum = 0,
            Maximum = 10000,
            Value = 1
        };

        var padLabel = new Label { Text = "补零位数:", Location = new Point(320, 32), Width = 70 };
        _renamePad = new NumericUpDown
        {
            Location = new Point(395, 30),
            Width = 60,
            Minimum = 1,
            Maximum = 10,
            Value = 3
        };

        numberGroup.Controls.Add(_renameUseNumber);
        numberGroup.Controls.Add(startLabel);
        numberGroup.Controls.Add(_renameStartNum);
        numberGroup.Controls.Add(padLabel);
        numberGroup.Controls.Add(_renamePad);

        var basicGroup = new GroupBox
        {
            Text = "基本设置",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        var prefixLabel = new Label { Text = "前缀:", Location = new Point(15, 32), Width = 40 };
        _renamePrefix = new TextBox
        {
            Location = new Point(60, 30),
            Width = 120
        };

        var suffixLabel = new Label { Text = "后缀:", Location = new Point(200, 32), Width = 40 };
        _renameSuffix = new TextBox
        {
            Location = new Point(245, 30),
            Width = 120
        };

        basicGroup.Controls.Add(prefixLabel);
        basicGroup.Controls.Add(_renamePrefix);
        basicGroup.Controls.Add(suffixLabel);
        basicGroup.Controls.Add(_renameSuffix);

        var regexGroup = new GroupBox
        {
            Text = "正则表达式替换",
            Dock = DockStyle.Top,
            Height = 110,
            Padding = new Padding(10)
        };

        _renameUseRegex = new CheckBox
        {
            Text = "启用正则替换（与编号互斥）",
            Location = new Point(15, 25)
        };

        var patternLabel = new Label { Text = "查找模式:", Location = new Point(15, 55), Width = 70 };
        _renamePattern = new TextBox
        {
            Location = new Point(90, 52),
            Width = 200,
            Text = @"(\d+)"
        };

        var replaceLabel = new Label { Text = "替换为:", Location = new Point(310, 55), Width = 60 };
        _renameReplacement = new TextBox
        {
            Location = new Point(375, 52),
            Width = 100,
            Text = "img_$1"
        };

        regexGroup.Controls.Add(_renameUseRegex);
        regexGroup.Controls.Add(patternLabel);
        regexGroup.Controls.Add(_renamePattern);
        regexGroup.Controls.Add(replaceLabel);
        regexGroup.Controls.Add(_renameReplacement);

        var outputGroup = new GroupBox
        {
            Text = "输出设置",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        _renameCopyMode = new CheckBox
        {
            Text = "复制到新目录（不修改原文件）",
            Location = new Point(15, 25),
            Checked = true
        };

        var dirLabel = new Label { Text = "输出目录:", Location = new Point(15, 55), Width = 70 };
        _renameOutputDir = new TextBox
        {
            Location = new Point(90, 52),
            Width = 280,
            Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "RenamedImages")
        };

        var browseBtn = new Button
        {
            Text = "浏览...",
            Location = new Point(380, 50),
            Width = 80
        };
        browseBtn.Click += (s, e) => BrowseOutputDir(_renameOutputDir);

        outputGroup.Controls.Add(_renameCopyMode);
        outputGroup.Controls.Add(dirLabel);
        outputGroup.Controls.Add(_renameOutputDir);
        outputGroup.Controls.Add(browseBtn);

        panel.Controls.Add(previewPanel);
        panel.Controls.Add(numberGroup);
        panel.Controls.Add(basicGroup);
        panel.Controls.Add(regexGroup);
        panel.Controls.Add(outputGroup);

        return panel;
    }

    private Panel CreateExifTab()
    {
        var panel = new Panel { Dock = DockStyle.Fill, Padding = new Padding(15), AutoScroll = true };

        var infoGroup = new GroupBox
        {
            Text = "EXIF 信息",
            Dock = DockStyle.Top,
            Height = 60,
            Padding = new Padding(10)
        };

        _exifInfoLabel = new Label
        {
            Text = "选择图片文件后，点击检测可查看 EXIF 数量",
            Dock = DockStyle.Fill,
            Padding = new Padding(5, 10, 5, 5),
            ForeColor = Color.DimGray
        };

        var detectBtn = new Button
        {
            Text = "检测",
            Dock = DockStyle.Right,
            Width = 80
        };
        detectBtn.Click += (s, e) => DetectExif();

        infoGroup.Controls.Add(_exifInfoLabel);
        infoGroup.Controls.Add(detectBtn);

        var optionsGroup = new GroupBox
        {
            Text = "删除选项",
            Dock = DockStyle.Top,
            Height = 150,
            Padding = new Padding(10)
        };

        _exifRemoveAll = new CheckBox
        {
            Text = "删除所有元数据（推荐）",
            Location = new Point(15, 25),
            Checked = true
        };

        _exifRemoveIptc = new CheckBox
        {
            Text = "删除 IPTC 数据",
            Location = new Point(15, 55),
            Checked = true
        };

        _exifRemoveXmp = new CheckBox
        {
            Text = "删除 XMP 数据",
            Location = new Point(15, 85),
            Checked = true
        };

        _exifRemoveProfile = new CheckBox
        {
            Text = "删除色彩配置文件",
            Location = new Point(15, 115),
            Checked = false
        };

        optionsGroup.Controls.Add(_exifRemoveAll);
        optionsGroup.Controls.Add(_exifRemoveIptc);
        optionsGroup.Controls.Add(_exifRemoveXmp);
        optionsGroup.Controls.Add(_exifRemoveProfile);

        var outputGroup = new GroupBox
        {
            Text = "输出目录",
            Dock = DockStyle.Top,
            Height = 90,
            Padding = new Padding(10)
        };

        var dirLabel = new Label { Text = "输出目录:", Location = new Point(15, 32), Width = 70 };
        _exifOutputDir = new TextBox
        {
            Location = new Point(90, 30),
            Width = 300,
            Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "StrippedImages")
        };

        var browseBtn = new Button
        {
            Text = "浏览...",
            Location = new Point(400, 28),
            Width = 80
        };
        browseBtn.Click += (s, e) => BrowseOutputDir(_exifOutputDir);

        outputGroup.Controls.Add(dirLabel);
        outputGroup.Controls.Add(_exifOutputDir);
        outputGroup.Controls.Add(browseBtn);

        var hintGroup = new GroupBox
        {
            Text = "说明",
            Dock = DockStyle.Top,
            Height = 110,
            Padding = new Padding(10)
        };

        var hintLabel = new Label
        {
            Text = "• 优先使用 ImageMagick (Magick.NET) 进行处理\n• 如未安装则使用 GDI+ 回退方案（仅能移除部分元数据）\n• 删除 EXIF 可保护隐私，去除拍摄时间、GPS、设备型号等信息",
            Dock = DockStyle.Fill,
            Padding = new Padding(5),
            ForeColor = Color.DimGray
        };

        hintGroup.Controls.Add(hintLabel);

        panel.Controls.Add(infoGroup);
        panel.Controls.Add(outputGroup);
        panel.Controls.Add(optionsGroup);
        panel.Controls.Add(hintGroup);

        return panel;
    }

    private void DragDropPanel_DragEnter(object? sender, DragEventArgs e)
    {
        if (e.Data?.GetDataPresent(DataFormats.FileDrop) == true)
        {
            e.Effect = DragDropEffects.Copy;
        }
    }

    private void DragDropPanel_DragDrop(object? sender, DragEventArgs e)
    {
        if (e.Data?.GetData(DataFormats.FileDrop) is string[] files)
        {
            AddFilesOrFolders(files);
        }
    }

    private void SelectFiles()
    {
        using var dialog = new OpenFileDialog
        {
            Multiselect = true,
            Filter = "图片文件|*.jpg;*.jpeg;*.png;*.bmp;*.gif;*.tiff;*.tif;*.webp|所有文件|*.*",
            Title = "选择图片文件"
        };

        if (dialog.ShowDialog() == DialogResult.OK)
        {
            AddFilesOrFolders(dialog.FileNames);
        }
    }

    private void AddFilesOrFolders(string[] paths)
    {
        foreach (var path in paths)
        {
            if (Directory.Exists(path))
            {
                var files = Directory.GetFiles(path, "*.*", SearchOption.AllDirectories)
                    .Where(f => FormatConverter.IsSupportedFormat(Path.GetExtension(f)));
                foreach (var file in files)
                {
                    AddFile(file);
                }
            }
            else if (File.Exists(path) && FormatConverter.IsSupportedFormat(Path.GetExtension(path)))
            {
                AddFile(path);
            }
        }

        UpdateFileCount();
        UpdateStatus($"已添加 {_imageFiles.Count} 个文件");
    }

    private void AddFile(string filePath)
    {
        if (!_imageFiles.Contains(filePath))
        {
            _imageFiles.Add(filePath);
            _fileListBox?.Items.Add(Path.GetFileName(filePath));
        }
    }

    private void RemoveSelectedFiles()
    {
        if (_fileListBox == null) return;

        var selected = _fileListBox.SelectedIndices.Cast<int>().OrderByDescending(i => i).ToList();
        foreach (var index in selected)
        {
            _imageFiles.RemoveAt(index);
            _fileListBox.Items.RemoveAt(index);
        }

        UpdateFileCount();
        UpdateStatus($"已添加 {_imageFiles.Count} 个文件");
    }

    private void ClearFiles()
    {
        _imageFiles.Clear();
        _fileListBox?.Items.Clear();
        UpdateFileCount();
        UpdateStatus("列表已清空");
    }

    private void UpdateFileCount()
    {
        var countLabel = Controls.Find("fileCountLabel", true).FirstOrDefault() as Label;
        if (countLabel != null)
        {
            countLabel.Text = $"共 {_imageFiles.Count} 个文件";
        }
    }

    private void BrowseOutputDir(TextBox targetText)
    {
        using var dialog = new FolderBrowserDialog
        {
            Description = "选择输出目录",
            SelectedPath = targetText?.Text ?? string.Empty
        };

        if (dialog.ShowDialog() == DialogResult.OK && targetText != null)
        {
            targetText.Text = dialog.SelectedPath;
        }
    }

    private void RefreshRenamePreview()
    {
        if (_renamePreview == null) return;

        _renamePreview.Items.Clear();

        if (_imageFiles.Count == 0)
        {
            _renamePreview.Items.Add("请先添加图片文件");
            return;
        }

        try
        {
            var options = new RenameOptions
            {
                Prefix = _renamePrefix?.Text ?? string.Empty,
                Suffix = _renameSuffix?.Text ?? string.Empty,
                UseNumbering = _renameUseNumber?.Checked ?? true,
                StartNumber = (int)(_renameStartNum?.Value ?? 1),
                NumberPadding = (int)(_renamePad?.Value ?? 3),
                UseRegex = _renameUseRegex?.Checked ?? false,
                RegexPattern = _renamePattern?.Text ?? string.Empty,
                RegexReplacement = _renameReplacement?.Text ?? string.Empty,
                KeepOriginalExtension = true
            };

            var names = RenameWorker.GenerateNewNames(_imageFiles, options);
            for (int i = 0; i < names.Count; i++)
            {
                _renamePreview.Items.Add($"{Path.GetFileName(names[i].OriginalPath)}  →  {Path.GetFileName(names[i].NewPath)}");
            }
        }
        catch (Exception ex)
        {
            _renamePreview.Items.Add($"错误: {ex.Message}");
        }
    }

    private void DetectExif()
    {
        if (_imageFiles.Count == 0)
        {
            MessageBox.Show("请先添加图片文件", "提示", MessageBoxButtons.OK, MessageBoxIcon.Information);
            return;
        }

        int totalExif = 0;
        int filesWithExif = 0;

        foreach (var file in _imageFiles)
        {
            var count = ExifRemover.GetExifDataCount(file);
            if (count > 0)
            {
                totalExif += count;
                filesWithExif++;
            }
        }

        var engine = ExifRemover.HasMagickNet ? "ImageMagick" : "GDI+ (回退)";
        _exifInfoLabel!.Text = $"{_imageFiles.Count} 个文件，{filesWithExif} 个含 EXIF（共 {totalExif} 条数据）| 引擎: {engine}";
    }

    private async Task ProcessCurrentTab()
    {
        if (_imageFiles.Count == 0)
        {
            MessageBox.Show("请先添加图片文件", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var currentTab = _mainTabControl?.SelectedTab?.Text ?? "图片处理";

        switch (currentTab)
        {
            case "图片处理":
                await ProcessImages();
                break;
            case "批量重命名":
                await ProcessRename();
                break;
            case "EXIF 删除":
                await ProcessExifRemoval();
                break;
        }
    }

    private async Task ProcessImages()
    {
        var outputDir = _formatOutputDir?.Text ?? string.Empty;
        if (string.IsNullOrWhiteSpace(outputDir))
        {
            MessageBox.Show("请选择输出目录", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        Directory.CreateDirectory(outputDir);

        _processBtn!.Enabled = false;
        _progressBar!.Maximum = _imageFiles.Count;
        _progressBar.Value = 0;

        int successCount = 0;
        int failCount = 0;

        var resizeOptions = new ResizeOptions
        {
            Width = (int)(_resizeWidth?.Value ?? 800),
            Height = (int)(_resizeHeight?.Value ?? 600),
            KeepAspectRatio = _resizeKeepRatio?.Checked ?? true
        };

        var watermarkOptions = new WatermarkOptions
        {
            Text = _watermarkText?.Text ?? string.Empty,
            Position = ParsePosition(_watermarkPosition?.SelectedIndex ?? 0),
            Opacity = (int)(_watermarkOpacity?.Value ?? 50)
        };

        var formatIndex = _formatCombo?.SelectedIndex ?? 0;
        var targetExt = GetTargetExtension(formatIndex);

        try
        {
            for (int i = 0; i < _imageFiles.Count; i++)
            {
                var inputPath = _imageFiles[i];
                var fileName = Path.GetFileNameWithoutExtension(inputPath);
                var ext = targetExt ?? Path.GetExtension(inputPath);
                var outputPath = Path.Combine(outputDir, $"{fileName}_processed{ext}");

                UpdateStatus($"正在处理: {Path.GetFileName(inputPath)} ({i + 1}/{_imageFiles.Count})");

                try
                {
                    var inputExt = Path.GetExtension(inputPath).ToLower();
                    var isAnimatedGif = inputExt == ".gif" && FormatConverter.IsAnimatedGif(inputPath);
                    var targetIsGif = ext == ".gif";
                    var isWebp = inputExt == ".webp" || ext == ".webp";

                    if (isWebp)
                    {
                        if (!FormatConverter.HasMagickNet)
                        {
                            throw new NotSupportedException("WebP 格式需要安装 Magick.NET 库");
                        }

                        if (HasResizeOrWatermark(resizeOptions, watermarkOptions, inputPath))
                        {
                            using var image = Image.FromFile(inputPath);
                            using var processed = ProcessSingleImage(image, resizeOptions, watermarkOptions);
                            var tempPath = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString() + ".png");
                            processed.Save(tempPath, ImageFormat.Png);
                            FormatConverter.ConvertWithMagick(tempPath, outputPath, 90);
                            File.Delete(tempPath);
                        }
                        else
                        {
                            FormatConverter.ConvertWithMagick(inputPath, outputPath, 90);
                        }
                    }
                    else if (isAnimatedGif && targetIsGif && !HasResizeOrWatermark(resizeOptions, watermarkOptions, inputPath))
                    {
                        File.Copy(inputPath, outputPath, true);
                    }
                    else
                    {
                        using var image = Image.FromFile(inputPath);
                        using var processed = ProcessSingleImage(image, resizeOptions, watermarkOptions);
                        SaveImage(processed, outputPath, ext);
                    }

                    successCount++;
                }
                catch (Exception ex)
                {
                    failCount++;
                    UpdateStatus($"处理失败: {Path.GetFileName(inputPath)} - {ex.Message}");
                    await Task.Delay(500);
                }

                _progressBar.Value = i + 1;
                await Task.Delay(50);
            }

            UpdateStatus($"处理完成！成功: {successCount}，失败: {failCount}");
            MessageBox.Show($"处理完成！\n成功: {successCount}\n失败: {failCount}", "完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"处理过程中发生错误: {ex.Message}", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _processBtn.Enabled = true;
        }
    }

    private async Task ProcessRename()
    {
        var options = new RenameOptions
        {
            Prefix = _renamePrefix?.Text ?? string.Empty,
            Suffix = _renameSuffix?.Text ?? string.Empty,
            UseNumbering = _renameUseNumber?.Checked ?? true,
            StartNumber = (int)(_renameStartNum?.Value ?? 1),
            NumberPadding = (int)(_renamePad?.Value ?? 3),
            UseRegex = _renameUseRegex?.Checked ?? false,
            RegexPattern = _renamePattern?.Text ?? string.Empty,
            RegexReplacement = _renameReplacement?.Text ?? string.Empty,
            KeepOriginalExtension = true
        };

        var useCopyMode = _renameCopyMode?.Checked ?? true;
        var outputDir = _renameOutputDir?.Text ?? string.Empty;

        if (useCopyMode && string.IsNullOrWhiteSpace(outputDir))
        {
            MessageBox.Show("请选择输出目录", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        if (useCopyMode)
        {
            Directory.CreateDirectory(outputDir);
        }

        _processBtn!.Enabled = false;
        _progressBar!.Maximum = _imageFiles.Count;
        _progressBar.Value = 0;

        int successCount = 0;
        int failCount = 0;

        try
        {
            if (useCopyMode)
            {
                RenameWorker.RenameToNewFolder(_imageFiles, outputDir, options, true);
                successCount = _imageFiles.Count;
                _progressBar.Value = _imageFiles.Count;
            }
            else
            {
                var names = RenameWorker.GenerateNewNames(_imageFiles, options);
                for (int i = 0; i < names.Count; i++)
                {
                    UpdateStatus($"正在重命名: {Path.GetFileName(names[i].OriginalPath)}");

                    try
                    {
                        RenameWorker.Rename(names[i].OriginalPath, names[i].NewPath, true);
                        successCount++;
                    }
                    catch (Exception ex)
                    {
                        failCount++;
                        UpdateStatus($"重命名失败: {Path.GetFileName(names[i].OriginalPath)} - {ex.Message}");
                        await Task.Delay(300);
                    }

                    _progressBar.Value = i + 1;
                    await Task.Delay(30);
                }
            }

            _imageFiles.Clear();
            _fileListBox?.Items.Clear();
            UpdateFileCount();

            UpdateStatus($"重命名完成！成功: {successCount}，失败: {failCount}");
            MessageBox.Show($"重命名完成！\n成功: {successCount}\n失败: {failCount}", "完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"处理过程中发生错误: {ex.Message}", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _processBtn.Enabled = true;
        }
    }

    private async Task ProcessExifRemoval()
    {
        var outputDir = _exifOutputDir?.Text ?? string.Empty;
        if (string.IsNullOrWhiteSpace(outputDir))
        {
            MessageBox.Show("请选择输出目录", "提示", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        Directory.CreateDirectory(outputDir);

        _processBtn!.Enabled = false;
        _progressBar!.Maximum = _imageFiles.Count;
        _progressBar.Value = 0;

        int successCount = 0;
        int failCount = 0;

        var options = new ExifRemoveOptions
        {
            RemoveAllExif = _exifRemoveAll?.Checked ?? true,
            RemoveIptc = _exifRemoveIptc?.Checked ?? true,
            RemoveXmp = _exifRemoveXmp?.Checked ?? true,
            RemoveColorProfile = _exifRemoveProfile?.Checked ?? false
        };

        try
        {
            for (int i = 0; i < _imageFiles.Count; i++)
            {
                var inputPath = _imageFiles[i];
                var fileName = Path.GetFileName(inputPath);
                var outputPath = Path.Combine(outputDir, fileName);

                UpdateStatus($"正在处理: {fileName} ({i + 1}/{_imageFiles.Count})");

                try
                {
                    ExifRemover.RemoveExif(inputPath, outputPath, options);
                    successCount++;
                }
                catch (Exception ex)
                {
                    failCount++;
                    UpdateStatus($"处理失败: {fileName} - {ex.Message}");
                    await Task.Delay(500);
                }

                _progressBar.Value = i + 1;
                await Task.Delay(50);
            }

            UpdateStatus($"EXIF 删除完成！成功: {successCount}，失败: {failCount}");
            MessageBox.Show($"EXIF 删除完成！\n成功: {successCount}\n失败: {failCount}\n\n使用引擎: {(ExifRemover.HasMagickNet ? "ImageMagick" : "GDI+ 回退")}", "完成", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show($"处理过程中发生错误: {ex.Message}", "错误", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        finally
        {
            _processBtn.Enabled = true;
        }
    }

    private Image ProcessSingleImage(Image image, ResizeOptions resizeOptions, WatermarkOptions watermarkOptions)
    {
        var resized = ResizeWorker.Resize(image, resizeOptions);

        if (!string.IsNullOrWhiteSpace(watermarkOptions.Text))
        {
            resized = Watermark.AddWatermark(resized, watermarkOptions);
        }

        return resized;
    }

    private void SaveImage(Image image, string path, string ext)
    {
        var saveFormat = GetImageFormatFromExtension(ext);
        FormatConverter.ConvertWithQuality(image, path, saveFormat, 90);
    }

    private string? GetTargetExtension(int index)
    {
        return index switch
        {
            1 => ".jpg",
            2 => ".png",
            3 => ".bmp",
            4 => ".gif",
            5 => ".tiff",
            6 => ".webp",
            _ => null
        };
    }

    private WatermarkPosition ParsePosition(int index)
    {
        return index switch
        {
            0 => WatermarkPosition.BottomRight,
            1 => WatermarkPosition.TopRight,
            2 => WatermarkPosition.BottomLeft,
            3 => WatermarkPosition.TopLeft,
            4 => WatermarkPosition.Center,
            _ => WatermarkPosition.BottomRight
        };
    }

    private ImageFormat GetImageFormatFromExtension(string ext)
    {
        return ext.ToLower() switch
        {
            ".jpg" or ".jpeg" => ImageFormat.Jpeg,
            ".png" => ImageFormat.Png,
            ".bmp" => ImageFormat.Bmp,
            ".gif" => ImageFormat.Gif,
            ".tiff" or ".tif" => ImageFormat.Tiff,
            _ => ImageFormat.Jpeg
        };
    }

    private bool HasResizeOrWatermark(ResizeOptions resizeOptions, WatermarkOptions watermarkOptions, string inputPath)
    {
        if (!string.IsNullOrWhiteSpace(watermarkOptions.Text))
        {
            return true;
        }

        try
        {
            using var image = Image.FromFile(inputPath);
            if (image.Width != resizeOptions.Width || image.Height != resizeOptions.Height)
            {
                return true;
            }
        }
        catch
        {
            return true;
        }

        return false;
    }

    private void UpdateStatus(string message)
    {
        if (_statusLabel != null)
        {
            _statusLabel.Text = message;
        }
    }
}

public class ResizeOptions
{
    public int Width { get; set; }
    public int Height { get; set; }
    public bool KeepAspectRatio { get; set; }
}

public enum WatermarkPosition
{
    TopLeft,
    TopRight,
    BottomLeft,
    BottomRight,
    Center
}

public class WatermarkOptions
{
    public string Text { get; set; } = string.Empty;
    public WatermarkPosition Position { get; set; }
    public int Opacity { get; set; }
}
