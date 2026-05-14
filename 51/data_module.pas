unit data_module;

interface

uses
  System.SysUtils, System.Classes, Data.DB, Datasnap.DBClient, Vcl.Dialogs;

type
  TDataModule1 = class(TDataModule)
    cdsStudents: TClientDataSet;
    cdsGrades: TClientDataSet;
    dsStudents: TDataSource;
    dsGrades: TDataSource;
    procedure DataModuleCreate(Sender: TObject);
    procedure DataModuleDestroy(Sender: TObject);
  private
    FDataPath: string;
    procedure InitDataSets;
    procedure LoadData;
    procedure SaveData;
  public
    procedure RefreshData;
    procedure SaveAllData;
  end;

var
  DataModule1: TDataModule1;

implementation

{%CLASSGROUP 'Vcl.Controls.TControl'}

{$R *.dfm}

procedure TDataModule1.DataModuleCreate(Sender: TObject);
begin
  FDataPath := ExtractFilePath(ParamStr(0));
  InitDataSets;
  LoadData;
end;

procedure TDataModule1.DataModuleDestroy(Sender: TObject);
begin
  SaveData;
end;

procedure TDataModule1.InitDataSets;
begin
  with cdsStudents do
  begin
    FieldDefs.Clear;
    FieldDefs.Add('StudentID', ftString, 20);
    FieldDefs.Add('StudentName', ftString, 50);
    FieldDefs.Add('Gender', ftString, 4);
    FieldDefs.Add('BirthDate', ftDate);
    FieldDefs.Add('Class', ftString, 30);
    FieldDefs.Add('Major', ftString, 50);
    CreateDataSet;
  end;

  with cdsGrades do
  begin
    FieldDefs.Clear;
    FieldDefs.Add('GradeID', ftInteger);
    FieldDefs.Add('StudentID', ftString, 20);
    FieldDefs.Add('CourseName', ftString, 50);
    FieldDefs.Add('Score', ftFloat);
    FieldDefs.Add('ExamDate', ftDate);
    FieldDefs.Add('Remark', ftString, 100);
    CreateDataSet;
  end;
end;

procedure TDataModule1.LoadData;
var
  StudentsFile, GradesFile: string;
begin
  StudentsFile := FDataPath + 'students.xml';
  GradesFile := FDataPath + 'grades.xml';

  if FileExists(StudentsFile) then
    cdsStudents.LoadFromFile(StudentsFile);

  if FileExists(GradesFile) then
    cdsGrades.LoadFromFile(GradesFile);
end;

procedure TDataModule1.SaveData;
begin
  try
    cdsStudents.SaveToFile(FDataPath + 'students.xml', dfXML);
    cdsGrades.SaveToFile(FDataPath + 'grades.xml', dfXML);
  except
    on E: Exception do
      ShowMessage('保存数据失败: ' + E.Message);
  end;
end;

procedure TDataModule1.RefreshData;
begin
  LoadData;
end;

procedure TDataModule1.SaveAllData;
begin
  SaveData;
end;

end.
