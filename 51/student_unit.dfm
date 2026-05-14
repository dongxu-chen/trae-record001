object FormStudent: TFormStudent
  Left = 0
  Top = 0
  Caption = '学生信息管理'
  ClientHeight = 530
  ClientWidth = 900
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
    Width = 900
    Height = 49
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 0
    object Label7: TLabel
      Left = 20
      Top = 16
      Width = 36
      Height = 13
      Caption = '搜索:'
    end
    object cboSearchField: TComboBox
      Left = 62
      Top = 12
      Width = 100
      Height = 21
      TabOrder = 0
      Text = '学号'
    end
    object edtSearch: TEdit
      Left = 168
      Top = 12
      Width = 200
      Height = 21
      TabOrder = 1
    end
    object btnSearch: TButton
      Left = 374
      Top = 10
      Width = 75
      Height = 25
      Caption = '搜索'
      TabOrder = 2
      OnClick = btnSearchClick
    end
  end
  object Panel2: TPanel
    Left = 0
    Top = 49
    Width = 900
    Height = 200
    Align = alTop
    BevelOuter = bvNone
    TabOrder = 1
    object DBGrid1: TDBGrid
      Left = 0
      Top = 0
      Width = 900
      Height = 200
      Align = alClient
      DataSource = DataModule1.dsStudents
      TabOrder = 0
      TitleFont.Charset = DEFAULT_CHARSET
      TitleFont.Color = clWindowText
      TitleFont.Height = -11
      TitleFont.Name = 'Tahoma'
      TitleFont.Style = []
      OnCellClick = DBGrid1CellClick
      Columns = <
        item
          Expanded = False
          FieldName = 'StudentID'
          Title.Caption = '学号'
          Width = 100
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'StudentName'
          Title.Caption = '姓名'
          Width = 80
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'Gender'
          Title.Caption = '性别'
          Width = 50
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'BirthDate'
          Title.Caption = '出生日期'
          Width = 100
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'Class'
          Title.Caption = '班级'
          Width = 100
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'Major'
          Title.Caption = '专业'
          Width = 150
          Visible = True
        end>
    end
  end
  object Panel3: TPanel
    Left = 0
    Top = 249
    Width = 900
    Height = 281
    Align = alClient
    BevelOuter = bvNone
    TabOrder = 2
    object GroupBox1: TGroupBox
      Left = 10
      Top = 10
      Width = 880
      Height = 175
      Caption = '学生信息'
      TabOrder = 0
      object Label1: TLabel
        Left = 20
        Top = 30
        Width = 36
        Height = 13
        Caption = '学号:'
      end
      object Label2: TLabel
        Left = 20
        Top = 70
        Width = 36
        Height = 13
        Caption = '姓名:'
      end
      object Label3: TLabel
        Left = 20
        Top = 110
        Width = 36
        Height = 13
        Caption = '性别:'
      end
      object Label4: TLabel
        Left = 250
        Top = 30
        Width = 48
        Height = 13
        Caption = '出生日期:'
      end
      object Label5: TLabel
        Left = 250
        Top = 70
        Width = 36
        Height = 13
        Caption = '班级:'
      end
      object Label6: TLabel
        Left = 250
        Top = 110
        Width = 36
        Height = 13
        Caption = '专业:'
      end
      object edtStudentID: TEdit
        Left = 70
        Top = 26
        Width = 140
        Height = 21
        TabOrder = 0
      end
      object edtStudentName: TEdit
        Left = 70
        Top = 66
        Width = 140
        Height = 21
        TabOrder = 1
      end
      object cboGender: TComboBox
        Left = 70
        Top = 106
        Width = 140
        Height = 21
        TabOrder = 2
        Text = '男'
      end
      object dtpBirthDate: TDateTimePicker
        Left = 310
        Top = 26
        Width = 140
        Height = 21
        Date = 45791.000000000000000000
        Format = 'yyyy-MM-dd'
        TabOrder = 3
      end
      object edtClass: TEdit
        Left = 310
        Top = 66
        Width = 200
        Height = 21
        TabOrder = 4
      end
      object edtMajor: TEdit
        Left = 310
        Top = 106
        Width = 200
        Height = 21
        TabOrder = 5
      end
    end
    object btnAdd: TButton
      Left = 180
      Top = 200
      Width = 90
      Height = 35
      Caption = '新增'
      TabOrder = 1
      OnClick = btnAddClick
    end
    object btnEdit: TButton
      Left = 290
      Top = 200
      Width = 90
      Height = 35
      Caption = '编辑'
      TabOrder = 2
      OnClick = btnEditClick
    end
    object btnDelete: TButton
      Left = 400
      Top = 200
      Width = 90
      Height = 35
      Caption = '删除'
      TabOrder = 3
      OnClick = btnDeleteClick
    end
    object btnSave: TButton
      Left = 510
      Top = 200
      Width = 90
      Height = 35
      Caption = '保存'
      TabOrder = 4
      OnClick = btnSaveClick
    end
    object btnCancel: TButton
      Left = 620
      Top = 200
      Width = 90
      Height = 35
      Caption = '取消'
      TabOrder = 5
      OnClick = btnCancelClick
    end
    object btnImport: TButton
      Left = 60
      Top = 200
      Width = 90
      Height = 35
      Caption = '导入'
      TabOrder = 6
      OnClick = btnImportClick
    end
    object btnExport: TButton
      Left = 730
      Top = 200
      Width = 90
      Height = 35
      Caption = '导出'
      TabOrder = 7
      OnClick = btnExportClick
    end
  end
end
