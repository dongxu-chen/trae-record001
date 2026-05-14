unit excel_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.ExtCtrls,
  Vcl.ComCtrls, Data.DB, Datasnap.DBClient, Vcl.OleServer,
  Vcl.OleCtrls, Excel2000, System.Win.ComObj;

type
  TFormExcel = class(TForm)
    Panel1: TPanel;
    GroupBox1: TGroupBox;
    rbImportStudent: TRadioButton;
    rbImportGrade: TRadioButton;
    rbExportStudent: TRadioButton;
    rbExportGrade: TRadioButton;
    Panel2: TPanel;
    edtFileName: TEdit;
    btnBrowse: TButton;
    Label1: TLabel;
    ProgressBar1: TProgressBar;
    btnExecute: TButton;
    btnClose: TButton;
    GroupBox2: TGroupBox;
    Memo1: TMemo;
    dlgOpen: TOpenDialog;
    dlgSave: TSaveDialog;
    procedure btnBrowseClick(Sender: TObject);
    procedure btnExecuteClick(Sender: TObject);
    procedure btnCloseClick(Sender: TObject);
    procedure FormCreate(Sender: TObject);
  private
    procedure ExportToExcel(const IsStudent: Boolean);
    procedure ImportFromExcel(const IsStudent: Boolean);
    procedure AddLog(const Msg: string);
    function GetExcelApp: Variant;
    procedure ReleaseExcelApp(const ExcelApp: Variant);
  public
  end;

var
  FormExcel: TFormExcel;

implementation

{$R *.dfm}

uses
  data_module;

procedure TFormExcel.FormCreate(Sender: TObject);
begin
  rbExportStudent.Checked := True;
  Memo1.Clear;
  ProgressBar1.Position := 0;
  dlgOpen.Filter := 'Excel 文件|*.xls;*.xlsx';
  dlgSave.Filter := 'Excel 文件|*.xlsx';
end;

procedure TFormExcel.AddLog(const Msg: string);
begin
  Memo1.Lines.Add(FormatDateTime('hh:nn:ss', Now) + ' - ' + Msg);
  Memo1.SelStart := Length(Memo1.Text);
  Application.ProcessMessages;
end;

function TFormExcel.GetExcelApp: Variant;
begin
  try
    Result := GetActiveOleObject('Excel.Application');
  except
    Result := CreateOleObject('Excel.Application');
  end;
end;

procedure TFormExcel.ReleaseExcelApp(const ExcelApp: Variant);
begin
  try
    ExcelApp.Quit;
  except
  end;
end;

procedure TFormExcel.btnBrowseClick(Sender: TObject);
begin
  if rbImportStudent.Checked or rbImportGrade.Checked then
  begin
    if dlgOpen.Execute then
      edtFileName.Text := dlgOpen.FileName;
  end
  else
  begin
    if rbExportStudent.Checked then
      dlgSave.FileName := '学生信息_' + FormatDateTime('yyyymmdd', Now) + '.xlsx'
    else
      dlgSave.FileName := '成绩信息_' + FormatDateTime('yyyymmdd', Now) + '.xlsx';

    if dlgSave.Execute then
      edtFileName.Text := dlgSave.FileName;
  end;
end;

procedure TFormExcel.btnExecuteClick(Sender: TObject);
begin
  if Trim(edtFileName.Text) = '' then
  begin
    ShowMessage('请选择文件路径！');
    btnBrowse.SetFocus;
    Exit;
  end;

  Screen.Cursor := crHourGlass;
  try
    if rbImportStudent.Checked then
      ImportFromExcel(True)
    else if rbImportGrade.Checked then
      ImportFromExcel(False)
    else if rbExportStudent.Checked then
      ExportToExcel(True)
    else if rbExportGrade.Checked then
      ExportToExcel(False);
  finally
    Screen.Cursor := crDefault;
    ProgressBar1.Position := 0;
  end;
end;

procedure TFormExcel.ExportToExcel(const IsStudent: Boolean);
var
  ExcelApp, WorkBook, Sheet: Variant;
  CDS: TClientDataSet;
  i, j: Integer;
  Row: Integer;
  Headers: array of string;
begin
  AddLog('开始导出...');
  ExcelApp := GetExcelApp;
  try
    ExcelApp.Visible := False;
    ExcelApp.DisplayAlerts := False;
    WorkBook := ExcelApp.Workbooks.Add;
    Sheet := WorkBook.Worksheets[1];

    if IsStudent then
    begin
      CDS := DataModule1.cdsStudents;
      Headers := ['学号', '姓名', '性别', '出生日期', '班级', '专业'];
      Sheet.Name := '学生信息';
    end
    else
    begin
      CDS := DataModule1.cdsGrades;
      Headers := ['学号', '课程名称', '成绩', '考试日期', '备注'];
      Sheet.Name := '成绩信息';
    end;

    ProgressBar1.Max := CDS.RecordCount + 1;
    ProgressBar1.Position := 0;

    for i := 0 to High(Headers) do
      Sheet.Cells[1, i + 1] := Headers[i];

    Row := 2;
    CDS.First;
    while not CDS.Eof do
    begin
      if IsStudent then
      begin
        Sheet.Cells[Row, 1] := CDS.FieldByName('StudentID').AsString;
        Sheet.Cells[Row, 2] := CDS.FieldByName('StudentName').AsString;
        Sheet.Cells[Row, 3] := CDS.FieldByName('Gender').AsString;
        if not CDS.FieldByName('BirthDate').IsNull then
          Sheet.Cells[Row, 4] := FormatDateTime('yyyy-mm-dd', CDS.FieldByName('BirthDate').AsDateTime);
        Sheet.Cells[Row, 5] := CDS.FieldByName('Class').AsString;
        Sheet.Cells[Row, 6] := CDS.FieldByName('Major').AsString;
      end
      else
      begin
        Sheet.Cells[Row, 1] := CDS.FieldByName('StudentID').AsString;
        Sheet.Cells[Row, 2] := CDS.FieldByName('CourseName').AsString;
        Sheet.Cells[Row, 3] := CDS.FieldByName('Score').AsFloat;
        if not CDS.FieldByName('ExamDate').IsNull then
          Sheet.Cells[Row, 4] := FormatDateTime('yyyy-mm-dd', CDS.FieldByName('ExamDate').AsDateTime);
        Sheet.Cells[Row, 5] := CDS.FieldByName('Remark').AsString;
      end;

      Inc(Row);
      ProgressBar1.Position := ProgressBar1.Position + 1;
      CDS.Next;
    end;

    Sheet.Range['A1:F1'].Font.Bold := True;
    Sheet.Columns.AutoFit;

    WorkBook.SaveAs(edtFileName.Text);
    AddLog('导出完成！共 ' + IntToStr(CDS.RecordCount) + ' 条记录');
    ShowMessage('导出成功！文件: ' + edtFileName.Text);
  except
    on E: Exception do
    begin
      AddLog('导出失败: ' + E.Message);
      ShowMessage('导出失败: ' + E.Message);
    end;
  end;
  ReleaseExcelApp(ExcelApp);
end;

procedure TFormExcel.ImportFromExcel(const IsStudent: Boolean);
var
  ExcelApp, WorkBook, Sheet: Variant;
  Row, MaxRow: Integer;
  StudentID, StudentName, Gender, CourseName, Remark: string;
  BirthDate, ExamDate: TDateTime;
  Score: Double;
  BM: TBookmark;
  SuccessCount, FailCount: Integer;
begin
  AddLog('开始导入...');
  SuccessCount := 0;
  FailCount := 0;

  if not FileExists(edtFileName.Text) then
  begin
    ShowMessage('文件不存在！');
    Exit;
  end;

  ExcelApp := GetExcelApp;
  try
    ExcelApp.Visible := False;
    ExcelApp.DisplayAlerts := False;
    WorkBook := ExcelApp.Workbooks.Open(edtFileName.Text);
    Sheet := WorkBook.Worksheets[1];

    MaxRow := Sheet.UsedRange.Rows.Count;
    if MaxRow <= 1 then
    begin
      AddLog('Excel 中没有数据');
      ShowMessage('Excel 中没有数据！');
      Exit;
    end;

    ProgressBar1.Max := MaxRow;
    ProgressBar1.Position := 0;

    if IsStudent then
      DataModule1.cdsStudents.DisableControls
    else
      DataModule1.cdsGrades.DisableControls;

    try
      for Row := 2 to MaxRow do
      begin
        try
          if IsStudent then
          begin
            StudentID := VarToStr(Sheet.Cells[Row, 1].Value);
            if Trim(StudentID) = '' then Continue;

            StudentName := VarToStr(Sheet.Cells[Row, 2].Value);
            Gender := VarToStr(Sheet.Cells[Row, 3].Value);
            try
              BirthDate := VarToDateTime(Sheet.Cells[Row, 4].Value);
            except
              BirthDate := 0;
            end;

            BM := DataModule1.cdsStudents.GetBookmark;
            try
              DataModule1.cdsStudents.Filter := 'StudentID = ' + QuotedStr(StudentID);
              DataModule1.cdsStudents.Filtered := True;

              if DataModule1.cdsStudents.IsEmpty then
              begin
                DataModule1.cdsStudents.Append;
                DataModule1.cdsStudents.FieldByName('StudentID').AsString := StudentID;
              end
              else
              begin
                DataModule1.cdsStudents.Edit;
              end;

              DataModule1.cdsStudents.FieldByName('StudentName').AsString := StudentName;
              DataModule1.cdsStudents.FieldByName('Gender').AsString := Gender;
              if BirthDate <> 0 then
                DataModule1.cdsStudents.FieldByName('BirthDate').AsDateTime := BirthDate;
              DataModule1.cdsStudents.FieldByName('Class').AsString := VarToStr(Sheet.Cells[Row, 5].Value);
              DataModule1.cdsStudents.FieldByName('Major').AsString := VarToStr(Sheet.Cells[Row, 6].Value);
              DataModule1.cdsStudents.Post;
              Inc(SuccessCount);
            finally
              DataModule1.cdsStudents.Filtered := False;
              if DataModule1.cdsStudents.BookmarkValid(BM) then
                DataModule1.cdsStudents.GotoBookmark(BM);
              DataModule1.cdsStudents.FreeBookmark(BM);
            end;
          end
          else
          begin
            StudentID := VarToStr(Sheet.Cells[Row, 1].Value);
            if Trim(StudentID) = '' then Continue;

            CourseName := VarToStr(Sheet.Cells[Row, 2].Value);
            try
              Score := VarToFloat(Sheet.Cells[Row, 3].Value);
            except
              Score := 0;
            end;
            try
              ExamDate := VarToDateTime(Sheet.Cells[Row, 4].Value);
            except
              ExamDate := 0;
            end;
            Remark := VarToStr(Sheet.Cells[Row, 5].Value);

            DataModule1.cdsGrades.Append;
            DataModule1.cdsGrades.FieldByName('GradeID').AsInteger :=
              DataModule1.cdsGrades.RecordCount + 1;
            DataModule1.cdsGrades.FieldByName('StudentID').AsString := StudentID;
            DataModule1.cdsGrades.FieldByName('CourseName').AsString := CourseName;
            DataModule1.cdsGrades.FieldByName('Score').AsFloat := Score;
            if ExamDate <> 0 then
              DataModule1.cdsGrades.FieldByName('ExamDate').AsDateTime := ExamDate;
            DataModule1.cdsGrades.FieldByName('Remark').AsString := Remark;
            DataModule1.cdsGrades.Post;
            Inc(SuccessCount);
          end;
        except
          on E: Exception do
          begin
            Inc(FailCount);
            AddLog('第 ' + IntToStr(Row) + ' 行导入失败: ' + E.Message);
            if IsStudent then
            begin
              if DataModule1.cdsStudents.State in [dsEdit, dsInsert] then
                DataModule1.cdsStudents.Cancel;
            end
            else
            begin
              if DataModule1.cdsGrades.State in [dsEdit, dsInsert] then
                DataModule1.cdsGrades.Cancel;
            end;
          end;
        end;
        ProgressBar1.Position := Row;
      end;

      DataModule1.SaveAllData;
      AddLog(Format('导入完成！成功: %d 条, 失败: %d 条', [SuccessCount, FailCount]));
      ShowMessage(Format('导入完成！成功: %d 条, 失败: %d 条', [SuccessCount, FailCount]));
    finally
      if IsStudent then
        DataModule1.cdsStudents.EnableControls
      else
        DataModule1.cdsGrades.EnableControls;
    end;
  except
    on E: Exception do
    begin
      AddLog('导入失败: ' + E.Message);
      ShowMessage('导入失败: ' + E.Message);
    end;
  end;
  try
    WorkBook.Close;
  except
  end;
  ReleaseExcelApp(ExcelApp);
end;

procedure TFormExcel.btnCloseClick(Sender: TObject);
begin
  Close;
end;

end.
