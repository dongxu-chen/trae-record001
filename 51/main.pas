unit main;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.Menus, Vcl.ComCtrls, Vcl.ToolWin,
  Vcl.StdCtrls, Vcl.ExtCtrls;

type
  TFormMain = class(TForm)
    MainMenu1: TMainMenu;
    N1: TMenuItem;
    N2: TMenuItem;
    N3: TMenuItem;
    N4: TMenuItem;
    N5: TMenuItem;
    N6: TMenuItem;
    N7: TMenuItem;
    N8: TMenuItem;
    ToolBar1: TToolBar;
    ToolButton1: TToolButton;
    ToolButton2: TToolButton;
    ToolButton3: TToolButton;
    ToolButton4: TToolButton;
    ToolButton5: TToolButton;
    ToolButton6: TToolButton;
    ToolButton7: TToolButton;
    ToolButton8: TToolButton;
    StatusBar1: TStatusBar;
    Panel1: TPanel;
    Label1: TLabel;
    procedure N2Click(Sender: TObject);
    procedure N3Click(Sender: TObject);
    procedure N4Click(Sender: TObject);
    procedure N5Click(Sender: TObject);
    procedure N6Click(Sender: TObject);
    procedure N7Click(Sender: TObject);
    procedure N8Click(Sender: TObject);
    procedure ToolButton1Click(Sender: TObject);
    procedure ToolButton2Click(Sender: TObject);
    procedure ToolButton3Click(Sender: TObject);
    procedure ToolButton4Click(Sender: TObject);
    procedure ToolButton5Click(Sender: TObject);
    procedure ToolButton6Click(Sender: TObject);
    procedure ToolButton7Click(Sender: TObject);
    procedure ToolButton8Click(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private
    procedure ShowStudentForm;
    procedure ShowGradeForm;
    procedure ShowReportForm;
    procedure ShowExcelForm;
    procedure ShowChartForm;
    procedure ShowBackupForm;
    procedure SaveAllData;
    procedure ExitApp;
  public
  end;

var
  FormMain: TFormMain;

implementation

{$R *.dfm}

uses
  student_unit, grade_unit, report_unit, data_module,
  excel_unit, chart_unit, backup_unit;

procedure TFormMain.FormCreate(Sender: TObject);
begin
  StatusBar1.Panels[0].Text := '学生成绩管理系统 v1.0';
  StatusBar1.Panels[1].Text := '当前用户: 管理员';
  StatusBar1.Panels[2].Text := FormatDateTime('yyyy-mm-dd', Now);
end;

procedure TFormMain.ShowStudentForm;
begin
  if not Assigned(FormStudent) then
    FormStudent := TFormStudent.Create(nil);
  FormStudent.ShowModal;
  FormStudent.Free;
  FormStudent := nil;
end;

procedure TFormMain.ShowGradeForm;
begin
  if not Assigned(FormGrade) then
    FormGrade := TFormGrade.Create(nil);
  FormGrade.ShowModal;
  FormGrade.Free;
  FormGrade := nil;
end;

procedure TFormMain.ShowReportForm;
begin
  if not Assigned(FormReport) then
    FormReport := TFormReport.Create(nil);
  FormReport.ShowModal;
  FormReport.Free;
  FormReport := nil;
end;

procedure TFormMain.ShowExcelForm;
begin
  if not Assigned(FormExcel) then
    FormExcel := TFormExcel.Create(nil);
  FormExcel.ShowModal;
  FormExcel.Free;
  FormExcel := nil;
end;

procedure TFormMain.ShowChartForm;
begin
  if not Assigned(FormChart) then
    FormChart := TFormChart.Create(nil);
  FormChart.ShowModal;
  FormChart.Free;
  FormChart := nil;
end;

procedure TFormMain.ShowBackupForm;
begin
  if not Assigned(FormBackup) then
    FormBackup := TFormBackup.Create(nil);
  FormBackup.ShowModal;
  FormBackup.Free;
  FormBackup := nil;
end;

procedure TFormMain.SaveAllData;
begin
  if Assigned(DataModule1) then
  begin
    DataModule1.SaveAllData;
    ShowMessage('数据已保存！');
  end;
end;

procedure TFormMain.ExitApp;
begin
  if MessageDlg('确定要退出系统吗？', mtConfirmation, [mbYes, mbNo], 0) = mrYes then
    Close;
end;

procedure TFormMain.N2Click(Sender: TObject);
begin
  ShowStudentForm;
end;

procedure TFormMain.N3Click(Sender: TObject);
begin
  ShowGradeForm;
end;

procedure TFormMain.N4Click(Sender: TObject);
begin
  ShowReportForm;
end;

procedure TFormMain.N5Click(Sender: TObject);
begin
  ShowExcelForm;
end;

procedure TFormMain.N6Click(Sender: TObject);
begin
  ShowChartForm;
end;

procedure TFormMain.N7Click(Sender: TObject);
begin
  ShowBackupForm;
end;

procedure TFormMain.N8Click(Sender: TObject);
begin
  ExitApp;
end;

procedure TFormMain.ToolButton1Click(Sender: TObject);
begin
  ShowStudentForm;
end;

procedure TFormMain.ToolButton2Click(Sender: TObject);
begin
  ShowGradeForm;
end;

procedure TFormMain.ToolButton3Click(Sender: TObject);
begin
  ShowReportForm;
end;

procedure TFormMain.ToolButton4Click(Sender: TObject);
begin
  SaveAllData;
end;

procedure TFormMain.ToolButton5Click(Sender: TObject);
begin
  ShowExcelForm;
end;

procedure TFormMain.ToolButton6Click(Sender: TObject);
begin
  ShowChartForm;
end;

procedure TFormMain.ToolButton7Click(Sender: TObject);
begin
  ShowBackupForm;
end;

procedure TFormMain.ToolButton8Click(Sender: TObject);
begin
  ExitApp;
end;

end.
