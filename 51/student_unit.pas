unit student_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.Grids, Vcl.DBGrids,
  Vcl.ExtCtrls, Vcl.ComCtrls, Data.DB, Datasnap.DBClient, Vcl.Mask;

type
  TFormStudent = class(TForm)
    Panel1: TPanel;
    Panel2: TPanel;
    DBGrid1: TDBGrid;
    GroupBox1: TGroupBox;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    Label4: TLabel;
    Label5: TLabel;
    Label6: TLabel;
    edtStudentID: TEdit;
    edtStudentName: TEdit;
    cboGender: TComboBox;
    dtpBirthDate: TDateTimePicker;
    edtClass: TEdit;
    edtMajor: TEdit;
    Panel3: TPanel;
    btnAdd: TButton;
    btnEdit: TButton;
    btnDelete: TButton;
    btnSave: TButton;
    btnCancel: TButton;
    btnSearch: TButton;
    edtSearch: TEdit;
    Label7: TLabel;
    cboSearchField: TComboBox;
    btnImport: TButton;
    btnExport: TButton;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure btnAddClick(Sender: TObject);
    procedure btnEditClick(Sender: TObject);
    procedure btnDeleteClick(Sender: TObject);
    procedure btnSaveClick(Sender: TObject);
    procedure btnCancelClick(Sender: TObject);
    procedure btnSearchClick(Sender: TObject);
    procedure DBGrid1CellClick(Column: TColumn);
    procedure btnImportClick(Sender: TObject);
    procedure btnExportClick(Sender: TObject);
  private
    FMode: (mBrowse, mAdd, mEdit);
    procedure SetMode(AMode: (mBrowse, mAdd, mEdit));
    procedure ClearEdits;
    procedure LoadEdits;
    function ValidateInput: Boolean;
    function StudentIDExists(const AStudentID: string; ExcludeCurrent: Boolean = False): Boolean;
  public
  end;

var
  FormStudent: TFormStudent;

implementation

{$R *.dfm}

uses
  data_module, excel_unit;

procedure TFormStudent.FormCreate(Sender: TObject);
begin
  SetMode(mBrowse);
  cboGender.Items.Add('男');
  cboGender.Items.Add('女');
  cboSearchField.Items.Add('学号');
  cboSearchField.Items.Add('姓名');
  cboSearchField.Items.Add('班级');
  cboSearchField.ItemIndex := 0;
  cboGender.ItemIndex := 0;
  dtpBirthDate.Date := Now;
end;

procedure TFormStudent.FormClose(Sender: TObject; var Action: TCloseAction);
begin
  DataModule1.SaveAllData;
end;

procedure TFormStudent.SetMode(AMode: (mBrowse, mAdd, mEdit));
begin
  FMode := AMode;
  case AMode of
    mBrowse:
      begin
        edtStudentID.Enabled := False;
        edtStudentName.Enabled := False;
        cboGender.Enabled := False;
        dtpBirthDate.Enabled := False;
        edtClass.Enabled := False;
        edtMajor.Enabled := False;
        btnAdd.Enabled := True;
        btnEdit.Enabled := not DataModule1.cdsStudents.IsEmpty;
        btnDelete.Enabled := not DataModule1.cdsStudents.IsEmpty;
        btnSave.Enabled := False;
        btnCancel.Enabled := False;
        DBGrid1.Enabled := True;
      end;
    mAdd, mEdit:
      begin
        edtStudentID.Enabled := AMode = mAdd;
        edtStudentName.Enabled := True;
        cboGender.Enabled := True;
        dtpBirthDate.Enabled := True;
        edtClass.Enabled := True;
        edtMajor.Enabled := True;
        btnAdd.Enabled := False;
        btnEdit.Enabled := False;
        btnDelete.Enabled := False;
        btnSave.Enabled := True;
        btnCancel.Enabled := True;
        DBGrid1.Enabled := False;
      end;
  end;
end;

procedure TFormStudent.ClearEdits;
begin
  edtStudentID.Text := '';
  edtStudentName.Text := '';
  cboGender.ItemIndex := 0;
  dtpBirthDate.Date := Now;
  edtClass.Text := '';
  edtMajor.Text := '';
end;

procedure TFormStudent.LoadEdits;
begin
  if DataModule1.cdsStudents.IsEmpty then Exit;
  edtStudentID.Text := DataModule1.cdsStudents.FieldByName('StudentID').AsString;
  edtStudentName.Text := DataModule1.cdsStudents.FieldByName('StudentName').AsString;
  cboGender.Text := DataModule1.cdsStudents.FieldByName('Gender').AsString;
  if not DataModule1.cdsStudents.FieldByName('BirthDate').IsNull then
    dtpBirthDate.Date := DataModule1.cdsStudents.FieldByName('BirthDate').AsDateTime
  else
    dtpBirthDate.Date := Now;
  edtClass.Text := DataModule1.cdsStudents.FieldByName('Class').AsString;
  edtMajor.Text := DataModule1.cdsStudents.FieldByName('Major').AsString;
end;

function TFormStudent.ValidateInput: Boolean;
begin
  Result := True;
  if Trim(edtStudentID.Text) = '' then
  begin
    ShowMessage('学号不能为空！');
    edtStudentID.SetFocus;
    Result := False;
    Exit;
  end;
  if Trim(edtStudentName.Text) = '' then
  begin
    ShowMessage('姓名不能为空！');
    edtStudentName.SetFocus;
    Result := False;
    Exit;
  end;
  if FMode = mAdd then
  begin
    if StudentIDExists(Trim(edtStudentID.Text)) then
    begin
      ShowMessage('学号已存在！');
      edtStudentID.SetFocus;
      Result := False;
      Exit;
    end;
  end
  else
  begin
    if StudentIDExists(Trim(edtStudentID.Text), True) then
    begin
      ShowMessage('学号已存在！');
      edtStudentID.SetFocus;
      Result := False;
      Exit;
    end;
  end;
end;

function TFormStudent.StudentIDExists(const AStudentID: string; ExcludeCurrent: Boolean): Boolean;
var
  BM, CurrentBM: TBookmark;
begin
  Result := False;
  if DataModule1.cdsStudents.IsEmpty then Exit;
  BM := DataModule1.cdsStudents.GetBookmark;
  try
    if ExcludeCurrent and DataModule1.cdsStudents.BookmarkValid(BM) then
    begin
      CurrentBM := DataModule1.cdsStudents.GetBookmark;
      try
        DataModule1.cdsStudents.First;
        while not DataModule1.cdsStudents.Eof do
        begin
          if SameText(DataModule1.cdsStudents.FieldByName('StudentID').AsString, AStudentID) then
          begin
            if DataModule1.cdsStudents.CompareBookmarks(CurrentBM, DataModule1.cdsStudents.GetBookmark) = 0 then
            begin
              DataModule1.cdsStudents.Next;
              Continue;
            end;
            Result := True;
            Break;
          end;
          DataModule1.cdsStudents.Next;
        end;
      finally
        DataModule1.cdsStudents.FreeBookmark(CurrentBM);
      end;
    end
    else
    begin
      DataModule1.cdsStudents.First;
      while not DataModule1.cdsStudents.Eof do
      begin
        if SameText(DataModule1.cdsStudents.FieldByName('StudentID').AsString, AStudentID) then
        begin
          Result := True;
          Break;
        end;
        DataModule1.cdsStudents.Next;
      end;
    end;
  finally
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
end;

procedure TFormStudent.btnAddClick(Sender: TObject);
begin
  ClearEdits;
  SetMode(mAdd);
  edtStudentID.SetFocus;
end;

procedure TFormStudent.btnEditClick(Sender: TObject);
begin
  if DataModule1.cdsStudents.IsEmpty then Exit;
  SetMode(mEdit);
  edtStudentName.SetFocus;
end;

procedure TFormStudent.btnDeleteClick(Sender: TObject);
begin
  if DataModule1.cdsStudents.IsEmpty then Exit;
  if MessageDlg('确定要删除该学生信息吗？', mtConfirmation, [mbYes, mbNo], 0) = mrYes then
  begin
    DataModule1.cdsStudents.Delete;
    if DataModule1.cdsStudents.IsEmpty then
      ClearEdits
    else
      LoadEdits;
    SetMode(mBrowse);
  end;
end;

procedure TFormStudent.btnSaveClick(Sender: TObject);
begin
  if not ValidateInput then Exit;
  try
    if FMode = mAdd then
    begin
      DataModule1.cdsStudents.Append;
      DataModule1.cdsStudents.FieldByName('StudentID').AsString := Trim(edtStudentID.Text);
    end
    else
    begin
      DataModule1.cdsStudents.Edit;
    end;
    DataModule1.cdsStudents.FieldByName('StudentName').AsString := Trim(edtStudentName.Text);
    DataModule1.cdsStudents.FieldByName('Gender').AsString := cboGender.Text;
    DataModule1.cdsStudents.FieldByName('BirthDate').AsDateTime := dtpBirthDate.Date;
    DataModule1.cdsStudents.FieldByName('Class').AsString := Trim(edtClass.Text);
    DataModule1.cdsStudents.FieldByName('Major').AsString := Trim(edtMajor.Text);
    DataModule1.cdsStudents.Post;
    SetMode(mBrowse);
    ShowMessage('保存成功！');
  except
    on E: Exception do
    begin
      DataModule1.cdsStudents.Cancel;
      ShowMessage('保存失败: ' + E.Message);
    end;
  end;
end;

procedure TFormStudent.btnCancelClick(Sender: TObject);
begin
  if FMode = mAdd then
    ClearEdits
  else
    LoadEdits;
  SetMode(mBrowse);
end;

procedure TFormStudent.btnSearchClick(Sender: TObject);
var
  FilterStr: string;
begin
  if Trim(edtSearch.Text) = '' then
  begin
    DataModule1.cdsStudents.Filter := '';
    DataModule1.cdsStudents.Filtered := False;
    Exit;
  end;
  case cboSearchField.ItemIndex of
    0: FilterStr := 'StudentID = ' + QuotedStr(edtSearch.Text);
    1: FilterStr := 'StudentID LIKE ' + QuotedStr('%' + edtSearch.Text + '%');
    2: FilterStr := 'StudentName LIKE ' + QuotedStr('%' + edtSearch.Text + '%');
    3: FilterStr := 'Class LIKE ' + QuotedStr('%' + edtSearch.Text + '%');
  end;
  DataModule1.cdsStudents.Filter := FilterStr;
  DataModule1.cdsStudents.Filtered := True;
  if not DataModule1.cdsStudents.IsEmpty then
    LoadEdits
  else
    ClearEdits;
  SetMode(mBrowse);
end;

procedure TFormStudent.DBGrid1CellClick(Column: TColumn);
begin
  if FMode = mBrowse then
    LoadEdits;
end;

procedure TFormStudent.btnImportClick(Sender: TObject);
begin
  if not Assigned(FormExcel) then
    FormExcel := TFormExcel.Create(nil);
  FormExcel.rbImportStudent.Checked := True;
  FormExcel.rbExportStudent.Checked := False;
  FormExcel.ShowModal;
  FormExcel.Free;
  FormExcel := nil;
  DataModule1.RefreshData;
  LoadEdits;
end;

procedure TFormStudent.btnExportClick(Sender: TObject);
begin
  if not Assigned(FormExcel) then
    FormExcel := TFormExcel.Create(nil);
  FormExcel.rbExportStudent.Checked := True;
  FormExcel.rbImportStudent.Checked := False;
  FormExcel.ShowModal;
  FormExcel.Free;
  FormExcel := nil;
end;

end.
