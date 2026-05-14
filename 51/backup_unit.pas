unit backup_unit;

interface

uses
  Winapi.Windows, Winapi.Messages, System.SysUtils, System.Variants, System.Classes, Vcl.Graphics,
  Vcl.Controls, Vcl.Forms, Vcl.Dialogs, Vcl.StdCtrls, Vcl.ExtCtrls, Vcl.ComCtrls,
  Data.DB, Datasnap.DBClient, System.IOUtils;

type
  TFormBackup = class(TForm)
    Panel1: TPanel;
    Panel2: TPanel;
    GroupBox1: TGroupBox;
    chkAutoBackup: TCheckBox;
    Label1: TLabel;
    edtBackupPath: TEdit;
    btnBrowse: TButton;
    Label2: TLabel;
    cboInterval: TComboBox;
    Label3: TLabel;
    spnKeepDays: TSpinEdit;
    GroupBox2: TGroupBox;
    btnBackupNow: TButton;
    btnRestore: TButton;
    btnDelete: TButton;
    btnClose: TButton;
    ListView1: TListView;
    StatusBar1: TStatusBar;
    dlgFolder: TFileOpenDialog;
    dlgOpen: TOpenDialog;
    Timer1: TTimer;
    procedure FormCreate(Sender: TObject);
    procedure FormClose(Sender: TObject; var Action: TCloseAction);
    procedure chkAutoBackupClick(Sender: TObject);
    procedure btnBrowseClick(Sender: TObject);
    procedure btnBackupNowClick(Sender: TObject);
    procedure btnRestoreClick(Sender: TObject);
    procedure btnDeleteClick(Sender: TObject);
    procedure btnCloseClick(Sender: TObject);
    procedure Timer1Timer(Sender: TObject);
  private
    FConfigPath: string;
    FDataPath: string;
    FBackupPath: string;
    FLastBackupTime: TDateTime;
    FBackupInterval: Integer;
    FKeepDays: Integer;
    FAutoBackup: Boolean;
    procedure LoadConfig;
    procedure SaveConfig;
    procedure LoadBackupList;
    function GenerateBackupFileName: string;
    procedure CreateBackup(const DestFileName: string);
    procedure RestoreBackup(const SourceDirName: string);
    procedure CleanOldBackups;
    procedure UpdateStatus;
    function GetDirSize(const Dir: string): Int64;
    procedure DeleteDir(const Dir: string);
  public
  end;

var
  FormBackup: TFormBackup;

implementation

{$R *.dfm}

uses
  data_module;

procedure TFormBackup.FormCreate(Sender: TObject);
begin
  FDataPath := ExtractFilePath(ParamStr(0));
  FConfigPath := FDataPath + 'backup_config.ini';
  FBackupPath := FDataPath + 'Backup';
  FLastBackupTime := 0;
  FBackupInterval := 60;
  FKeepDays := 30;
  FAutoBackup := False;

  cboInterval.Items.Add('1 分钟');
  cboInterval.Items.Add('5 分钟');
  cboInterval.Items.Add('10 分钟');
  cboInterval.Items.Add('30 分钟');
  cboInterval.Items.Add('1 小时');
  cboInterval.Items.Add('2 小时');
  cboInterval.ItemIndex := 4;

  spnKeepDays.MinValue := 1;
  spnKeepDays.MaxValue := 365;
  spnKeepDays.Value := 30;

  ListView1.ViewStyle := vsReport;
  ListView1.Columns.Add.Caption := '备份名称';
  ListView1.Columns[0].Width := 200;
  ListView1.Columns.Add.Caption := '日期时间';
  ListView1.Columns[1].Width := 150;
  ListView1.Columns.Add.Caption := '大小';
  ListView1.Columns[2].Width := 100;

  LoadConfig;
  LoadBackupList;
  UpdateStatus;
end;

procedure TFormBackup.FormClose(Sender: TObject; var Action: TCloseAction);
begin
  SaveConfig;
end;

procedure TFormBackup.LoadConfig;
var
  IniFile: TStringList;
begin
  if not FileExists(FConfigPath) then Exit;
  IniFile := TStringList.Create;
  try
    IniFile.LoadFromFile(FConfigPath);
    FBackupPath := IniFile.Values['BackupPath'];
    if Trim(FBackupPath) = '' then
      FBackupPath := FDataPath + 'Backup';
    FAutoBackup := LowerCase(IniFile.Values['AutoBackup']) = 'true';
    FBackupInterval := StrToIntDef(IniFile.Values['BackupInterval'], 60);
    FKeepDays := StrToIntDef(IniFile.Values['KeepDays'], 30);

    chkAutoBackup.Checked := FAutoBackup;
    edtBackupPath.Text := FBackupPath;
    spnKeepDays.Value := FKeepDays;

    case FBackupInterval of
      1: cboInterval.ItemIndex := 0;
      5: cboInterval.ItemIndex := 1;
      10: cboInterval.ItemIndex := 2;
      30: cboInterval.ItemIndex := 3;
      60: cboInterval.ItemIndex := 4;
      120: cboInterval.ItemIndex := 5;
    else
      cboInterval.ItemIndex := 4;
    end;

    Timer1.Enabled := FAutoBackup;
    Timer1.Interval := FBackupInterval * 60 * 1000;
  finally
    IniFile.Free;
  end;
end;

procedure TFormBackup.SaveConfig;
var
  IniFile: TStringList;
begin
  IniFile := TStringList.Create;
  try
    IniFile.Values['BackupPath'] := edtBackupPath.Text;
    IniFile.Values['AutoBackup'] := BoolToStr(chkAutoBackup.Checked, True);
    case cboInterval.ItemIndex of
      0: FBackupInterval := 1;
      1: FBackupInterval := 5;
      2: FBackupInterval := 10;
      3: FBackupInterval := 30;
      4: FBackupInterval := 60;
      5: FBackupInterval := 120;
    else
      FBackupInterval := 60;
    end;
    IniFile.Values['BackupInterval'] := IntToStr(FBackupInterval);
    IniFile.Values['KeepDays'] := IntToStr(spnKeepDays.Value);
    IniFile.SaveToFile(FConfigPath);
  finally
    IniFile.Free;
  end;
end;

procedure TFormBackup.chkAutoBackupClick(Sender: TObject);
begin
  FAutoBackup := chkAutoBackup.Checked;
  case cboInterval.ItemIndex of
    0: FBackupInterval := 1;
    1: FBackupInterval := 5;
    2: FBackupInterval := 10;
    3: FBackupInterval := 30;
    4: FBackupInterval := 60;
    5: FBackupInterval := 120;
  else
    FBackupInterval := 60;
  end;
  FKeepDays := spnKeepDays.Value;
  Timer1.Interval := FBackupInterval * 60 * 1000;
  Timer1.Enabled := FAutoBackup;
  SaveConfig;
  UpdateStatus;
end;

procedure TFormBackup.btnBrowseClick(Sender: TObject);
begin
  if not TDirectory.Exists(edtBackupPath.Text) then
  try
    TDirectory.CreateDirectory(edtBackupPath.Text);
  except
  end;

  if SelectDirectory('选择备份文件夹', '', FBackupPath) then
  begin
    edtBackupPath.Text := FBackupPath;
    SaveConfig;
    LoadBackupList;
  end;
end;

function TFormBackup.GenerateBackupFileName: string;
begin
  Result := Format('Backup_%s', [FormatDateTime('yyyymmdd_hhnnss', Now)]);
end;

procedure TFormBackup.CreateBackup(const DestFileName: string);
var
  SrcFile, DestFile, BackupDir: string;
  Files: TStringDynArray;
  i: Integer;
begin
  BackupDir := edtBackupPath.Text + '\' + DestFileName;
  if not TDirectory.Exists(BackupDir) then
    TDirectory.CreateDirectory(BackupDir);

  Files := TDirectory.GetFiles(FDataPath, '*.xml');
  for i := 0 to High(Files) do
  begin
    SrcFile := Files[i];
    DestFile := BackupDir + '\' + ExtractFileName(SrcFile);
    try
      CopyFile(PChar(SrcFile), PChar(DestFile), False);
    except
      on E: Exception do
        raise Exception.Create('备份文件失败: ' + ExtractFileName(SrcFile) + ' - ' + E.Message);
    end;
  end;
end;

procedure TFormBackup.RestoreBackup(const SourceFileName: string);
var
  BackupDir, FileName, SrcFile, DestFile: string;
  SR: TSearchRec;
  BackupFiles: TStringList;
  i: Integer;
begin
  BackupDir := edtBackupPath.Text + '\' + SourceFileName;
  if not TDirectory.Exists(BackupDir) then
    raise Exception.Create('备份目录不存在！');

  BackupFiles := TStringList.Create;
  try
    if FindFirst(BackupDir + '\*.xml', faAnyFile, SR) = 0 then
    begin
      repeat
        if (SR.Attr and faDirectory) = 0 then
          BackupFiles.Add(SR.Name);
      until FindNext(SR) <> 0;
      FindClose(SR);
    end;

    if BackupFiles.Count = 0 then
      raise Exception.Create('备份目录中没有找到数据文件！');

    if MessageDlg('确定要恢复数据吗？当前数据将被覆盖！', mtConfirmation, [mbYes, mbNo], 0) <> mrYes then
      Exit;

    for i := 0 to BackupFiles.Count - 1 do
    begin
      FileName := BackupFiles[i];
      SrcFile := BackupDir + '\' + FileName;
      DestFile := FDataPath + FileName;
      CopyFile(PChar(SrcFile), PChar(DestFile), False);
    end;

    DataModule1.RefreshData;
    ShowMessage('数据恢复成功！');
  finally
    BackupFiles.Free;
  end;
end;

function TFormBackup.GetDirSize(const Dir: string): Int64;
var
  SR: TSearchRec;
begin
  Result := 0;
  if not TDirectory.Exists(Dir) then Exit;
  if FindFirst(Dir + '\*.*', faAnyFile, SR) = 0 then
  begin
    repeat
      if (SR.Attr and faDirectory) = 0 then
        Inc(Result, SR.Size);
    until FindNext(SR) <> 0;
    FindClose(SR);
  end;
end;

procedure TFormBackup.DeleteDir(const Dir: string);
var
  SR: TSearchRec;
begin
  if not TDirectory.Exists(Dir) then Exit;
  if FindFirst(Dir + '\*.*', faAnyFile, SR) = 0 then
  begin
    repeat
      if (SR.Attr and faDirectory) = 0 then
        DeleteFile(Dir + '\' + SR.Name)
      else if (SR.Name <> '.') and (SR.Name <> '..') then
        DeleteDir(Dir + '\' + SR.Name);
    until FindNext(SR) <> 0;
    FindClose(SR);
  end;
  RemoveDir(Dir);
end;

procedure TFormBackup.LoadBackupList;
var
  SR: TSearchRec;
  Item: TListItem;
  BackupDir: string;
  FileDateTime: TDateTime;
  TotalSize: Int64;
begin
  ListView1.Items.Clear;
  BackupDir := edtBackupPath.Text;
  if not TDirectory.Exists(BackupDir) then Exit;

  if FindFirst(BackupDir + '\*.*', faDirectory, SR) = 0 then
  begin
    repeat
      if (SR.Attr and faDirectory) <> 0 then
      begin
        if (SR.Name = '.') or (SR.Name = '..') then Continue;
        if Pos('Backup_', SR.Name) = 1 then
        begin
          Item := ListView1.Items.Add;
          Item.Caption := SR.Name;
          FileDateTime := FileDateToDateTime(SR.Time);
          Item.SubItems.Add(FormatDateTime('yyyy-mm-dd hh:nn:ss', FileDateTime));
          TotalSize := GetDirSize(BackupDir + '\' + SR.Name);
          if TotalSize < 1024 then
            Item.SubItems.Add(IntToStr(TotalSize) + ' B')
          else if TotalSize < 1024 * 1024 then
            Item.SubItems.Add(FormatFloat('0.0', TotalSize / 1024) + ' KB')
          else
            Item.SubItems.Add(FormatFloat('0.0', TotalSize / (1024 * 1024)) + ' MB');
          Item.Data := Pointer(FileDateTime);
        end;
      end;
    until FindNext(SR) <> 0;
    FindClose(SR);
  end;

  ListView1.AlphaSort;
end;

procedure TFormBackup.CleanOldBackups;
var
  SR: TSearchRec;
  BackupDir: string;
  FileDateTime: TDateTime;
  CutoffDate: TDateTime;
begin
  BackupDir := edtBackupPath.Text;
  if not TDirectory.Exists(BackupDir) then Exit;

  CutoffDate := Now - FKeepDays;

  if FindFirst(BackupDir + '\*.*', faDirectory, SR) = 0 then
  begin
    repeat
      if (SR.Attr and faDirectory) <> 0 then
      begin
        if (SR.Name = '.') or (SR.Name = '..') then Continue;
        if Pos('Backup_', SR.Name) = 1 then
        begin
          FileDateTime := FileDateToDateTime(SR.Time);
          if FileDateTime < CutoffDate then
            DeleteDir(BackupDir + '\' + SR.Name);
        end;
      end;
    until FindNext(SR) <> 0;
    FindClose(SR);
  end;
end;

procedure TFormBackup.UpdateStatus;
begin
  if FAutoBackup then
    StatusBar1.Panels[0].Text := '自动备份已启用 (间隔: ' + cboInterval.Text + ')'
  else
    StatusBar1.Panels[0].Text := '自动备份已关闭';
  StatusBar1.Panels[1].Text := '保留天数: ' + IntToStr(FKeepDays) + ' 天';
  StatusBar1.Panels[2].Text := '备份数量: ' + IntToStr(ListView1.Items.Count);
end;

procedure TFormBackup.btnBackupNowClick(Sender: TObject);
var
  BackupFile: string;
begin
  try
    BackupFile := edtBackupPath.Text + '\' + GenerateBackupFileName;
    CreateBackup(BackupFile);
    FLastBackupTime := Now;
    ShowMessage('备份成功！');
    LoadBackupList;
    CleanOldBackups;
    UpdateStatus;
  except
    on E: Exception do
      ShowMessage('备份失败: ' + E.Message);
  end;
end;

procedure TFormBackup.btnRestoreClick(Sender: TObject);
begin
  if ListView1.Selected = nil then
  begin
    ShowMessage('请选择要恢复的备份文件！');
    Exit;
  end;

  try
    RestoreBackup(ListView1.Selected.Caption);
    LoadBackupList;
    UpdateStatus;
  except
    on E: Exception do
      ShowMessage('恢复失败: ' + E.Message);
  end;
end;

procedure TFormBackup.btnDeleteClick(Sender: TObject);
begin
  if ListView1.Selected = nil then
  begin
    ShowMessage('请选择要删除的备份文件！');
    Exit;
  end;

  if MessageDlg('确定要删除备份文件 ' + ListView1.Selected.Caption + ' 吗？',
                mtConfirmation, [mbYes, mbNo], 0) = mrYes then
  begin
    try
      DeleteDir(edtBackupPath.Text + '\' + ListView1.Selected.Caption);
      LoadBackupList;
      UpdateStatus;
      ShowMessage('删除成功！');
    except
      ShowMessage('删除失败！');
    end;
  end;
end;

procedure TFormBackup.btnCloseClick(Sender: TObject);
begin
  SaveConfig;
  Close;
end;

procedure TFormBackup.Timer1Timer(Sender: TObject);
var
  BackupFile: string;
begin
  Timer1.Enabled := False;
  try
    BackupFile := edtBackupPath.Text + '\Auto_' + GenerateBackupFileName;
    CreateBackup(BackupFile);
    FLastBackupTime := Now;
    CleanOldBackups;
    LoadBackupList;
    UpdateStatus;
  finally
    Timer1.Enabled := True;
  end;
end;

end.
