object FormChart: TFormChart
  Left = 0
  Top = 0
  Caption = '数据分析图表'
  ClientHeight = 600
  ClientWidth = 900
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -11
  Font.Name = 'Tahoma'
  Font.Style = []
  OldCreateOrder = False
  OnCreate = FormCreate
  PixelsPerInch = 96
  TextHeight = 13
  object Panel1: TPanel
    Left = 0
    Top = 0
    Width = 900
    Height = 120
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object GroupBox1: TGroupBox
      Left = 10
      Top = 10
      Width = 500
      Height = 100
      Caption = '图表类型'
      TabOrder = 0
      object rbChartType1: TRadioButton
        Left = 20
        Top = 30
        Width = 150
        Height = 17
        Caption = '成绩分数段分布'
        Checked = True
        TabOrder = 0
        TabStop = True
      end
      object rbChartType2: TRadioButton
        Left = 20
        Top = 55
        Width = 150
        Height = 17
        Caption = '学生平均分对比'
        TabOrder = 1
      end
      object rbChartType3: TRadioButton
        Left = 180
        Top = 30
        Width = 150
        Height = 17
        Caption = '班级平均分对比'
        TabOrder = 2
      end
      object rbChartType4: TRadioButton
        Left = 180
        Top = 55
        Width = 150
        Height = 17
        Caption = '各课程平均分对比'
        TabOrder = 3
      end
    end
    object Label1: TLabel
      Left = 520
      Top = 30
      Width = 36
      Height = 13
      Caption = '班级:'
    end
    object cboClass: TComboBox
      Left = 560
      Top = 26
      Width = 150
      Height = 21
      TabOrder = 1
      Text = 'cboClass'
    end
    object chkAllClasses: TCheckBox
      Left = 520
      Top = 55
      Width = 97
      Height = 17
      Caption = '所有班级'
      Checked = True
      State = cbChecked
      TabOrder = 2
      OnClick = chkAllClassesClick
    end
    object btnGenerate: TButton
      Left = 720
      Top = 20
      Width = 90
      Height = 35
      Caption = '生成图表'
      TabOrder = 3
      OnClick = btnGenerateClick
    end
    object btnExport: TButton
      Left = 720
      Top = 65
      Width = 90
      Height = 35
      Caption = '导出图表'
      TabOrder = 4
      OnClick = btnExportClick
    end
    object btnClose: TButton
      Left = 820
      Top = 40
      Width = 70
      Height = 35
      Caption = '关闭'
      TabOrder = 5
      OnClick = btnCloseClick
    end
  end
  object Panel2: TPanel
    Left = 0
    Top = 120
    Width = 900
    Height = 480
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 1
    object Chart1: TChart
      Left = 10
      Top = 10
      Width = 880
      Height = 460
      BackWall.Brush.Color = clWhite
      BackWall.Pen.Color = clGray
      Frame.Color = clGray
      Frame.Visible = False
      Legend.Visible = True
      Title.Font.Height = -13
      Title.Text.Strings = (
        '图表')
      View3D = False
      BackColor = 15189684
      Color = clWhite
      TabOrder = 0
    end
  end
  object dlgSaveChart: TSaveDialog
    Filter = 'PNG 图片|*.png|JPEG 图片|*.jpg|PDF 文件|*.pdf'
    Left = 24
    Top = 24
  end
end
