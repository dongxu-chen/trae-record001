unit report_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.Grids, Vcl.DBGrids,
  Vcl.ExtCtrls, Vcl.ComCtrls, Vcl.Printers, Data.DB, Datasnap.DBClient;

type
  TFormReport = class(TForm)
    Panel1: TPanel;
    Panel2: TPanel;
    GroupBox1: TGroupBox;
    rbStudentList: TRadioButton;
    rbGradeList: TRadioButton;
    rbStudentSummary: TRadioButton;
    rbClassSummary: TRadioButton;
    cboStudent: TComboBox;
    Label1: TLabel;
    cboClass: TComboBox;
    Label2: TLabel;
    chkFilter: TCheckBox;
    btnPreview: TButton;
    btnPrint: TButton;
    btnClose: TButton;
    RichEdit1: TRichEdit;
    procedure FormCreate(Sender: TObject);
    procedure btnPreviewClick(Sender: TObject);
    procedure btnPrintClick(Sender: TObject);
    procedure btnCloseClick(Sender: TObject);
    procedure chkFilterClick(Sender: TObject);
    procedure rbStudentListClick(Sender: TObject);
  private
    procedure LoadStudentList;
    procedure LoadClassList;
    procedure GenerateStudentListReport;
    procedure GenerateGradeListReport;
    procedure GenerateStudentSummaryReport;
    procedure GenerateClassSummaryReport;
    procedure PrintReport;
    procedure PrintPreview;
    function GetSelectedStudentID: string;
    function GetSelectedClassName: string;
    function GetStudentDisplay(const StudentID: string): string;
  public
  end;

var
  FormReport: TFormReport;

implementation

{$R *.dfm}

uses
  data_module;

procedure TFormReport.FormCreate(Sender: TObject);
begin
  LoadStudentList;
  LoadClassList;
  chkFilter.Checked := False;
  cboStudent.Enabled := False;
  cboClass.Enabled := False;
  rbStudentList.Checked := True;
  RichEdit1.Clear;
end;

procedure TFormReport.LoadStudentList;
var
  BM: TBookmark;
begin
  cboStudent.Items.Clear;
  cboStudent.Items.Add('全部学生');
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
  cboStudent.ItemIndex := 0;
end;

procedure TFormReport.LoadClassList;
var
  BM: TBookmark;
  ClassName: string;
begin
  cboClass.Items.Clear;
  cboClass.Items.Add('全部班级');
  if DataModule1.cdsStudents.IsEmpty then Exit;
  BM := DataModule1.cdsStudents.GetBookmark;
  try
    DataModule1.cdsStudents.First;
    while not DataModule1.cdsStudents.Eof do
    begin
      ClassName := DataModule1.cdsStudents.FieldByName('Class').AsString;
      if (Trim(ClassName) <> '') and (cboClass.Items.IndexOf(ClassName) = -1) then
        cboClass.Items.Add(ClassName);
      DataModule1.cdsStudents.Next;
    end;
  finally
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
  cboClass.ItemIndex := 0;
end;

function TFormReport.GetSelectedStudentID: string;
var
  P: Integer;
begin
  Result := '';
  if cboStudent.ItemIndex <= 0 then Exit;
  P := Pos(' - ', cboStudent.Text);
  if P > 0 then
    Result := Trim(Copy(cboStudent.Text, 1, P - 1));
end;

function TFormReport.GetSelectedClassName: string;
begin
  Result := '';
  if cboClass.ItemIndex <= 0 then Exit;
  Result := cboClass.Text;
end;

function TFormReport.GetStudentDisplay(const StudentID: string): string;
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
      Result := DataModule1.cdsStudents.FieldByName('StudentName').AsString;
  finally
    DataModule1.cdsStudents.Filtered := False;
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
end;

procedure TFormReport.GenerateStudentListReport;
var
  BM: TBookmark;
  Line: string;
  ClassFilter: string;
begin
  RichEdit1.Clear;
  RichEdit1.SelAttributes.Size := 16;
  RichEdit1.SelAttributes.Style := [fsBold];
  RichEdit1.Lines.Add('                         学生信息列表');
  RichEdit1.SelAttributes.Size := 10;
  RichEdit1.SelAttributes.Style := [];
  RichEdit1.Lines.Add('打印时间: ' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now));
  RichEdit1.Lines.Add('');
  RichEdit1.Lines.Add('================================================================================');
  RichEdit1.Lines.Add('  学号        姓名        性别    出生日期      班级          专业');
  RichEdit1.Lines.Add('================================================================================');

  if DataModule1.cdsStudents.IsEmpty then
  begin
    RichEdit1.Lines.Add('                     暂无学生数据');
    Exit;
  end;

  BM := DataModule1.cdsStudents.GetBookmark;
  try
    if chkFilter.Checked then
    begin
      ClassFilter := GetSelectedClassName;
      if ClassFilter <> '' then
      begin
        DataModule1.cdsStudents.Filter := 'Class = ' + QuotedStr(ClassFilter);
        DataModule1.cdsStudents.Filtered := True;
      end;
    end;

    DataModule1.cdsStudents.First;
    while not DataModule1.cdsStudents.Eof do
    begin
      Line := Format('  %-12s%-12s%-6s%-12s%-12s%s', [
        DataModule1.cdsStudents.FieldByName('StudentID').AsString,
        DataModule1.cdsStudents.FieldByName('StudentName').AsString,
        DataModule1.cdsStudents.FieldByName('Gender').AsString,
        FormatDateTime('yyyy-mm-dd', DataModule1.cdsStudents.FieldByName('BirthDate').AsDateTime),
        DataModule1.cdsStudents.FieldByName('Class').AsString,
        DataModule1.cdsStudents.FieldByName('Major').AsString
      ]);
      RichEdit1.Lines.Add(Line);
      DataModule1.cdsStudents.Next;
    end;
  finally
    DataModule1.cdsStudents.Filtered := False;
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
  RichEdit1.Lines.Add('================================================================================');
end;

procedure TFormReport.GenerateGradeListReport;
var
  BM: TBookmark;
  Line: string;
  StudentID: string;
begin
  RichEdit1.Clear;
  RichEdit1.SelAttributes.Size := 16;
  RichEdit1.SelAttributes.Style := [fsBold];
  RichEdit1.Lines.Add('                         学生成绩列表');
  RichEdit1.SelAttributes.Size := 10;
  RichEdit1.SelAttributes.Style := [];
  RichEdit1.Lines.Add('打印时间: ' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now));
  RichEdit1.Lines.Add('');
  RichEdit1.Lines.Add('================================================================================');
  RichEdit1.Lines.Add('  学号        姓名        课程名称              成绩    考试日期    备注');
  RichEdit1.Lines.Add('================================================================================');

  if DataModule1.cdsGrades.IsEmpty then
  begin
    RichEdit1.Lines.Add('                     暂无成绩数据');
    Exit;
  end;

  BM := DataModule1.cdsGrades.GetBookmark;
  try
    if chkFilter.Checked then
    begin
      StudentID := GetSelectedStudentID;
      if StudentID <> '' then
      begin
        DataModule1.cdsGrades.Filter := 'StudentID = ' + QuotedStr(StudentID);
        DataModule1.cdsGrades.Filtered := True;
      end;
    end;

    DataModule1.cdsGrades.First;
    while not DataModule1.cdsGrades.Eof do
    begin
      Line := Format('  %-12s%-12s%-22s%-6s%-12s%s', [
        DataModule1.cdsGrades.FieldByName('StudentID').AsString,
        GetStudentDisplay(DataModule1.cdsGrades.FieldByName('StudentID').AsString),
        DataModule1.cdsGrades.FieldByName('CourseName').AsString,
        FormatFloat('0.0', DataModule1.cdsGrades.FieldByName('Score').AsFloat),
        FormatDateTime('yyyy-mm-dd', DataModule1.cdsGrades.FieldByName('ExamDate').AsDateTime),
        DataModule1.cdsGrades.FieldByName('Remark').AsString
      ]);
      RichEdit1.Lines.Add(Line);
      DataModule1.cdsGrades.Next;
    end;
  finally
    DataModule1.cdsGrades.Filtered := False;
    if DataModule1.cdsGrades.BookmarkValid(BM) then
      DataModule1.cdsGrades.GotoBookmark(BM);
    DataModule1.cdsGrades.FreeBookmark(BM);
  end;
  RichEdit1.Lines.Add('================================================================================');
end;

procedure TFormReport.GenerateStudentSummaryReport;
var
  StudentID: string;
  TotalScore, AvgScore: Double;
  Count, PassCount, ExcellentCount: Integer;
  BM: TBookmark;
  Line: string;
  SelectedStudentID: string;
begin
  RichEdit1.Clear;
  RichEdit1.SelAttributes.Size := 16;
  RichEdit1.SelAttributes.Style := [fsBold];
  RichEdit1.Lines.Add('                         学生成绩统计');
  RichEdit1.SelAttributes.Size := 10;
  RichEdit1.SelAttributes.Style := [];
  RichEdit1.Lines.Add('打印时间: ' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now));
  RichEdit1.Lines.Add('');
  RichEdit1.Lines.Add('================================================================================');
  RichEdit1.Lines.Add('  学号        姓名        课程数  总分    平均分    及格  优秀    备注');
  RichEdit1.Lines.Add('================================================================================');

  if DataModule1.cdsStudents.IsEmpty then
  begin
    RichEdit1.Lines.Add('                     暂无数据');
    Exit;
  end;

  SelectedStudentID := '';
  if chkFilter.Checked then
    SelectedStudentID := GetSelectedStudentID;

  BM := DataModule1.cdsStudents.GetBookmark;
  try
    DataModule1.cdsStudents.First;
    while not DataModule1.cdsStudents.Eof do
    begin
      StudentID := DataModule1.cdsStudents.FieldByName('StudentID').AsString;

      if (SelectedStudentID <> '') and (SelectedStudentID <> StudentID) then
      begin
        DataModule1.cdsStudents.Next;
        Continue;
      end;

      TotalScore := 0;
      Count := 0;
      PassCount := 0;
      ExcellentCount := 0;

      with DataModule1.cdsGrades do
      begin
        First;
        while not Eof do
        begin
          if FieldByName('StudentID').AsString = StudentID then
          begin
            Inc(Count);
            TotalScore := TotalScore + FieldByName('Score').AsFloat;
            if FieldByName('Score').AsFloat >= 60 then Inc(PassCount);
            if FieldByName('Score').AsFloat >= 90 then Inc(ExcellentCount);
          end;
          Next;
        end;
      end;

      if Count > 0 then
      begin
        AvgScore := TotalScore / Count;
        Line := Format('  %-12s%-12s%-6s%-8s%-10s%-6s%-6s', [
          StudentID,
          DataModule1.cdsStudents.FieldByName('StudentName').AsString,
          IntToStr(Count),
          FormatFloat('0.0', TotalScore),
          FormatFloat('0.0', AvgScore),
          IntToStr(PassCount),
          IntToStr(ExcellentCount)
        ]);
      end
      else
      begin
        Line := Format('  %-12s%-12s%-6s%-8s%-10s%-6s%-6s(暂无成绩)', [
          StudentID,
          DataModule1.cdsStudents.FieldByName('StudentName').AsString,
          '0', '0.0', '0.0', '0', '0'
        ]);
      end;

      RichEdit1.Lines.Add(Line);
      DataModule1.cdsStudents.Next;
    end;
  finally
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
  RichEdit1.Lines.Add('================================================================================');
end;

procedure TFormReport.GenerateClassSummaryReport;
var
  ClassName: string;
  TotalStudents, TotalGrades: Integer;
  TotalScore, AvgScore: Double;
  PassCount, ExcellentCount: Integer;
  BM: TBookmark;
  Line: string;
  ClassList: TStringList;
  SelectedClass: string;
  i: Integer;
begin
  RichEdit1.Clear;
  RichEdit1.SelAttributes.Size := 16;
  RichEdit1.SelAttributes.Style := [fsBold];
  RichEdit1.Lines.Add('                         班级成绩统计');
  RichEdit1.SelAttributes.Size := 10;
  RichEdit1.SelAttributes.Style := [];
  RichEdit1.Lines.Add('打印时间: ' + FormatDateTime('yyyy-mm-dd hh:nn:ss', Now));
  RichEdit1.Lines.Add('');
  RichEdit1.Lines.Add('================================================================================');
  RichEdit1.Lines.Add('  班级            学生数  成绩数  平均分    及格数  优秀数');
  RichEdit1.Lines.Add('================================================================================');

  if DataModule1.cdsStudents.IsEmpty then
  begin
    RichEdit1.Lines.Add('                     暂无数据');
    Exit;
  end;

  ClassList := TStringList.Create;
  try
    BM := DataModule1.cdsStudents.GetBookmark;
    try
      DataModule1.cdsStudents.First;
      while not DataModule1.cdsStudents.Eof do
      begin
        ClassName := DataModule1.cdsStudents.FieldByName('Class').AsString;
        if Trim(ClassName) = '' then ClassName := '未分配班级';
        if ClassList.IndexOf(ClassName) = -1 then
          ClassList.Add(ClassName);
        DataModule1.cdsStudents.Next;
      end;
    finally
      if DataModule1.cdsStudents.BookmarkValid(BM) then
        DataModule1.cdsStudents.GotoBookmark(BM);
      DataModule1.cdsStudents.FreeBookmark(BM);
    end;

    SelectedClass := '';
    if chkFilter.Checked then
      SelectedClass := GetSelectedClassName;

    for i := 0 to ClassList.Count - 1 do
    begin
      ClassName := ClassList[i];
      if (SelectedClass <> '') and (SelectedClass <> ClassName) then Continue;

      TotalStudents := 0;
      TotalGrades := 0;
      TotalScore := 0;
      PassCount := 0;
      ExcellentCount := 0;

      BM := DataModule1.cdsStudents.GetBookmark;
      try
        DataModule1.cdsStudents.Filter := 'Class = ' + QuotedStr(ClassName);
        DataModule1.cdsStudents.Filtered := True;
        DataModule1.cdsStudents.First;
        while not DataModule1.cdsStudents.Eof do
        begin
          Inc(TotalStudents);
          with DataModule1.cdsGrades do
          begin
            First;
            while not Eof do
            begin
              if FieldByName('StudentID').AsString = DataModule1.cdsStudents.FieldByName('StudentID').AsString then
              begin
                Inc(TotalGrades);
                TotalScore := TotalScore + FieldByName('Score').AsFloat;
                if FieldByName('Score').AsFloat >= 60 then Inc(PassCount);
                if FieldByName('Score').AsFloat >= 90 then Inc(ExcellentCount);
              end;
              Next;
            end;
          end;
          DataModule1.cdsStudents.Next;
        end;
      finally
        DataModule1.cdsStudents.Filtered := False;
        if DataModule1.cdsStudents.BookmarkValid(BM) then
          DataModule1.cdsStudents.GotoBookmark(BM);
        DataModule1.cdsStudents.FreeBookmark(BM);
      end;

      if TotalGrades > 0 then
        AvgScore := TotalScore / TotalGrades
      else
        AvgScore := 0;

      Line := Format('  %-16s%-6s%-6s%-10s%-6s%-6s', [
        ClassName,
        IntToStr(TotalStudents),
        IntToStr(TotalGrades),
        FormatFloat('0.0', AvgScore),
        IntToStr(PassCount),
        IntToStr(ExcellentCount)
      ]);
      RichEdit1.Lines.Add(Line);
    end;
  finally
    ClassList.Free;
  end;
  RichEdit1.Lines.Add('================================================================================');
end;

procedure TFormReport.PrintPreview;
begin
  if RichEdit1.Lines.Count = 0 then
  begin
    ShowMessage('请先生成报表！');
    Exit;
  end;
  ShowMessage('预览模式: 报表内容已显示在文本框中，可直接查看。点击打印按钮可输出到打印机。');
end;

procedure TFormReport.PrintReport;
var
  i: Integer;
  Y: Integer;
  LineHeight: Integer;
begin
  if RichEdit1.Lines.Count = 0 then
  begin
    ShowMessage('请先生成报表！');
    Exit;
  end;

  with Printer do
  begin
    BeginDoc;
    try
      Canvas.Font.Name := 'Microsoft YaHei UI';
      Canvas.Font.Charset := GB2312_CHARSET;
      Canvas.Font.Size := 10;
      LineHeight := Canvas.TextHeight('中');
      Y := 50;

      for i := 0 to RichEdit1.Lines.Count - 1 do
      begin
        Canvas.TextOut(50, Y, RichEdit1.Lines[i]);
        Y := Y + LineHeight;

        if Y > (PageHeight - 100) then
        begin
          NewPage;
          Y := 50;
        end;
      end;
    finally
      EndDoc;
    end;
  end;
  ShowMessage('报表已发送到打印机！');
end;

procedure TFormReport.btnPreviewClick(Sender: TObject);
begin
  if rbStudentList.Checked then
    GenerateStudentListReport
  else if rbGradeList.Checked then
    GenerateGradeListReport
  else if rbStudentSummary.Checked then
    GenerateStudentSummaryReport
  else if rbClassSummary.Checked then
    GenerateClassSummaryReport;
end;

procedure TFormReport.btnPrintClick(Sender: TObject);
begin
  if RichEdit1.Lines.Count = 0 then
    btnPreviewClick(Sender);
  PrintReport;
end;

procedure TFormReport.btnCloseClick(Sender: TObject);
begin
  Close;
end;

procedure TFormReport.chkFilterClick(Sender: TObject);
begin
  cboStudent.Enabled := chkFilter.Checked and (rbGradeList.Checked or rbStudentSummary.Checked);
  cboClass.Enabled := chkFilter.Checked and (rbStudentList.Checked or rbClassSummary.Checked);
end;

procedure TFormReport.rbStudentListClick(Sender: TObject);
begin
  cboStudent.Enabled := chkFilter.Checked and (rbGradeList.Checked or rbStudentSummary.Checked);
  cboClass.Enabled := chkFilter.Checked and (rbStudentList.Checked or rbClassSummary.Checked);
end;

end.
