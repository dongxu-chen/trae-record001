object FormMain: TFormMain
  Left = 0
  Top = 0
  Caption = '学生成绩管理系统'
  ClientHeight = 480
  ClientWidth = 950
  Color = clBtnFace
  Font.Charset = DEFAULT_CHARSET
  Font.Color = clWindowText
  Font.Height = -11
  Font.Name = 'Tahoma'
  Font.Style = []
  Menu = MainMenu1
  OldCreateOrder = False
  OnCreate = FormCreate
  PixelsPerInch = 96
  TextHeight = 13
  object Panel1: TPanel
    Left = 0
    Top = 63
    Width = 950
    Height = 46
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object Label1: TLabel
      Left = 20
      Top = 15
      Width = 680
      Height = 24
      Caption = '欢迎使用学生成绩管理系统 - 请从上方菜单或工具栏选择功能'
      Font.Charset = DEFAULT_CHARSET
      Font.Color = clWindowText
      Font.Height = -16
      Font.Name = 'Microsoft YaHei UI'
      Font.Style = []
      ParentFont = False
    end
  end
  object ToolBar1: TToolBar
    Left = 0
    Top = 30
    Width = 950
    Height = 33
    ButtonHeight = 29
    ButtonWidth = 90
    Caption = 'ToolBar1'
    Images = nil
    TabOrder = 1
    object ToolButton1: TToolButton
      Left = 0
      Top = 2
      Caption = '学生管理'
      OnClick = ToolButton1Click
    end
    object ToolButton2: TToolButton
      Left = 90
      Top = 2
      Caption = '成绩录入'
      OnClick = ToolButton2Click
    end
    object ToolButton3: TToolButton
      Left = 180
      Top = 2
      Caption = '报表打印'
      OnClick = ToolButton3Click
    end
    object ToolButton6: TToolButton
      Left = 270
      Top = 2
      Caption = '数据分析'
      OnClick = ToolButton6Click
    end
    object ToolButton5: TToolButton
      Left = 360
      Top = 2
      Caption = 'Excel导入导出'
      OnClick = ToolButton5Click
    end
    object ToolButton7: TToolButton
      Left = 450
      Top = 2
      Caption = '数据备份'
      OnClick = ToolButton7Click
    end
    object ToolButton4: TToolButton
      Left = 540
      Top = 2
      Caption = '保存数据'
      OnClick = ToolButton4Click
    end
    object ToolButton8: TToolButton
      Left = 630
      Top = 2
      Caption = '退出系统'
      OnClick = ToolButton8Click
    end
  end
  object StatusBar1: TStatusBar
    Left = 0
    Top = 461
    Width = 950
    Height = 19
    Panels = <
      item
        Text = '系统'
        Width = 150
      end
      item
        Text = '用户'
        Width = 150
      end
      item
        Text = '日期'
        Width = 100
      end>
  end
  object MainMenu1: TMainMenu
    Left = 24
    Top = 16
    object N1: TMenuItem
      Caption = '系统管理'
      object N2: TMenuItem
        Caption = '学生信息管理'
        OnClick = N2Click
      end
      object N3: TMenuItem
        Caption = '成绩录入管理'
        OnClick = N3Click
      end
      object N4: TMenuItem
        Caption = '打印报表'
        OnClick = N4Click
      end
      object N6: TMenuItem
        Caption = '数据分析图表'
        OnClick = N6Click
      end
      object N5: TMenuItem
        Caption = 'Excel导入导出'
        OnClick = N5Click
      end
      object N7: TMenuItem
        Caption = '数据备份恢复'
        OnClick = N7Click
      end
      object N8: TMenuItem
        Caption = '退出'
        OnClick = N8Click
      end
    end
  end
end
