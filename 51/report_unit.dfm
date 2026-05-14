object FormReport: TFormReport
  Left = 0
  Top = 0
  Caption = '打印报表'
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
    Height = 150
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object GroupBox1: TGroupBox
      Left = 20
      Top = 10
      Width = 500
      Height = 130
      Caption = '报表类型'
      TabOrder = 0
      object rbStudentList: TRadioButton
        Left = 20
        Top = 30
        Width = 110
        Height = 17
        Caption = '学生信息列表'
        Checked = True
        TabOrder = 0
        TabStop = True
        OnClick = rbStudentListClick
      end
      object rbGradeList: TRadioButton
        Left = 20
        Top = 60
        Width = 110
        Height = 17
        Caption = '学生成绩列表'
        TabOrder = 1
        OnClick = rbStudentListClick
      end
      object rbStudentSummary: TRadioButton
        Left = 150
        Top = 30
        Width = 110
        Height = 17
        Caption = '学生成绩统计'
        TabOrder = 2
        OnClick = rbStudentListClick
      end
      object rbClassSummary: TRadioButton
        Left = 150
        Top = 60
        Width = 110
        Height = 17
        Caption = '班级成绩统计'
        TabOrder = 3
        OnClick = rbStudentListClick
      end
    end
    object chkFilter: TCheckBox
      Left = 540
      Top = 30
      Width = 97
      Height = 17
      Caption = '启用筛选条件'
      TabOrder = 1
      OnClick = chkFilterClick
    end
    object Label1: TLabel
      Left = 540
      Top = 60
      Width = 36
      Height = 13
      Caption = '学生:'
    end
    object cboStudent: TComboBox
      Left = 580
      Top = 56
      Width = 150
      Height = 21
      Enabled = False
      TabOrder = 2
      Text = '全部学生'
    end
    object Label2: TLabel
      Left = 540
      Top = 90
      Width = 36
      Height = 13
      Caption = '班级:'
    end
    object cboClass: TComboBox
      Left = 580
      Top = 86
      Width = 150
      Height = 21
      Enabled = False
      TabOrder = 3
      Text = '全部班级'
    end
    object btnPreview: TButton
      Left = 760
      Top = 40
      Width = 100
      Height = 35
      Caption = '生成预览'
      TabOrder = 4
      OnClick = btnPreviewClick
    end
    object btnPrint: TButton
      Left = 760
      Top = 85
      Width = 100
      Height = 35
      Caption = '打印报表'
      TabOrder = 5
      OnClick = btnPrintClick
    end
    object btnClose: TButton
      Left = 760
      Top = 130
      Width = 100
      Height = 25
      Caption = '关闭'
      TabOrder = 6
      OnClick = btnCloseClick
    end
  end
  object Panel2: TPanel
    Left = 0
    Top = 150
    Width = 900
    Height = 450
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 1
    object RichEdit1: TRichEdit
      Left = 10
      Top = 10
      Width = 880
      Height = 430
      Font.Charset = GB2312_CHARSET
      Font.Color = clWindowText
      Font.Height = -12
      Font.Name = 'Consolas'
      Font.Style = []
      Lines.Strings = (
        'RichEdit1')
      ParentFont = False
      ScrollBars = ssBoth
      TabOrder = 0
      WordWrap = False
    end
  end
end
