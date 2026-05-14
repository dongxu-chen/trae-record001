object DataModule1: TDataModule
  Left = 192
  Top = 114
  Height = 271
  Width = 361
  object cdsStudents: TClientDataSet
    Aggregates = <>
    Params = <>
    Left = 32
    Top = 24
  end
  object cdsGrades: TClientDataSet
    Aggregates = <>
    Params = <>
    Left = 152
    Top = 24
  end
  object dsStudents: TDataSource
    DataSet = cdsStudents
    Left = 32
    Top = 96
  end
  object dsGrades: TDataSource
    DataSet = cdsGrades
    Left = 152
    Top = 96
  end
end
