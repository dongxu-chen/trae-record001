unit chart_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.ExtCtrls, Vcl.ComCtrls,
  Data.DB, Datasnap.DBClient, VCLTee.TeeProcs, VCLTee.TeEngine,
  VCLTee.Series, VCLTee.Chart;

type
  TFormChart = class(TForm)
    Panel1: TPanel;
    Panel2: TPanel;
    GroupBox1: TGroupBox;
    rbChartType1: TRadioButton;
    rbChartType2: TRadioButton;
    rbChartType3: TRadioButton;
    rbChartType4: TRadioButton;
    cboClass: TComboBox;
    Label1: TLabel;
    chkAllClasses: TCheckBox;
    btnGenerate: TButton;
    btnExport: TButton;
    btnClose: TButton;
    Chart1: TChart;
    dlgSaveChart: TSaveDialog;
    procedure FormCreate(Sender: TObject);
    procedure btnGenerateClick(Sender: TObject);
    procedure btnExportClick(Sender: TObject);
    procedure btnCloseClick(Sender: TObject);
    procedure chkAllClassesClick(Sender: TObject);
  private
    procedure LoadClassList;
    procedure GenerateScoreDistribution;
    procedure GenerateStudentComparison;
    procedure GenerateClassComparison;
    procedure GenerateCourseComparison;
    procedure ClearChart;
    function GetClassNameList: TStringList;
  public
  end;

var
  FormChart: TFormChart;

implementation

{$R *.dfm}

uses
  data_module, VCLTee.TeeExport;

procedure TFormChart.FormCreate(Sender: TObject);
begin
  Chart1.View3D := False;
  Chart1.Title.Text.Clear;
  Chart1.Legend.Visible := True;
  Chart1.Axes.Left.Title.Text := '人数';
  Chart1.Axes.Bottom.Title.Text := '分数段';
  LoadClassList;
  dlgSaveChart.Filter := 'PNG 图片|*.png|JPEG 图片|*.jpg|PDF 文件|*.pdf';
end;

procedure TFormChart.LoadClassList;
var
  BM: TBookmark;
  ClassName: string;
begin
  cboClass.Items.Clear;
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
  if cboClass.Items.Count > 0 then
    cboClass.ItemIndex := 0;
  chkAllClasses.Checked := True;
  cboClass.Enabled := False;
end;

procedure TFormChart.chkAllClassesClick(Sender: TObject);
begin
  cboClass.Enabled := not chkAllClasses.Checked;
end;

procedure TFormChart.ClearChart;
begin
  Chart1.SeriesList.Clear;
  Chart1.Title.Text.Clear;
end;

function TFormChart.GetClassNameList: TStringList;
var
  i: Integer;
begin
  Result := TStringList.Create;
  if chkAllClasses.Checked then
  begin
    for i := 0 to cboClass.Items.Count - 1 do
      Result.Add(cboClass.Items[i]);
  end
  else
  begin
    if cboClass.ItemIndex >= 0 then
      Result.Add(cboClass.Text);
  end;
end;

procedure TFormChart.GenerateScoreDistribution;
var
  BarSeries: TBarSeries;
  BM, BM2: TBookmark;
  ClassName, StudentID: string;
  ClassList: TStringList;
  i, j: Integer;
  Scores: array[0..10] of Integer;
  Score: Double;
  RangeIndex: Integer;
begin
  ClearChart;
  Chart1.Title.Text.Add('成绩分数段分布统计');
  Chart1.Axes.Left.Title.Text := '人数';
  Chart1.Axes.Bottom.Title.Text := '分数段';

  ClassList := GetClassNameList;
  try
    for i := 0 to ClassList.Count - 1 do
    begin
      ClassName := ClassList[i];
      BarSeries := TBarSeries.Create(Chart1);
      BarSeries.Title := ClassName;
      BarSeries.Marks.Visible := True;
      Chart1.AddSeries(BarSeries);

      for j := 0 to 10 do
        Scores[j] := 0;

      BM := DataModule1.cdsStudents.GetBookmark;
      try
        DataModule1.cdsStudents.Filter := 'Class = ' + QuotedStr(ClassName);
        DataModule1.cdsStudents.Filtered := True;
        DataModule1.cdsStudents.First;

        while not DataModule1.cdsStudents.Eof do
        begin
          StudentID := DataModule1.cdsStudents.FieldByName('StudentID').AsString;

          BM2 := DataModule1.cdsGrades.GetBookmark;
          try
            DataModule1.cdsGrades.First;
            while not DataModule1.cdsGrades.Eof do
            begin
              if DataModule1.cdsGrades.FieldByName('StudentID').AsString = StudentID then
              begin
                Score := DataModule1.cdsGrades.FieldByName('Score').AsFloat;
                if Score >= 100 then
                  RangeIndex := 10
                else if Score >= 90 then
                  RangeIndex := 9
                else if Score >= 80 then
                  RangeIndex := 8
                else if Score >= 70 then
                  RangeIndex := 7
                else if Score >= 60 then
                  RangeIndex := 6
                else if Score >= 50 then
                  RangeIndex := 5
                else if Score >= 40 then
                  RangeIndex := 4
                else if Score >= 30 then
                  RangeIndex := 3
                else if Score >= 20 then
                  RangeIndex := 2
                else if Score >= 10 then
                  RangeIndex := 1
                else
                  RangeIndex := 0;
                Inc(Scores[RangeIndex]);
              end;
              DataModule1.cdsGrades.Next;
            end;
          finally
            if DataModule1.cdsGrades.BookmarkValid(BM2) then
              DataModule1.cdsGrades.GotoBookmark(BM2);
            DataModule1.cdsGrades.FreeBookmark(BM2);
          end;

          DataModule1.cdsStudents.Next;
        end;
      finally
        DataModule1.cdsStudents.Filtered := False;
        if DataModule1.cdsStudents.BookmarkValid(BM) then
          DataModule1.cdsStudents.GotoBookmark(BM);
        DataModule1.cdsStudents.FreeBookmark(BM);
      end;

      BarSeries.Add(Scores[0], '0-9分', clRed);
      BarSeries.Add(Scores[1], '10-19分', clOlive);
      BarSeries.Add(Scores[2], '20-29分', clPurple);
      BarSeries.Add(Scores[3], '30-39分', clNavy);
      BarSeries.Add(Scores[4], '40-49分', clMaroon);
      BarSeries.Add(Scores[5], '50-59分', clGray);
      BarSeries.Add(Scores[6], '60-69分', clGreen);
      BarSeries.Add(Scores[7], '70-79分', clTeal);
      BarSeries.Add(Scores[8], '80-89分', clBlue);
      BarSeries.Add(Scores[9], '90-99分', clAqua);
      BarSeries.Add(Scores[10], '100分', clYellow);
    end;
  finally
    ClassList.Free;
  end;
end;

procedure TFormChart.GenerateStudentComparison;
var
  BarSeries: TBarSeries;
  BM, BM2: TBookmark;
  StudentID, StudentName, ClassName: string;
  TotalScore: Double;
  Count: Integer;
  SelectedClass: string;
begin
  ClearChart;
  Chart1.Title.Text.Add('学生平均分对比');
  Chart1.Axes.Left.Title.Text := '平均分';
  Chart1.Axes.Bottom.Title.Text := '学生';

  BarSeries := TBarSeries.Create(Chart1);
  BarSeries.Title := '平均分';
  BarSeries.Marks.Visible := True;
  BarSeries.ColorEachPoint := True;
  Chart1.AddSeries(BarSeries);

  SelectedClass := '';
  if not chkAllClasses.Checked and (cboClass.ItemIndex >= 0) then
    SelectedClass := cboClass.Text;

  BM := DataModule1.cdsStudents.GetBookmark;
  try
    DataModule1.cdsStudents.First;
    while not DataModule1.cdsStudents.Eof do
    begin
      StudentID := DataModule1.cdsStudents.FieldByName('StudentID').AsString;
      StudentName := DataModule1.cdsStudents.FieldByName('StudentName').AsString;
      ClassName := DataModule1.cdsStudents.FieldByName('Class').AsString;

      if (SelectedClass <> '') and (SelectedClass <> ClassName) then
      begin
        DataModule1.cdsStudents.Next;
        Continue;
      end;

      TotalScore := 0;
      Count := 0;

      BM2 := DataModule1.cdsGrades.GetBookmark;
      try
        DataModule1.cdsGrades.First;
        while not DataModule1.cdsGrades.Eof do
        begin
          if DataModule1.cdsGrades.FieldByName('StudentID').AsString = StudentID then
          begin
            Inc(Count);
            TotalScore := TotalScore + DataModule1.cdsGrades.FieldByName('Score').AsFloat;
          end;
          DataModule1.cdsGrades.Next;
        end;
      finally
        if DataModule1.cdsGrades.BookmarkValid(BM2) then
          DataModule1.cdsGrades.GotoBookmark(BM2);
        DataModule1.cdsGrades.FreeBookmark(BM2);
      end;

      if Count > 0 then
        BarSeries.Add(TotalScore / Count, StudentName);

      DataModule1.cdsStudents.Next;
    end;
  finally
    if DataModule1.cdsStudents.BookmarkValid(BM) then
      DataModule1.cdsStudents.GotoBookmark(BM);
    DataModule1.cdsStudents.FreeBookmark(BM);
  end;
end;

procedure TFormChart.GenerateClassComparison;
var
  BarSeries: TBarSeries;
  BM, BM2: TBookmark;
  ClassList: TStringList;
  i: Integer;
  ClassName, StudentID: string;
  TotalScore, AvgScore: Double;
  TotalStudents, TotalGrades: Integer;
begin
  ClearChart;
  Chart1.Title.Text.Add('班级平均分对比');
  Chart1.Axes.Left.Title.Text := '平均分';
  Chart1.Axes.Bottom.Title.Text := '班级';

  BarSeries := TBarSeries.Create(Chart1);
  BarSeries.Title := '平均分';
  BarSeries.Marks.Visible := True;
  BarSeries.ColorEachPoint := True;
  Chart1.AddSeries(BarSeries);

  ClassList := GetClassNameList;
  try
    for i := 0 to ClassList.Count - 1 do
    begin
      ClassName := ClassList[i];
      TotalScore := 0;
      TotalStudents := 0;
      TotalGrades := 0;

      BM := DataModule1.cdsStudents.GetBookmark;
      try
        DataModule1.cdsStudents.Filter := 'Class = ' + QuotedStr(ClassName);
        DataModule1.cdsStudents.Filtered := True;
        DataModule1.cdsStudents.First;

        while not DataModule1.cdsStudents.Eof do
        begin
          Inc(TotalStudents);
          StudentID := DataModule1.cdsStudents.FieldByName('StudentID').AsString;

          BM2 := DataModule1.cdsGrades.GetBookmark;
          try
            DataModule1.cdsGrades.First;
            while not DataModule1.cdsGrades.Eof do
            begin
              if DataModule1.cdsGrades.FieldByName('StudentID').AsString = StudentID then
              begin
                Inc(TotalGrades);
                TotalScore := TotalScore + DataModule1.cdsGrades.FieldByName('Score').AsFloat;
              end;
              DataModule1.cdsGrades.Next;
            end;
          finally
            if DataModule1.cdsGrades.BookmarkValid(BM2) then
              DataModule1.cdsGrades.GotoBookmark(BM2);
            DataModule1.cdsGrades.FreeBookmark(BM2);
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

      BarSeries.Add(AvgScore, ClassName + #13#10 + '(' + IntToStr(TotalStudents) + '人)');
    end;
  finally
    ClassList.Free;
  end;
end;

procedure TFormChart.GenerateCourseComparison;
var
  BarSeries: TBarSeries;
  BM: TBookmark;
  CourseName: string;
  CourseList: TStringList;
  i: Integer;
  TotalScore: Double;
  Count: Integer;
  AvgScore: Double;
begin
  ClearChart;
  Chart1.Title.Text.Add('各课程平均分对比');
  Chart1.Axes.Left.Title.Text := '平均分';
  Chart1.Axes.Bottom.Title.Text := '课程';

  BarSeries := TBarSeries.Create(Chart1);
  BarSeries.Title := '平均分';
  BarSeries.Marks.Visible := True;
  BarSeries.ColorEachPoint := True;
  Chart1.AddSeries(BarSeries);

  CourseList := TStringList.Create;
  CourseList.Duplicates := dupIgnore;
  CourseList.Sorted := True;
  try
    BM := DataModule1.cdsGrades.GetBookmark;
    try
      DataModule1.cdsGrades.First;
      while not DataModule1.cdsGrades.Eof do
      begin
        CourseName := DataModule1.cdsGrades.FieldByName('CourseName').AsString;
        if Trim(CourseName) <> '' then
          CourseList.Add(CourseName);
        DataModule1.cdsGrades.Next;
      end;
    finally
      if DataModule1.cdsGrades.BookmarkValid(BM) then
        DataModule1.cdsGrades.GotoBookmark(BM);
      DataModule1.cdsGrades.FreeBookmark(BM);
    end;

    for i := 0 to CourseList.Count - 1 do
    begin
      CourseName := CourseList[i];
      TotalScore := 0;
      Count := 0;

      DataModule1.cdsGrades.First;
      while not DataModule1.cdsGrades.Eof do
      begin
        if DataModule1.cdsGrades.FieldByName('CourseName').AsString = CourseName then
        begin
          Inc(Count);
          TotalScore := TotalScore + DataModule1.cdsGrades.FieldByName('Score').AsFloat;
        end;
        DataModule1.cdsGrades.Next;
      end;

      if Count > 0 then
      begin
        AvgScore := TotalScore / Count;
        BarSeries.Add(AvgScore, CourseName);
      end;
    end;
  finally
    CourseList.Free;
  end;
end;

procedure TFormChart.btnGenerateClick(Sender: TObject);
begin
  if rbChartType1.Checked then
    GenerateScoreDistribution
  else if rbChartType2.Checked then
    GenerateStudentComparison
  else if rbChartType3.Checked then
    GenerateClassComparison
  else if rbChartType4.Checked then
    GenerateCourseComparison;
end;

procedure TFormChart.btnExportClick(Sender: TObject);
begin
  if Chart1.SeriesList.Count = 0 then
  begin
    ShowMessage('请先生成图表！');
    Exit;
  end;

  if dlgSaveChart.Execute then
  begin
    try
      case dlgSaveChart.FilterIndex of
        1: Chart1.SaveToBitmapFile(dlgSaveChart.FileName);
        2: Chart1.SaveToBitmapFile(dlgSaveChart.FileName);
        3: Chart1.SaveToBitmapFile(ChangeFileExt(dlgSaveChart.FileName, '.bmp'));
      end;
      ShowMessage('图表已导出：' + dlgSaveChart.FileName);
    except
      on E: Exception do
        ShowMessage('导出失败: ' + E.Message);
    end;
  end;
end;

procedure TFormChart.btnCloseClick(Sender: TObject);
begin
  Close;
end;

end.
