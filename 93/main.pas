unit main;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Forms, Controls, Graphics, Dialogs, StdCtrls, ComCtrls,
  ExtCtrls, Buttons, DBGrids, DB, sqldb, connection, dbgrid, export, bookmark,
  er_diagram, query_builder, Grids, Menus, ActnList;

type

  { TMainForm }

  TMainForm = class(TForm)
    btnConnect: TBitBtn;
    btnDisconnect: TBitBtn;
    btnExecute: TBitBtn;
    btnExportCSV: TBitBtn;
    btnRefreshER: TButton;
    btnRefreshTables: TBitBtn;
    btnSaveBookmark: TBitBtn;
    btnSaveChanges: TBitBtn;
    dlgOpenDB: TOpenDialog;
    dlgSaveBookmark: TSaveDialog;
    dlgSaveCSV: TSaveDialog;
    gbConnection: TGroupBox;
    gbQuery: TGroupBox;
    gbResults: TGroupBox;
    lblBookmarks: TLabel;
    lblDBPath: TLabel;
    lblRecordCount: TLabel;
    lblStatus: TLabel;
    lblTables: TLabel;
    lbBookmarks: TListBox;
    lbTables: TListBox;
    mmoQuery: TMemo;
    pnlCenter: TPanel;
    pnlMain: TPanel;
    pnlRight: TPanel;
    pnlSQLQuery: TPanel;
    pnlSQLResults: TPanel;
    pnlSplit: TSplitter;
    pnlTop: TPanel;
    sbStatus: TStatusBar;
    tabERDiagram: TTabSheet;
    tabMain: TPageControl;
    tabQueryBuilder: TTabSheet;
    tabSQL: TTabSheet;
    dbgResults: TDBGrid;
    procedure btnConnectClick(Sender: TObject);
    procedure btnDisconnectClick(Sender: TObject);
    procedure btnExecuteClick(Sender: TObject);
    procedure btnExportCSVClick(Sender: TObject);
    procedure btnRefreshERClick(Sender: TObject);
    procedure btnRefreshTablesClick(Sender: TObject);
    procedure btnSaveBookmarkClick(Sender: TObject);
    procedure btnSaveChangesClick(Sender: TObject);
    procedure FormClose(Sender: TObject; var CloseAction: TCloseAction);
    procedure FormCreate(Sender: TObject);
    procedure FormDestroy(Sender: TObject);
    procedure lbBookmarksDblClick(Sender: TObject);
    procedure lbTablesDblClick(Sender: TObject);
  private
    FDB: TDBConnection;
    FGridMgr: TDBGridManager;
    FExporter: TCSVExporter;
    FBookmarkMgr: TBookmarkManager;
    FERDiagram: TERDiagramManager;
    FQueryBuilder: TQueryBuilderManager;
    FCurrentQuery: TSQLQuery;
    procedure UpdateUIState;
    procedure LoadTables;
    procedure LoadBookmarks;
    procedure ShowStatus(const AMsg: string);
    procedure ShowError(const AMsg: string);
    procedure ClearResults;
    procedure QueryBuilderApplySQL(const SQL: string);
    procedure QueryBuilderPreviewSQL(const SQL: string);
    procedure ERTableDblClick(Sender: TObject);
    function InputQueryWithDefault(const ACaption, APrompt, ADefault: string): string;
  public
  end;

var
  MainForm: TMainForm;

implementation

{$R *.lfm}

{ TMainForm }

procedure TMainForm.FormCreate(Sender: TObject);
begin
  FDB := TDBConnection.Create;
  FGridMgr := TDBGridManager.Create(dbgResults);
  FExporter := TCSVExporter.Create;
  FBookmarkMgr := TBookmarkManager.Create;
  FCurrentQuery := nil;
  FERDiagram := nil;
  FQueryBuilder := nil;

  dlgOpenDB.Filter := 'SQLite 数据库 (*.db;*.sqlite;*.db3)|*.db;*.sqlite;*.db3|所有文件 (*.*)|*.*';
  dlgOpenDB.DefaultExt := 'db';

  dlgSaveCSV.Filter := 'CSV 文件 (*.csv)|*.csv|所有文件 (*.*)|*.*';
  dlgSaveCSV.DefaultExt := 'csv';

  dlgSaveBookmark.Filter := 'SQL 文件 (*.sql)|*.sql|所有文件 (*.*)|*.*';
  dlgSaveBookmark.DefaultExt := 'sql';

  mmoQuery.Font.Name := 'Consolas';
  mmoQuery.Font.Size := 10;

  LoadBookmarks;
  UpdateUIState;
  ShowStatus('就绪 - 请选择并连接 SQLite 数据库');
end;

procedure TMainForm.FormDestroy(Sender: TObject);
begin
  if Assigned(FERDiagram) then
    FERDiagram.Free;
  if Assigned(FQueryBuilder) then
    FQueryBuilder.Free;
  ClearResults;
  FBookmarkMgr.Free;
  FExporter.Free;
  FGridMgr.Free;
  FDB.Free;
end;

procedure TMainForm.FormClose(Sender: TObject; var CloseAction: TCloseAction);
begin
  FBookmarkMgr.Save;
  FDB.Disconnect;
end;

procedure TMainForm.UpdateUIState;
var
  Connected: Boolean;
begin
  Connected := FDB.IsConnected;
  btnConnect.Enabled := not Connected;
  btnDisconnect.Enabled := Connected;
  btnRefreshTables.Enabled := Connected;
  btnExecute.Enabled := Connected and (Trim(mmoQuery.Text) <> '');
  btnExportCSV.Enabled := Connected and Assigned(FCurrentQuery) and FCurrentQuery.Active;
  btnSaveChanges.Enabled := Connected and Assigned(FCurrentQuery) and FCurrentQuery.Active;
  btnSaveBookmark.Enabled := Connected and (Trim(mmoQuery.Text) <> '');
  btnRefreshER.Enabled := Connected;
  lbTables.Enabled := Connected;
  mmoQuery.Enabled := Connected;
  gbQuery.Enabled := Connected;
  gbResults.Enabled := Connected;

  if Connected then
  begin
    lblDBPath.Caption := '数据库: ' + FDB.DatabasePath;
    lblStatus.Caption := '已连接';
    lblStatus.Font.Color := clGreen;
  end
  else
  begin
    lblDBPath.Caption := '数据库: 未连接';
    lblStatus.Caption := '未连接';
    lblStatus.Font.Color := clRed;
  end;
end;

procedure TMainForm.LoadTables;
var
  Tables: TStringList;
begin
  lbTables.Items.Clear;
  if not FDB.IsConnected then Exit;

  try
    Tables := FDB.GetTables;
    try
      lbTables.Items.Assign(Tables);
    finally
      Tables.Free;
    end;
  except
    on E: Exception do
      ShowError('加载表列表失败: ' + E.Message);
  end;
end;

procedure TMainForm.LoadBookmarks;
var
  i: Integer;
begin
  lbBookmarks.Items.Clear;
  try
    FBookmarkMgr.Load;
    for i := 0 to FBookmarkMgr.Count - 1 do
    begin
      lbBookmarks.Items.AddObject(FBookmarkMgr[i].Name, FBookmarkMgr[i]);
    end;
  except
    on E: Exception do
      ShowError('加载书签失败: ' + E.Message);
  end;
end;

procedure TMainForm.ShowStatus(const AMsg: string);
begin
  sbStatus.SimpleText := AMsg;
end;

procedure TMainForm.ShowError(const AMsg: string);
begin
  ShowMessage('错误: ' + AMsg);
  ShowStatus('错误: ' + AMsg);
end;

procedure TMainForm.ClearResults;
begin
  FGridMgr.Clear;
  if Assigned(FCurrentQuery) then
  begin
    FreeAndNil(FCurrentQuery);
  end;
  lblRecordCount.Caption := '记录数: 0';
  UpdateUIState;
end;

function TMainForm.InputQueryWithDefault(const ACaption, APrompt, ADefault: string): string;
var
  Form: TForm;
  Label: TLabel;
  Edit: TEdit;
  OKBtn, CancelBtn: TButton;
begin
  Form := TForm.Create(Self);
  try
    Form.Caption := ACaption;
    Form.Width := 400;
    Form.Height := 150;
    Form.BorderStyle := bsDialog;
    Form.Position := poScreenCenter;

    Label := TLabel.Create(Form);
    Label.Parent := Form;
    Label.Left := 16;
    Label.Top := 16;
    Label.Width := 368;
    Label.Caption := APrompt;

    Edit := TEdit.Create(Form);
    Edit.Parent := Form;
    Edit.Left := 16;
    Edit.Top := 40;
    Edit.Width := 360;
    Edit.Text := ADefault;

    OKBtn := TButton.Create(Form);
    OKBtn.Parent := Form;
    OKBtn.Left := 200;
    OKBtn.Top := 72;
    OKBtn.Width := 80;
    OKBtn.Caption := '确定';
    OKBtn.ModalResult := mrOK;
    OKBtn.Default := True;

    CancelBtn := TButton.Create(Form);
    CancelBtn.Parent := Form;
    CancelBtn.Left := 296;
    CancelBtn.Top := 72;
    CancelBtn.Width := 80;
    CancelBtn.Caption := '取消';
    CancelBtn.ModalResult := mrCancel;
    CancelBtn.Cancel := True;

    if Form.ShowModal = mrOK then
      Result := Edit.Text
    else
      Result := '';
  finally
    Form.Free;
  end;
end;

procedure TMainForm.QueryBuilderApplySQL(const SQL: string);
begin
  mmoQuery.Text := SQL;
  btnExecute.Click;
end;

procedure TMainForm.QueryBuilderPreviewSQL(const SQL: string);
begin
  mmoQuery.Text := SQL;
end;

procedure TMainForm.ERTableDblClick(Sender: TObject);
var
  Node: TERTableNode;
begin
  if Assigned(Sender) and (Sender is TERTableNode) then
  begin
    Node := TERTableNode(Sender);
    mmoQuery.Text := 'SELECT * FROM ' + Node.TableName;
    tabMain.ActivePage := tabSQL;
    btnExecute.Click;
  end;
end;

procedure TMainForm.btnConnectClick(Sender: TObject);
begin
  if not dlgOpenDB.Execute then Exit;

  try
    ShowStatus('正在连接数据库...');
    if FDB.Connect(dlgOpenDB.FileName) then
    begin
      LoadTables;
      mmoQuery.Text := 'SELECT * FROM ';

      if not Assigned(FERDiagram) then
      begin
        FERDiagram := TERDiagramManager.Create(nil, FDB);
        FERDiagram.Grid.Parent := tabERDiagram;
        FERDiagram.Grid.Align := alClient;
        FERDiagram.Grid.Top := 40;
        FERDiagram.Grid.Height := FERDiagram.Grid.Height - 40;
        FERDiagram.OnTableDblClick := @ERTableDblClick;
      end;
      FERDiagram.LoadTables;

      if not Assigned(FQueryBuilder) then
      begin
        FQueryBuilder := TQueryBuilderManager.Create(FDB, tabQueryBuilder);
        FQueryBuilder.OnApplySQL := @QueryBuilderApplySQL;
        FQueryBuilder.OnPreviewSQL := @QueryBuilderPreviewSQL;
      end;
      FQueryBuilder.LoadTables;

      ShowStatus('连接成功: ' + FDB.DatabasePath);
    end
    else
    begin
      ShowError('无法连接到数据库');
    end;
  except
    on E: Exception do
    begin
      ShowError('连接失败: ' + E.Message);
    end;
  end;
  UpdateUIState;
end;

procedure TMainForm.btnDisconnectClick(Sender: TObject);
begin
  try
    ClearResults;
    FDB.Disconnect;
    lbTables.Items.Clear;
    mmoQuery.Clear;
    ShowStatus('已断开连接');
  except
    on E: Exception do
      ShowError('断开连接失败: ' + E.Message);
  end;
  UpdateUIState;
end;

procedure TMainForm.btnExecuteClick(Sender: TObject);
var
  SQL: string;
  RecordCount: Integer;
begin
  SQL := Trim(mmoQuery.Text);
  if SQL = '' then
  begin
    ShowError('请输入 SQL 语句');
    Exit;
  end;

  try
    ShowStatus('正在执行查询...');
    ClearResults;

    if UpperCase(Copy(SQL, 1, 6)) = 'SELECT' then
    begin
      FCurrentQuery := FDB.ExecuteQuery(SQL);
      FGridMgr.BindQuery(FCurrentQuery);
      RecordCount := FGridMgr.GetRecordCount;
      lblRecordCount.Caption := '记录数: ' + IntToStr(RecordCount);
      ShowStatus('查询完成，共 ' + IntToStr(RecordCount) + ' 条记录');
    end
    else
    begin
      RecordCount := FDB.ExecuteSQL(SQL);
      lblRecordCount.Caption := '影响行数: ' + IntToStr(RecordCount);
      ShowStatus('SQL 执行完成，影响 ' + IntToStr(RecordCount) + ' 行');
      if UpperCase(Copy(SQL, 1, 6)) = 'CREATE' then
        LoadTables;
    end;
  except
    on E: Exception do
    begin
      ShowError('SQL 执行失败: ' + E.Message);
      ClearResults;
    end;
  end;
  UpdateUIState;
end;

procedure TMainForm.btnExportCSVClick(Sender: TObject);
var
  ExportedCount: Integer;
begin
  if not Assigned(FCurrentQuery) or not FCurrentQuery.Active then
  begin
    ShowError('没有可导出的数据');
    Exit;
  end;

  if not dlgSaveCSV.Execute then Exit;

  try
    ShowStatus('正在导出 CSV...');
    ExportedCount := FExporter.ExportToCSV(FCurrentQuery, dlgSaveCSV.FileName);
    ShowMessage('导出成功!' + sLineBreak + '文件: ' + dlgSaveCSV.FileName + sLineBreak + '记录数: ' + IntToStr(ExportedCount));
    ShowStatus('导出完成: ' + IntToStr(ExportedCount) + ' 条记录');
  except
    on E: Exception do
      ShowError('导出失败: ' + E.Message);
  end;
end;

procedure TMainForm.btnRefreshERClick(Sender: TObject);
begin
  if Assigned(FERDiagram) then
  begin
    ShowStatus('正在刷新 ER 图...');
    FERDiagram.LoadTables;
    ShowStatus('ER 图已刷新');
  end;
end;

procedure TMainForm.btnRefreshTablesClick(Sender: TObject);
begin
  LoadTables;
  ShowStatus('表列表已刷新');
end;

procedure TMainForm.btnSaveBookmarkClick(Sender: TObject);
var
  SQL, Name, Desc: string;
begin
  SQL := Trim(mmoQuery.Text);
  if SQL = '' then
  begin
    ShowError('请先输入 SQL 语句');
    Exit;
  end;

  Name := InputQueryWithDefault('保存书签', '书签名称:', '查询_' + FormatDateTime('yyyy-mm-dd_hh-nn-ss', Now));
  if Trim(Name) = '' then Exit;

  Desc := InputQueryWithDefault('保存书签', '书签描述（可选）:', '');

  try
    if FBookmarkMgr.FindByName(Name) = nil then
    begin
      FBookmarkMgr.Add(Name, SQL, Desc);
    end
    else
    begin
      if MessageDlg('书签 "' + Name + '" 已存在，是否覆盖？', mtConfirmation, [mbYes, mbNo], 0) = mrYes then
      begin
        FBookmarkMgr.Update(FBookmarkMgr.IndexOf(FBookmarkMgr.FindByName(Name)), Name, SQL, Desc);
      end
      else
      begin
        Name := FBookmarkMgr.GetUniqueName(Name);
        FBookmarkMgr.Add(Name, SQL, Desc);
      end;
    end;

    FBookmarkMgr.Save;
    LoadBookmarks;
    ShowStatus('书签已保存: ' + Name);
  except
    on E: Exception do
      ShowError('保存书签失败: ' + E.Message);
  end;
end;

procedure TMainForm.btnSaveChangesClick(Sender: TObject);
begin
  if Assigned(FGridMgr) then
  begin
    try
      ShowStatus('正在保存更改...');
      FGridMgr.PostChanges;
      ShowStatus('更改已保存');
    except
      on E: Exception do
        ShowError('保存更改失败: ' + E.Message);
    end;
  end;
end;

procedure TMainForm.lbBookmarksDblClick(Sender: TObject);
var
  Item: TBookmarkItem;
begin
  if lbBookmarks.ItemIndex >= 0 then
  begin
    Item := TBookmarkItem(lbBookmarks.Items.Objects[lbBookmarks.ItemIndex]);
    if Assigned(Item) then
    begin
      mmoQuery.Text := Item.SQL;
      tabMain.ActivePage := tabSQL;
      btnExecute.Click;
    end;
  end;
end;

procedure TMainForm.lbTablesDblClick(Sender: TObject);
var
  TableName: string;
begin
  if lbTables.ItemIndex >= 0 then
  begin
    TableName := lbTables.Items[lbTables.ItemIndex];
    mmoQuery.Text := 'SELECT * FROM ' + TableName;
    btnExecute.Click;
  end;
end;

end.
