unit query_builder;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Controls, Graphics, Forms, Dialogs, StdCtrls, ComCtrls,
  ExtCtrls, Grids, DB, sqldb, connection;

type
  TQueryOperator = (
    opEqual, opNotEqual, opLess, opLessOrEqual, opGreater, opGreaterOrEqual,
    opLike, opNotLike, opIsNull, opIsNotNull, opIn, opBetween
  );

  TQueryLogic = (qlAnd, qlOr);

  TQueryConditionItem = class
  private
    FTable: string;
    FField: string;
    FOperator: TQueryOperator;
    FValue1: string;
    FValue2: string;
    FLogic: TQueryLogic;
    FEnabled: Boolean;
  public
    constructor Create;
    function ToSQL: string;
    property Table: string read FTable write FTable;
    property Field: string read FField write FField;
    property Operator: TQueryOperator read FOperator write FOperator;
    property Value1: string read FValue1 write FValue1;
    property Value2: string read FValue2 write FValue2;
    property Logic: TQueryLogic read FLogic write FLogic;
    property Enabled: Boolean read FEnabled write FEnabled;
  end;

  TQueryBuilderManager = class;

  TQueryBuilderPanel = class(TPanel)
  private
    FManager: TQueryBuilderManager;
    FTableList: TListBox;
    FFieldList: TListBox;
    FConditionGrid: TStringGrid;
    FOperatorCombo: TComboBox;
    FLogicCombo: TComboBox;
    FValue1Edit: TEdit;
    FValue2Edit: TEdit;
    FValue2Label: TLabel;
    FAddBtn: TButton;
    FRemoveBtn: TButton;
    FClearBtn: TButton;
    FSQLMemo: TMemo;
    FPreviewBtn: TButton;
    FApplyBtn: TButton;
    FTablesLabel: TLabel;
    FFieldsLabel: TLabel;
    FConditionsLabel: TLabel;
    FSQLPreviewLabel: TLabel;
    FSelectedTable: string;
    FSelectedFields: TStringList;
    procedure TableListClick(Sender: TObject);
    procedure TableListDblClick(Sender: TObject);
    procedure FieldListDblClick(Sender: TObject);
    procedure OperatorComboChange(Sender: TObject);
    procedure AddBtnClick(Sender: TObject);
    procedure RemoveBtnClick(Sender: TObject);
    procedure ClearBtnClick(Sender: TObject);
    procedure ConditionGridSelectCell(Sender: TObject; aCol, aRow: Integer;
      var CanSelect: Boolean);
    procedure PreviewBtnClick(Sender: TObject);
    procedure ApplyBtnClick(Sender: TObject);
    procedure FieldListDrawItem(Control: TWinControl; Index: Integer;
      ARect: TRect; State: TOwnerDrawState);
    procedure InitControls;
    function GetOperatorName(Op: TQueryOperator): string;
    function GetOperatorFromString(const S: string): TQueryOperator;
    function GetLogicName(Log: TQueryLogic): string;
    function GetLogicFromString(const S: string): TQueryLogic;
  public
    constructor Create(AOwner: TComponent; AManager: TQueryBuilderManager); reintroduce;
    destructor Destroy; override;
    procedure LoadTables;
    procedure LoadFields(const ATable: string);
    function BuildSQL: string;
    procedure ClearConditions;
    property SelectedFields: TStringList read FSelectedFields;
  end;

  TQueryBuilderManager = class
  private
    FConnection: TDBConnection;
    FPanel: TQueryBuilderPanel;
    FOnApplySQL: TGetStrProc;
    FOnPreviewSQL: TGetStrProc;
  public
    constructor Create(AConnection: TDBConnection; AParent: TWinControl);
    destructor Destroy; override;
    procedure LoadTables;
    procedure Clear;
    property Connection: TDBConnection read FConnection write FConnection;
    property Panel: TQueryBuilderPanel read FPanel;
    property OnApplySQL: TGetStrProc read FOnApplySQL write FOnApplySQL;
    property OnPreviewSQL: TGetStrProc read FOnPreviewSQL write FOnPreviewSQL;
  end;

implementation

{ TQueryConditionItem }

constructor TQueryConditionItem.Create;
begin
  inherited Create;
  FTable := '';
  FField := '';
  FOperator := opEqual;
  FValue1 := '';
  FValue2 := '';
  FLogic := qlAnd;
  FEnabled := True;
end;

function TQueryConditionItem.ToSQL: string;
var
  FieldRef: string;
begin
  Result := '';
  if (Field = '') then Exit;

  if Table <> '' then
    FieldRef := Table + '.' + Field
  else
    FieldRef := Field;

  case Operator of
    opEqual:
      Result := FieldRef + ' = ' + QuotedStr(Value1);
    opNotEqual:
      Result := FieldRef + ' != ' + QuotedStr(Value1);
    opLess:
      Result := FieldRef + ' < ' + QuotedStr(Value1);
    opLessOrEqual:
      Result := FieldRef + ' <= ' + QuotedStr(Value1);
    opGreater:
      Result := FieldRef + ' > ' + QuotedStr(Value1);
    opGreaterOrEqual:
      Result := FieldRef + ' >= ' + QuotedStr(Value1);
    opLike:
      Result := FieldRef + ' LIKE ' + QuotedStr(Value1);
    opNotLike:
      Result := FieldRef + ' NOT LIKE ' + QuotedStr(Value1);
    opIsNull:
      Result := FieldRef + ' IS NULL';
    opIsNotNull:
      Result := FieldRef + ' IS NOT NULL';
    opIn:
      Result := FieldRef + ' IN (' + Value1 + ')';
    opBetween:
      Result := FieldRef + ' BETWEEN ' + QuotedStr(Value1) + ' AND ' + QuotedStr(Value2);
  end;
end;

{ TQueryBuilderPanel }

constructor TQueryBuilderPanel.Create(AOwner: TComponent; AManager: TQueryBuilderManager);
begin
  inherited Create(AOwner);
  FManager := AManager;
  FSelectedFields := TStringList.Create;
  FSelectedTable := '';
  BevelOuter := bvNone;
  Caption := '';
  ParentColor := True;
  InitControls;
end;

destructor TQueryBuilderPanel.Destroy;
begin
  FSelectedFields.Free;
  inherited Destroy;
end;

procedure TQueryBuilderPanel.InitControls;
var
  LeftPanel, RightPanel: TPanel;
  GridPanel, SQLPanel: TPanel;
  i: Integer;
begin
  LeftPanel := TPanel.Create(Self);
  LeftPanel.Parent := Self;
  LeftPanel.Align := alLeft;
  LeftPanel.Width := 280;
  LeftPanel.BevelOuter := bvNone;
  LeftPanel.Caption := '';

  FTablesLabel := TLabel.Create(Self);
  FTablesLabel.Parent := LeftPanel;
  FTablesLabel.Left := 8;
  FTablesLabel.Top := 8;
  FTablesLabel.Width := 200;
  FTablesLabel.Caption := '可用表（双击选择）';
  FTablesLabel.Font.Style := [fsBold];

  FTableList := TListBox.Create(Self);
  FTableList.Parent := LeftPanel;
  FTableList.Left := 8;
  FTableList.Top := 28;
  FTableList.Width := 260;
  FTableList.Height := 120;
  FTableList.Sorted := True;
  FTableList.OnClick := @TableListClick;
  FTableList.OnDblClick := @TableListDblClick;

  FFieldsLabel := TLabel.Create(Self);
  FFieldsLabel.Parent := LeftPanel;
  FFieldsLabel.Left := 8;
  FFieldsLabel.Top := 160;
  FFieldsLabel.Width := 200;
  FFieldsLabel.Caption := '可用字段（双击选择）';
  FFieldsLabel.Font.Style := [fsBold];

  FFieldList := TListBox.Create(Self);
  FFieldList.Parent := LeftPanel;
  FFieldList.Left := 8;
  FFieldList.Top := 180;
  FFieldList.Width := 260;
  FFieldList.Height := 200;
  FFieldList.Sorted := True;
  FFieldList.Style := lbOwnerDrawFixed;
  FFieldList.ItemHeight := 20;
  FFieldList.OnDrawItem := @FieldListDrawItem;
  FFieldList.OnDblClick := @FieldListDblClick;

  RightPanel := TPanel.Create(Self);
  RightPanel.Parent := Self;
  RightPanel.Align := alClient;
  RightPanel.BevelOuter := bvNone;
  RightPanel.Caption := '';

  GridPanel := TPanel.Create(Self);
  GridPanel.Parent := RightPanel;
  GridPanel.Align := alTop;
  GridPanel.Height := 250;
  GridPanel.BevelOuter := bvNone;
  GridPanel.Caption := '';

  FConditionsLabel := TLabel.Create(Self);
  FConditionsLabel.Parent := GridPanel;
  FConditionsLabel.Left := 8;
  FConditionsLabel.Top := 8;
  FConditionsLabel.Width := 200;
  FConditionsLabel.Caption := '查询条件';
  FConditionsLabel.Font.Style := [fsBold];

  FConditionGrid := TStringGrid.Create(Self);
  FConditionGrid.Parent := GridPanel;
  FConditionGrid.Left := 8;
  FConditionGrid.Top := 28;
  FConditionGrid.Width := 620;
  FConditionGrid.Height := 180;
  FConditionGrid.ColCount := 7;
  FConditionGrid.RowCount := 1;
  FConditionGrid.FixedRows := 1;
  FConditionGrid.DefaultColWidth := 100;
  FConditionGrid.DefaultRowHeight := 24;
  FConditionGrid.Options := [goEditing, goTabs, goRowSizing, goColSizing, goEditing];
  FConditionGrid.OnSelectCell := @ConditionGridSelectCell;

  FConditionGrid.ColWidths[0] := 50;
  FConditionGrid.ColWidths[1] := 100;
  FConditionGrid.ColWidths[2] := 120;
  FConditionGrid.ColWidths[3] := 90;
  FConditionGrid.ColWidths[4] := 140;
  FConditionGrid.ColWidths[5] := 100;
  FConditionGrid.ColWidths[6] := 60;

  FConditionGrid.Cells[0, 0] := '逻辑';
  FConditionGrid.Cells[1, 0] := '表';
  FConditionGrid.Cells[2, 0] := '字段';
  FConditionGrid.Cells[3, 0] := '操作符';
  FConditionGrid.Cells[4, 0] := '值1';
  FConditionGrid.Cells[5, 0] := '值2';
  FConditionGrid.Cells[6, 0] := '启用';

  FAddBtn := TButton.Create(Self);
  FAddBtn.Parent := GridPanel;
  FAddBtn.Left := 8;
  FAddBtn.Top := 214;
  FAddBtn.Width := 80;
  FAddBtn.Caption := '添加条件';
  FAddBtn.OnClick := @AddBtnClick;

  FRemoveBtn := TButton.Create(Self);
  FRemoveBtn.Parent := GridPanel;
  FRemoveBtn.Left := 94;
  FRemoveBtn.Top := 214;
  FRemoveBtn.Width := 80;
  FRemoveBtn.Caption := '删除选中';
  FRemoveBtn.OnClick := @RemoveBtnClick;

  FClearBtn := TButton.Create(Self);
  FClearBtn.Parent := GridPanel;
  FClearBtn.Left := 180;
  FClearBtn.Top := 214;
  FClearBtn.Width := 80;
  FClearBtn.Caption := '清空';
  FClearBtn.OnClick := @ClearBtnClick;

  SQLPanel := TPanel.Create(Self);
  SQLPanel.Parent := RightPanel;
  SQLPanel.Align := alClient;
  SQLPanel.BevelOuter := bvNone;
  SQLPanel.Caption := '';

  FSQLPreviewLabel := TLabel.Create(Self);
  FSQLPreviewLabel.Parent := SQLPanel;
  FSQLPreviewLabel.Left := 8;
  FSQLPreviewLabel.Top := 8;
  FSQLPreviewLabel.Width := 200;
  FSQLPreviewLabel.Caption := '生成的 SQL 预览';
  FSQLPreviewLabel.Font.Style := [fsBold];

  FSQLMemo := TMemo.Create(Self);
  FSQLMemo.Parent := SQLPanel;
  FSQLMemo.Left := 8;
  FSQLMemo.Top := 28;
  FSQLMemo.Width := 620;
  FSQLMemo.Height := 100;
  FSQLMemo.Font.Name := 'Consolas';
  FSQLMemo.Font.Size := 10;
  FSQLMemo.ScrollBars := ssBoth;
  FSQLMemo.WordWrap := False;

  FPreviewBtn := TButton.Create(Self);
  FPreviewBtn.Parent := SQLPanel;
  FPreviewBtn.Left := 8;
  FPreviewBtn.Top := 134;
  FPreviewBtn.Width := 100;
  FPreviewBtn.Caption := '预览 SQL';
  FPreviewBtn.OnClick := @PreviewBtnClick;

  FApplyBtn := TButton.Create(Self);
  FApplyBtn.Parent := SQLPanel;
  FApplyBtn.Left := 114;
  FApplyBtn.Top := 134;
  FApplyBtn.Width := 120;
  FApplyBtn.Caption := '应用到查询';
  FApplyBtn.OnClick := @ApplyBtnClick;
end;

function TQueryBuilderPanel.GetOperatorName(Op: TQueryOperator): string;
begin
  case Op of
    opEqual: Result := '=';
    opNotEqual: Result := '!=';
    opLess: Result := '<';
    opLessOrEqual: Result := '<=';
    opGreater: Result := '>';
    opGreaterOrEqual: Result := '>=';
    opLike: Result := 'LIKE';
    opNotLike: Result := 'NOT LIKE';
    opIsNull: Result := 'IS NULL';
    opIsNotNull: Result := 'IS NOT NULL';
    opIn: Result := 'IN';
    opBetween: Result := 'BETWEEN';
  end;
end;

function TQueryBuilderPanel.GetOperatorFromString(const S: string): TQueryOperator;
var
  OpStr: string;
begin
  OpStr := UpperCase(Trim(S));
  if OpStr = '=' then Result := opEqual
  else if OpStr = '!=' then Result := opNotEqual
  else if OpStr = '<>' then Result := opNotEqual
  else if OpStr = '<' then Result := opLess
  else if OpStr = '<=' then Result := opLessOrEqual
  else if OpStr = '>' then Result := opGreater
  else if OpStr = '>=' then Result := opGreaterOrEqual
  else if OpStr = 'LIKE' then Result := opLike
  else if OpStr = 'NOT LIKE' then Result := opNotLike
  else if OpStr = 'IS NULL' then Result := opIsNull
  else if OpStr = 'IS NOT NULL' then Result := opIsNotNull
  else if OpStr = 'IN' then Result := opIn
  else if OpStr = 'BETWEEN' then Result := opBetween
  else Result := opEqual;
end;

function TQueryBuilderPanel.GetLogicName(Log: TQueryLogic): string;
begin
  case Log of
    qlAnd: Result := 'AND';
    qlOr: Result := 'OR';
  end;
end;

function TQueryBuilderPanel.GetLogicFromString(const S: string): TQueryLogic;
var
  LogStr: string;
begin
  LogStr := UpperCase(Trim(S));
  if LogStr = 'OR' then Result := qlOr
  else Result := qlAnd;
end;

procedure TQueryBuilderPanel.TableListClick(Sender: TObject);
begin
  if FTableList.ItemIndex >= 0 then
  begin
    FSelectedTable := FTableList.Items[FTableList.ItemIndex];
    LoadFields(FSelectedTable);
  end;
end;

procedure TQueryBuilderPanel.TableListDblClick(Sender: TObject);
begin
  if FTableList.ItemIndex >= 0 then
  begin
    FSelectedTable := FTableList.Items[FTableList.ItemIndex];
    LoadFields(FSelectedTable);
  end;
end;

procedure TQueryBuilderPanel.FieldListDblClick(Sender: TObject);
var
  FieldName: string;
begin
  if FFieldList.ItemIndex >= 0 then
  begin
    FieldName := FFieldList.Items[FFieldList.ItemIndex];
    if Pos(':', FieldName) > 0 then
      FieldName := Copy(FieldName, 1, Pos(':', FieldName) - 1);
    FieldName := Trim(FieldName);

    if FConditionGrid.RowCount = 1 then
      FConditionGrid.RowCount := 2;

    FConditionGrid.RowCount := FConditionGrid.RowCount + 1;
    FConditionGrid.Cells[0, FConditionGrid.RowCount - 1] := 'AND';
    FConditionGrid.Cells[1, FConditionGrid.RowCount - 1] := FSelectedTable;
    FConditionGrid.Cells[2, FConditionGrid.RowCount - 1] := FieldName;
    FConditionGrid.Cells[3, FConditionGrid.RowCount - 1] := '=';
    FConditionGrid.Cells[4, FConditionGrid.RowCount - 1] := '';
    FConditionGrid.Cells[5, FConditionGrid.RowCount - 1] := '';
    FConditionGrid.Cells[6, FConditionGrid.RowCount - 1] := '是';
  end;
end;

procedure TQueryBuilderPanel.FieldListDrawItem(Control: TWinControl;
  Index: Integer; ARect: TRect; State: TOwnerDrawState);
var
  ListBox: TListBox;
  Canvas: TCanvas;
  S: string;
  ColIdx: Integer;
  FieldName, FieldType: string;
begin
  ListBox := TListBox(Control);
  Canvas := ListBox.Canvas;

  if odSelected in State then
  begin
    Canvas.Brush.Color := clHighlight;
    Canvas.Font.Color := clHighlightText;
  end
  else
  begin
    Canvas.Brush.Color := ListBox.Color;
    Canvas.Font.Color := ListBox.Font.Color;
  end;

  Canvas.FillRect(ARect);
  S := ListBox.Items[Index];

  ColIdx := Pos(':', S);
  if ColIdx > 0 then
  begin
    FieldName := Trim(Copy(S, 1, ColIdx - 1));
    FieldType := Trim(Copy(S, ColIdx + 1, MaxInt));

    Canvas.Font.Style := [];
    Canvas.TextOut(ARect.Left + 4, ARect.Top + 2, FieldName);

    Canvas.Font.Color := clGray;
    Canvas.TextOut(ARect.Left + 120, ARect.Top + 2, ': ' + FieldType);
  end
  else
  begin
    Canvas.TextOut(ARect.Left + 4, ARect.Top + 2, S);
  end;
end;

procedure TQueryBuilderPanel.OperatorComboChange(Sender: TObject);
begin
  if FOperatorCombo.Text = 'IS NULL' then
  begin
    FValue1Edit.Enabled := False;
    FValue1Edit.Text := '';
    FValue2Edit.Enabled := False;
    FValue2Edit.Text := '';
  end
  else if FOperatorCombo.Text = 'BETWEEN' then
  begin
    FValue1Edit.Enabled := True;
    FValue2Edit.Enabled := True;
  end
  else
  begin
    FValue1Edit.Enabled := True;
    FValue2Edit.Enabled := False;
    FValue2Edit.Text := '';
  end;
end;

procedure TQueryBuilderPanel.AddBtnClick(Sender: TObject);
begin
  if FSelectedTable = '' then
  begin
    ShowMessage('请先选择一个表');
    Exit;
  end;

  if FConditionGrid.RowCount = 1 then
    FConditionGrid.RowCount := 2;

  FConditionGrid.RowCount := FConditionGrid.RowCount + 1;
  FConditionGrid.Cells[0, FConditionGrid.RowCount - 1] := 'AND';
  FConditionGrid.Cells[1, FConditionGrid.RowCount - 1] := FSelectedTable;
  FConditionGrid.Cells[2, FConditionGrid.RowCount - 1] := '';
  FConditionGrid.Cells[3, FConditionGrid.RowCount - 1] := '=';
  FConditionGrid.Cells[4, FConditionGrid.RowCount - 1] := '';
  FConditionGrid.Cells[5, FConditionGrid.RowCount - 1] := '';
  FConditionGrid.Cells[6, FConditionGrid.RowCount - 1] := '是';
end;

procedure TQueryBuilderPanel.RemoveBtnClick(Sender: TObject);
var
  i: Integer;
begin
  for i := FConditionGrid.RowCount - 1 downto 1 do
  begin
    if FConditionGrid.Selection.Top = i then
    begin
      FConditionGrid.DeleteRow(i);
      Break;
    end;
  end;
  if FConditionGrid.RowCount <= 1 then
    FConditionGrid.RowCount := 1;
end;

procedure TQueryBuilderPanel.ClearBtnClick(Sender: TObject);
begin
  if MessageDlg('确定要清空所有条件吗？', mtConfirmation, [mbYes, mbNo], 0) = mrYes then
    ClearConditions;
end;

procedure TQueryBuilderPanel.ConditionGridSelectCell(Sender: TObject; aCol,
  aRow: Integer; var CanSelect: Boolean);
begin
  CanSelect := True;
end;

function TQueryBuilderPanel.BuildSQL: string;
var
  i: Integer;
  Logic: TQueryLogic;
  TableName, FieldName, Operator, Value1, Value2, Enabled: string;
  Item: TQueryConditionItem;
  FirstCond: Boolean;
begin
  Result := '';
  FirstCond := True;

  if FSelectedTable = '' then
  begin
    if FConditionGrid.RowCount <= 1 then
    begin
      Result := 'SELECT * FROM <请选择表>';
      Exit;
    end;
  end;

  for i := 1 to FConditionGrid.RowCount - 1 do
  begin
    Enabled := UpperCase(Trim(FConditionGrid.Cells[6, i]));
    if (Enabled = '否') or (Enabled = 'N') or (Enabled = 'FALSE') or (Enabled = '0') then
      Continue;

    Logic := GetLogicFromString(FConditionGrid.Cells[0, i]);
    TableName := Trim(FConditionGrid.Cells[1, i]);
    FieldName := Trim(FConditionGrid.Cells[2, i]);
    Operator := Trim(FConditionGrid.Cells[3, i]);
    Value1 := Trim(FConditionGrid.Cells[4, i]);
    Value2 := Trim(FConditionGrid.Cells[5, i]);

    if TableName = '' then TableName := FSelectedTable;
    if TableName = '' then Continue;
    if FieldName = '' then Continue;

    Item := TQueryConditionItem.Create;
    try
      Item.Table := TableName;
      Item.Field := FieldName;
      Item.Operator := GetOperatorFromString(Operator);
      Item.Value1 := Value1;
      Item.Value2 := Value2;
      Item.Logic := Logic;

      if FirstCond then
      begin
        Result := Item.ToSQL;
        FirstCond := False;
      end
      else
      begin
        if Trim(Result) <> '' then
          Result := Result + ' ' + GetLogicName(Logic) + ' ' + Item.ToSQL
        else
          Result := Item.ToSQL;
      end;
    finally
      Item.Free;
    end;
  end;

  if FSelectedTable <> '' then
  begin
    if Trim(Result) <> '' then
      Result := 'SELECT * FROM ' + FSelectedTable + ' WHERE ' + Result
    else
      Result := 'SELECT * FROM ' + FSelectedTable;
  end
  else
  begin
    if Trim(Result) <> '' then
      Result := 'SELECT * FROM <请选择表> WHERE ' + Result
    else
      Result := 'SELECT * FROM <请选择表>';
  end;
end;

procedure TQueryBuilderPanel.PreviewBtnClick(Sender: TObject);
begin
  FSQLMemo.Text := BuildSQL;
  if Assigned(FManager) and Assigned(FManager.OnPreviewSQL) then
    FManager.OnPreviewSQL(FSQLMemo.Text);
end;

procedure TQueryBuilderPanel.ApplyBtnClick(Sender: TObject);
var
  SQL: string;
begin
  SQL := BuildSQL;
  FSQLMemo.Text := SQL;
  if Assigned(FManager) and Assigned(FManager.OnApplySQL) then
    FManager.OnApplySQL(SQL);
end;

procedure TQueryBuilderPanel.LoadTables;
var
  Tables: TStringList;
begin
  if not Assigned(FManager) or not Assigned(FManager.Connection) or
     not FManager.Connection.IsConnected then
  begin
    FTableList.Items.Clear;
    FFieldList.Items.Clear;
    FSelectedTable := '';
    Exit;
  end;

  try
    Tables := FManager.Connection.GetTables;
    try
      FTableList.Items.Assign(Tables);
    finally
      Tables.Free;
    end;

    if FTableList.Items.Count > 0 then
    begin
      FTableList.ItemIndex := 0;
      FSelectedTable := FTableList.Items[0];
      LoadFields(FSelectedTable);
    end
    else
    begin
      FSelectedTable := '';
      FFieldList.Items.Clear;
    end;
  except
    on E: Exception do
      ShowMessage('加载表列表失败: ' + E.Message);
  end;
end;

procedure TQueryBuilderPanel.LoadFields(const ATable: string);
var
  Query: TSQLQuery;
  FieldInfo: string;
begin
  FFieldList.Items.Clear;
  if (ATable = '') or not Assigned(FManager) or not Assigned(FManager.Connection) then
    Exit;

  try
    Query := FManager.Connection.ExecuteQuery('PRAGMA table_info(' + ATable + ')');
    try
      while not Query.EOF do
      begin
        FieldInfo := Query.FieldByName('name').AsString + ': ' + Query.FieldByName('type').AsString;
        if Query.FieldByName('pk').AsInteger > 0 then
          FieldInfo := FieldInfo + ' (PK)';
        FFieldList.Items.Add(FieldInfo);
        Query.Next;
      end;
    finally
      Query.Free;
    end;
  except
    on E: Exception do
      ShowMessage('加载字段失败: ' + E.Message);
  end;
end;

procedure TQueryBuilderPanel.ClearConditions;
begin
  FConditionGrid.RowCount := 1;
  FSQLMemo.Clear;
end;

{ TQueryBuilderManager }

constructor TQueryBuilderManager.Create(AConnection: TDBConnection; AParent: TWinControl);
begin
  inherited Create;
  FConnection := AConnection;
  FPanel := TQueryBuilderPanel.Create(AParent, Self);
  FPanel.Parent := AParent;
  FPanel.Align := alClient;
end;

destructor TQueryBuilderManager.Destroy;
begin
  FPanel.Free;
  inherited Destroy;
end;

procedure TQueryBuilderManager.LoadTables;
begin
  if Assigned(FPanel) then
    FPanel.LoadTables;
end;

procedure TQueryBuilderManager.Clear;
begin
  if Assigned(FPanel) then
  begin
    FPanel.ClearConditions;
    FPanel.LoadTables;
  end;
end;

end.
