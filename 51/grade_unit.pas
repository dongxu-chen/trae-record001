unit grade_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.Grids, Vcl.DBGrids,
  Vcl.ExtCtrls, Vcl.ComCtrls, Data.DB, Datasnap.DBClient;

type
  TFormGrade = class(TForm)
    Panel1: TPanel;
    Panel2: TPanel;
    Panel3: TPanel;
    DBGrid1: TDBGrid;
    GroupBox1: TGroupBox;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    Label4: TLabel;
    Label5: TLabel;
    Label6: TLabel;
    cboStudent: TComboBox;
    edtCourse: TEdit;
    edtScore: TEdit;
    dtpExamDate: TDateTimePicker;
    edtRemark: TEdit;
    btnAdd: TButton;
    btnEdit: TButton;
    btnDelete: TButton;
    btnSave: TButton;
    btnCancel: TButton;
    Label7: TLabel;
    edtSearch: TEdit;
    btnSearch: TButton;
    cboSearchField: TComboBox;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure btnAddClick(Sender: TObject);
    procedure btnEditClick(Sender: TObject);
    procedure btnDeleteClick(Sender: TObject);
    procedure btnSaveClick(Sender: TObject);
    procedure btnCancelClick(Sender: TObject);
    procedure btnSearchClick(Sender: TObject);
    procedure DBGrid1CellClick(Column: TColumn);
  private
    FMode: (mBrowse, mAdd, mEdit);
    FCurrentGradeID: Integer;
    procedure SetMode(AMode: (mBrowse, mAdd, mEdit));
    procedure ClearEdits;
    procedure LoadEdits;
    procedure LoadStudentList;
    function ValidateInput: Boolean;
    function GetNextGradeID: Integer;
    function GetStudentID(const StudentDisplay: string): string;
    function GetStudentDisplay(const StudentID: string): string;
  public
  end;

var
  FormGrade: TFormGrade;

implementation

{$R *.dfm}

uses
  data_module;

procedure TFormGrade.FormCreate(Sender: TObject);
begin
  FCurrentGradeID := 0;
  LoadStudentList;
  cboSearchField.Items.Add('学生');
  cboSearchField.Items.Add('课程');
  cboSearchField.ItemIndex := 0;
  dtpExamDate.Date := Now;
  SetMode(mBrowse);
end;

procedure TFormGrade.FormClose(Sender: TObject; var Action: TCloseAction);
begin
  DataModule1.SaveAllData;
end;

procedure TFormGrade.LoadStudentList;
var
  BM: TBookmark;
begin
  cboStudent.Items.Clear;
  if DataModule1.cdsStudents.IsEmpty then Exit;
  BM := DataModule1.cdsStudents.GetBookmark;
  try
    DataModule1.cdsStudents.First;
    while not DataModule1.cdsStudents.Eof do
    begin
      cboStudent.Items.Add(
        DataModule1.cdsStudents.FieldByName('StudentID').AsString + ' - ' +
        DataModule1.cdsStudents.FieldByName('StudentName').AsString
      );
      DataModule1.cdsStudents.Next;
    end;
  finally
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
end;

function TFormGrade.GetStudentID(const StudentDisplay: string): string;
var
  P: Integer;
begin
  Result := '';
  P := Pos(' - ', StudentDisplay);
  if P > 0 then
    Result := Trim(Copy(StudentDisplay, 1, P - 1));
end;

function TFormGrade.GetStudentDisplay(const StudentID: string): string;
var
  BM: TBookmark;
begin
  Result := '';
  if DataModule1.cdsStudents.IsEmpty then Exit;
  BM := DataModule1.cdsStudents.GetBookmark;
  try
    DataModule1.cdsStudents.Filter := 'StudentID = ' + QuotedStr(StudentID);
    DataModule1.cdsStudents.Filtered := True;
    if not DataModule1.cdsStudents.IsEmpty then
      Result := DataModule1.cdsStudents.FieldByName('StudentID').AsString + ' - ' +
                DataModule1.cdsStudents.FieldByName('StudentName').AsString;
  finally
    DataModule1.cdsStudents.Filtered := False;
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
end;

procedure TFormGrade.SetMode(AMode: (mBrowse, mAdd, mEdit));
begin
  FMode := AMode;
  case AMode of
    mBrowse:
      begin
        cboStudent.Enabled := False;
        edtCourse.Enabled := False;
        edtScore.Enabled := False;
        dtpExamDate.Enabled := False;
        edtRemark.Enabled := False;
        btnAdd.Enabled := cboStudent.Items.Count > 0;
        btnEdit.Enabled := not DataModule1.cdsGrades.IsEmpty;
        btnDelete.Enabled := not DataModule1.cdsGrades.IsEmpty;
        btnSave.Enabled := False;
        btnCancel.Enabled := False;
        DBGrid1.Enabled := True;
      end;
    mAdd, mEdit:
      begin
        cboStudent.Enabled := AMode = mAdd;
        edtCourse.Enabled := True;
        edtScore.Enabled := True;
        dtpExamDate.Enabled := True;
        edtRemark.Enabled := True;
        btnAdd.Enabled := False;
        btnEdit.Enabled := False;
        btnDelete.Enabled := False;
        btnSave.Enabled := True;
        btnCancel.Enabled := True;
        DBGrid1.Enabled := False;
      end;
  end;
end;

procedure TFormGrade.ClearEdits;
begin
  cboStudent.ItemIndex := -1;
  edtCourse.Text := '';
  edtScore.Text := '';
  dtpExamDate.Date := Now;
  edtRemark.Text := '';
  FCurrentGradeID := 0;
end;

procedure TFormGrade.LoadEdits;
begin
  if DataModule1.cdsGrades.IsEmpty then Exit;
  FCurrentGradeID := DataModule1.cdsGrades.FieldByName('GradeID').AsInteger;
  cboStudent.Text := GetStudentDisplay(DataModule1.cdsGrades.FieldByName('StudentID').AsString);
  edtCourse.Text := DataModule1.cdsGrades.FieldByName('CourseName').AsString;
  edtScore.Text := DataModule1.cdsGrades.FieldByName('Score').AsString;
  if not DataModule1.cdsGrades.FieldByName('ExamDate').IsNull then
    dtpExamDate.Date := DataModule1.cdsGrades.FieldByName('ExamDate').AsDateTime
  else
    dtpExamDate.Date := Now;
  edtRemark.Text := DataModule1.cdsGrades.FieldByName('Remark').AsString;
end;

function TFormGrade.ValidateInput: Boolean;
var
  Score: Double;
begin
  Result := True;
  if cboStudent.ItemIndex = -1 then
  begin
    ShowMessage('请选择学生！');
    cboStudent.SetFocus;
    Result := False;
    Exit;
  end;
  if Trim(edtCourse.Text) = '' then
  begin
    ShowMessage('课程名称不能为空！');
    edtCourse.SetFocus;
    Result := False;
    Exit;
  end;
  if Trim(edtScore.Text) = '' then
  begin
    ShowMessage('成绩不能为空！');
    edtScore.SetFocus;
    Result := False;
    Exit;
  end;
  if not TryStrToFloat(Trim(edtScore.Text), Score) then
  begin
    ShowMessage('成绩必须是数字！');
    edtScore.SetFocus;
    Result := False;
    Exit;
  end;
  if (Score < 0) or (Score > 100) then
  begin
    ShowMessage('成绩必须在0-100之间！');
    edtScore.SetFocus;
    Result := False;
    Exit;
  end;
end;

function TFormGrade.GetNextGradeID: Integer;
var
  MaxID: Integer;
  BM: TBookmark;
begin
  MaxID := 0;
  if not DataModule1.cdsGrades.IsEmpty then
  begin
    BM := DataModule1.cdsGrades.GetBookmark;
    try
      DataModule1.cdsGrades.First;
      while not DataModule1.cdsGrades.Eof do
      begin
        if DataModule1.cdsGrades.FieldByName('GradeID').AsInteger > MaxID then
          MaxID := DataModule1.cdsGrades.FieldByName('GradeID').AsInteger;
        DataModule1.cdsGrades.Next;
      end;
    finally
      if DataModule1.cdsGrades.BookmarkValid(BM) then
        DataModule1.cdsGrades.GotoBookmark(BM);
      DataModule1.cdsGrades.FreeBookmark(BM);
    end;
  end;
  Result := MaxID + 1;
end;

procedure TFormGrade.btnAddClick(Sender: TObject);
begin
  ClearEdits;
  LoadStudentList;
  if cboStudent.Items.Count = 0 then
  begin
    ShowMessage('请先添加学生信息！');
    Exit;
  end;
  SetMode(mAdd);
  cboStudent.SetFocus;
end;

procedure TFormGrade.btnEditClick(Sender: TObject);
begin
  if DataModule1.cdsGrades.IsEmpty then Exit;
  LoadStudentList;
  SetMode(mEdit);
  edtCourse.SetFocus;
end;

procedure TFormGrade.btnDeleteClick(Sender: TObject);
begin
  if DataModule1.cdsGrades.IsEmpty then Exit;
  if MessageDlg('确定要删除该成绩记录吗？', mtConfirmation, [mbYes, mbNo], 0) = mrYes then
  begin
    DataModule1.cdsGrades.Delete;
    if DataModule1.cdsGrades.IsEmpty then
      ClearEdits
    else
      LoadEdits;
    SetMode(mBrowse);
  end;
end;

procedure TFormGrade.btnSaveClick(Sender: TObject);
begin
  if not ValidateInput then Exit;
  try
    if FMode = mAdd then
    begin
      DataModule1.cdsGrades.Append;
      DataModule1.cdsGrades.FieldByName('GradeID').AsInteger := GetNextGradeID;
      DataModule1.cdsGrades.FieldByName('StudentID').AsString := GetStudentID(cboStudent.Text);
    end
    else
    begin
      DataModule1.cdsGrades.Edit;
    end;
    DataModule1.cdsGrades.FieldByName('CourseName').AsString := Trim(edtCourse.Text);
    DataModule1.cdsGrades.FieldByName('Score').AsFloat := StrToFloat(Trim(edtScore.Text));
    DataModule1.cdsGrades.FieldByName('ExamDate').AsDateTime := dtpExamDate.Date;
    DataModule1.cdsGrades.FieldByName('Remark').AsString := Trim(edtRemark.Text);
    DataModule1.cdsGrades.Post;
    SetMode(mBrowse);
    ShowMessage('保存成功！');
  except
    on E: Exception do
    begin
      DataModule1.cdsGrades.Cancel;
      ShowMessage('保存失败: ' + E.Message);
    end;
  end;
end;

procedure TFormGrade.btnCancelClick(Sender: TObject);
begin
  if FMode = mAdd then
    ClearEdits
  else
    LoadEdits;
  SetMode(mBrowse);
end;

procedure TFormGrade.btnSearchClick(Sender: TObject);
var
  FilterStr: string;
  StudentID: string;
begin
  if Trim(edtSearch.Text) = '' then
  begin
    DataModule1.cdsGrades.Filter := '';
    DataModule1.cdsGrades.Filtered := False;
    Exit;
  end;
  if cboSearchField.ItemIndex = 0 then
  begin
    StudentID := GetStudentID(GetStudentDisplay(edtSearch.Text));
    if StudentID <> '' then
      FilterStr := 'StudentID = ' + QuotedStr(StudentID)
    else
      FilterStr := 'StudentID LIKE ' + QuotedStr('%' + edtSearch.Text + '%');
  end
  else
  begin
    FilterStr := 'CourseName LIKE ' + QuotedStr('%' + edtSearch.Text + '%');
  end;
  DataModule1.cdsGrades.Filter := FilterStr;
  DataModule1.cdsGrades.Filtered := True;
  if not DataModule1.cdsGrades.IsEmpty then
    LoadEdits
  else
    ClearEdits;
  SetMode(mBrowse);
end;

procedure TFormGrade.DBGrid1CellClick(Column: TColumn);
begin
  if FMode = mBrowse then
    LoadEdits;
end;

end.
