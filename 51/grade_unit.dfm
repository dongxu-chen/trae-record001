object FormGrade: TFormGrade
  Left = 0
  Top = 0
  Caption = '成绩录入管理'
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
      Text = '学生'
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
      DataSource = DataModule1.dsGrades
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
          FieldName = 'CourseName'
          Title.Caption = '课程'
          Width = 150
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'Score'
          Title.Caption = '成绩'
          Width = 80
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'ExamDate'
          Title.Caption = '考试日期'
          Width = 100
          Visible = True
        end
        item
          Expanded = False
          FieldName = 'Remark'
          Title.Caption = '备注'
          Width = 200
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
      Caption = '成绩信息'
      TabOrder = 0
      object Label1: TLabel
        Left = 20
        Top = 30
        Width = 36
        Height = 13
        Caption = '学生:'
      end
      object Label2: TLabel
        Left = 20
        Top = 70
        Width = 48
        Height = 13
        Caption = '课程名称:'
      end
      object Label3: TLabel
        Left = 20
        Top = 110
        Width = 36
        Height = 13
        Caption = '成绩:'
      end
      object Label4: TLabel
        Left = 300
        Top = 30
        Width = 54
        Height = 13
        Caption = '考试日期:'
      end
      object Label5: TLabel
        Left = 300
        Top = 70
        Width = 36
        Height = 13
        Caption = '备注:'
      end
      object Label6: TLabel
        Left = 36
        Top = 110
        Width = 0
        Height = 13
      end
      object cboStudent: TComboBox
        Left = 70
        Top = 26
        Width = 200
        Height = 21
        TabOrder = 0
        Text = '请选择学生'
      end
      object edtCourse: TEdit
        Left = 74
        Top = 66
        Width = 200
        Height = 21
        TabOrder = 1
      end
      object edtScore: TEdit
        Left = 70
        Top = 106
        Width = 100
        Height = 21
        TabOrder = 2
      end
      object dtpExamDate: TDateTimePicker
        Left = 360
        Top = 26
        Width = 140
        Height = 21
        Date = 45791.000000000000000000
        Format = 'yyyy-MM-dd'
        TabOrder = 3
      end
      object edtRemark: TEdit
        Left = 360
        Top = 66
        Width = 300
        Height = 21
        TabOrder = 4
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
  end
end
