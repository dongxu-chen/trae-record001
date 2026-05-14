object FormExcel: TFormExcel
  Left = 0
  Top = 0
  Caption = 'Excel 导入导出'
  ClientHeight = 500
  ClientWidth = 750
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
    Width = 750
    Height = 120
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object GroupBox1: TGroupBox
      Left = 10
      Top = 10
      Width = 360
      Height = 100
      Caption = '操作类型'
      TabOrder = 0
      object rbImportStudent: TRadioButton
        Left = 20
        Top = 30
        Width = 120
        Height = 17
        Caption = '导入学生信息'
        TabOrder = 0
      end
      object rbImportGrade: TRadioButton
        Left = 20
        Top = 55
        Width = 120
        Height = 17
        Caption = '导入成绩信息'
        TabOrder = 1
      end
      object rbExportStudent: TRadioButton
        Left = 180
        Top = 30
        Width = 120
        Height = 17
        Caption = '导出学生信息'
        Checked = True
        TabOrder = 2
        TabStop = True
      end
      object rbExportGrade: TRadioButton
        Left = 180
        Top = 55
        Width = 120
        Height = 17
        Caption = '导出成绩信息'
        TabOrder = 3
      end
    end
    object Panel2: TPanel
      Left = 380
      Top = 10
      Width = 360
      Height = 100
      BevelOuter = bvNone
      TabOrder = 1
      object Label1: TLabel
        Left = 10
        Top = 15
        Width = 48
        Height = 13
        Caption = '文件路径:'
      end
      object edtFileName: TEdit
        Left = 10
        Top = 34
        Width = 260
        Height = 21
        TabOrder = 0
      end
      object btnBrowse: TButton
        Left = 276
        Top = 32
        Width = 75
        Height = 25
        Caption = '浏览...'
        TabOrder = 1
        OnClick = btnBrowseClick
      end
      object ProgressBar1: TProgressBar
        Left = 10
        Top = 65
        Width = 340
        Height = 20
        TabOrder = 2
      end
    end
  end
  object GroupBox2: TGroupBox
    Left = 10
    Top = 130
    Width = 730
    Height = 300
    Caption = '操作日志'
    TabOrder = 1
    object Memo1: TMemo
      Left = 10
      Top = 20
      Width = 710
      Height = 270
      ScrollBars = ssBoth
      TabOrder = 0
    end
  end
  object btnExecute: TButton
    Left = 520
    Top = 440
    Width = 90
    Height = 35
    Caption = '执行'
    TabOrder = 2
    OnClick = btnExecuteClick
  end
  object btnClose: TButton
    Left = 630
    Top = 440
    Width = 90
    Height = 35
    Caption = '关闭'
    TabOrder = 3
    OnClick = btnCloseClick
  end
  object dlgOpen: TOpenDialog
    Left = 24
    Top = 24
  end
  object dlgSave: TSaveDialog
    Left = 72
    Top = 24
  end
end
