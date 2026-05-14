object FormBackup: TFormBackup
  Left = 0
  Top = 0
  Caption = '数据备份恢复'
  ClientHeight = 520
  ClientWidth = 750
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -11
  Font.Name = 'Tahoma'
  Font.Style = []
  OldCreateOrder = False
  OnCreate = FormCreate
  OnClose = FormClose
  PixelsPerInch = 96
  TextHeight = 13
  object Panel1: TPanel
    Left = 0
    Top = 0
    Width = 750
    Height = 140
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object GroupBox1: TGroupBox
      Left = 10
      Top = 10
      Width = 730
      Height = 120
      Caption = '备份设置'
      TabOrder = 0
      object chkAutoBackup: TCheckBox
        Left = 20
        Top = 30
        Width = 97
        Height = 17
        Caption = '自动备份'
        TabOrder = 0
        OnClick = chkAutoBackupClick
      end
      object Label1: TLabel
        Left = 20
        Top = 55
        Width = 60
        Height = 13
        Caption = '备份路径:'
      end
      object edtBackupPath: TEdit
        Left = 20
        Top = 74
        Width = 400
        Height = 21
        TabOrder = 1
      end
      object btnBrowse: TButton
        Left = 426
        Top = 72
        Width = 75
        Height = 25
        Caption = '浏览...'
        TabOrder = 2
        OnClick = btnBrowseClick
      end
      object Label2: TLabel
        Left = 150
        Top = 30
        Width = 60
        Height = 13
        Caption = '备份间隔:'
      end
      object cboInterval: TComboBox
        Left = 210
        Top = 26
        Width = 100
        Height = 21
        TabOrder = 3
        Text = '1 小时'
      end
      object Label3: TLabel
        Left = 330
        Top = 30
        Width = 60
        Height = 13
        Caption = '保留天数:'
      end
      object spnKeepDays: TSpinEdit
        Left = 390
        Top = 26
        Width = 60
        Height = 22
        MaxValue = 365
        MinValue = 1
        TabOrder = 4
        Value = 30
      end
    end
  end
  object Panel2: TPanel
    Left = 0
    Top = 140
    Width = 750
    Height = 350
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 1
    object GroupBox2: TGroupBox
      Left = 10
      Top = 10
      Width = 730
      Height = 330
      Caption = '备份列表'
      TabOrder = 0
      object ListView1: TListView
        Left = 10
        Top = 20
        Width = 710
        Height = 260
        Columns = <
          item
            Caption = '备份名称'
            Width = 200
          end
          item
            Caption = '日期时间'
            Width = 150
          end
          item
            Caption = '大小'
            Width = 100
          end>
        GridLines = True
        HideSelection = False
        ViewStyle = vsReport
        TabOrder = 0
      end
      object btnBackupNow: TButton
        Left = 200
        Top = 290
        Width = 90
        Height = 30
        Caption = '立即备份'
        TabOrder = 1
        OnClick = btnBackupNowClick
      end
      object btnRestore: TButton
        Left = 310
        Top = 290
        Width = 90
        Height = 30
        Caption = '恢复数据'
        TabOrder = 2
        OnClick = btnRestoreClick
      end
      object btnDelete: TButton
        Left = 420
        Top = 290
        Width = 90
        Height = 30
        Caption = '删除备份'
        TabOrder = 3
        OnClick = btnDeleteClick
      end
      object btnClose: TButton
        Left = 530
        Top = 290
        Width = 90
        Height = 30
        Caption = '关闭'
        TabOrder = 4
        OnClick = btnCloseClick
      end
    end
  end
  object StatusBar1: TStatusBar
    Left = 0
    Top = 490
    Width = 750
    Height = 19
    Panels = <
      item
        Text = '自动备份已关闭'
        Width = 200
      end
      item
        Text = '保留天数: 30 天'
        Width = 150
      end
      item
        Text = '备份数量: 0'
        Width = 150
      end>
  end
  object dlgFolder: TFileOpenDialog
    FavoriteLinks = <>
    FileTypes = <>
    Options = [fdoPickFolders, fdoPathMustExist]
    Left = 24
    Top = 24
  end
  object dlgOpen: TOpenDialog
    Left = 72
    Top = 24
  end
  object Timer1: TTimer
    OnTimer = Timer1Timer
    Left = 120
    Top = 24
  end
end
