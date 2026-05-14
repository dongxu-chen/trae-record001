program StudentGradeSystem;

uses
  Vcl.Forms,
  main in 'main.pas' {FormMain},
  student_unit in 'student_unit.pas' {FormStudent},
  grade_unit in 'grade_unit.pas' {FormGrade},
  report_unit in 'report_unit.pas' {FormReport},
  data_module in 'data_module.pas' {DataModule1: TDataModule},
  excel_unit in 'excel_unit.pas' {FormExcel},
  chart_unit in 'chart_unit.pas' {FormChart},
  backup_unit in 'backup_unit.pas' {FormBackup};

{$R *.res}

begin
  Application.Initialize;
  Application.MainFormOnTaskbar := True;
  Application.CreateForm(TFormMain, FormMain);
  Application.CreateForm(TDataModule1, DataModule1);
  Application.Run;
end.
