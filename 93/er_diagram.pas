unit er_diagram;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Controls, Graphics, Grids, DB, sqldb, connection,
  Forms, Dialogs, ExtCtrls;

type
  TERTableNode = class
  private
    FTableName: string;
    FColumns: TStringList;
    FColumnTypes: TStringList;
    FPrimaryKeys: TStringList;
    FX: Integer;
    FY: Integer;
    FWidth: Integer;
    FHeight: Integer;
    FSelected: Boolean;
  public
    constructor Create;
    destructor Destroy; override;
    function GetColumnIndex(const AName: string): Integer;
    function IsPrimaryKey(const AName: string): Boolean;
    property TableName: string read FTableName write FTableName;
    property Columns: TStringList read FColumns;
    property ColumnTypes: TStringList read FColumnTypes;
    property PrimaryKeys: TStringList read FPrimaryKeys;
    property X: Integer read FX write FX;
    property Y: Integer read FY write FY;
    property Width: Integer read FWidth write FWidth;
    property Height: Integer read FHeight write FHeight;
    property Selected: Boolean read FSelected write FSelected;
  end;

  TERDiagramManager = class;

  TERDrawGrid = class(TCustomDrawGrid)
  private
    FManager: TERDiagramManager;
    FOffsetX: Integer;
    FOffsetY: Integer;
    FZoom: Double;
    FDragging: Boolean;
    FDragStartX: Integer;
    FDragStartY: Integer;
    FDragNode: TERTableNode;
    FLastMouseX: Integer;
    FLastMouseY: Integer;
    procedure GridDrawCell(Sender: TObject; aCol, aRow: Integer; aRect: TRect;
      aState: TGridDrawState);
    procedure GridMouseDown(Sender: TObject; Button: TMouseButton;
      Shift: TShiftState; X, Y: Integer);
    procedure GridMouseMove(Sender: TObject; Shift: TShiftState; X, Y: Integer);
    procedure GridMouseUp(Sender: TObject; Button: TMouseButton;
      Shift: TShiftState; X, Y: Integer);
    procedure GridDblClick(Sender: TObject);
    function GetNodeAt(X, Y: Integer): TERTableNode;
  public
    constructor Create(AOwner: TComponent; AManager: TERDiagramManager); reintroduce;
    procedure SetOffset(AX, AY: Integer);
    procedure SetZoom(AValue: Double);
    property OffsetX: Integer read FOffsetX write FOffsetX;
    property OffsetY: Integer read FOffsetY write FOffsetY;
    property Zoom: Double read FZoom write FZoom;
  end;

  TERDiagramManager = class
  private
    FGrid: TERDrawGrid;
    FConnection: TDBConnection;
    FNodes: TObjectList;
    FOnTableDblClick: TNotifyEvent;
    FSelectedNode: TERTableNode;
  public
    constructor Create(AGrid: TCustomDrawGrid; AConnection: TDBConnection);
    destructor Destroy; override;
    procedure LoadTables;
    procedure Clear;
    procedure Refresh;
    function GetNodeByName(const ATableName: string): TERTableNode;
    property Nodes: TObjectList read FNodes;
    property SelectedNode: TERTableNode read FSelectedNode write FSelectedNode;
    property Connection: TDBConnection read FConnection write FConnection;
    property OnTableDblClick: TNotifyEvent read FOnTableDblClick write FOnTableDblClick;
    property Grid: TERDrawGrid read FGrid;
  end;

implementation

{ TERTableNode }

constructor TERTableNode.Create;
begin
  inherited Create;
  FColumns := TStringList.Create;
  FColumnTypes := TStringList.Create;
  FPrimaryKeys := TStringList.Create;
  FX := 20;
  FY := 20;
  FWidth := 200;
  FHeight := 100;
  FSelected := False;
end;

destructor TERTableNode.Destroy;
begin
  FPrimaryKeys.Free;
  FColumnTypes.Free;
  FColumns.Free;
  inherited Destroy;
end;

function TERTableNode.GetColumnIndex(const AName: string): Integer;
begin
  Result := FColumns.IndexOf(AName);
end;

function TERTableNode.IsPrimaryKey(const AName: string): Boolean;
begin
  Result := FPrimaryKeys.IndexOf(AName) >= 0;
end;

{ TERDrawGrid }

constructor TERDrawGrid.Create(AOwner: TComponent; AManager: TERDiagramManager);
begin
  inherited Create(AOwner);
  FManager := AManager;
  FOffsetX := 0;
  FOffsetY := 0;
  FZoom := 1.0;
  FDragging := False;
  FDragNode := nil;

  ColCount := 1;
  RowCount := 1;
  DefaultColWidth := 100;
  DefaultRowHeight := 100;
  Options := Options + [goEditing, goDrawFocusSelected, goThumbTracking];
  Options := Options - [goVertLine, goHorzLine, goFixedVertLine, goFixedHorzLine];
  OnDrawCell := @GridDrawCell;
  OnMouseDown := @GridMouseDown;
  OnMouseMove := @GridMouseMove;
  OnMouseUp := @GridMouseUp;
  OnDblClick := @GridDblClick;
end;

procedure TERDrawGrid.SetOffset(AX, AY: Integer);
begin
  FOffsetX := AX;
  FOffsetY := AY;
  Invalidate;
end;

procedure TERDrawGrid.SetZoom(AValue: Double);
begin
  if AValue < 0.25 then AValue := 0.25;
  if AValue > 3.0 then AValue := 3.0;
  FZoom := AValue;
  Invalidate;
end;

function TERDrawGrid.GetNodeAt(X, Y: Integer): TERTableNode;
var
  i: Integer;
  Node: TERTableNode;
  NodeRect: TRect;
begin
  Result := nil;
  X := Round((X - FOffsetX) / FZoom);
  Y := Round((Y - FOffsetY) / FZoom);

  for i := FManager.Nodes.Count - 1 downto 0 do
  begin
    Node := TERTableNode(FManager.Nodes[i]);
    NodeRect := Rect(Node.X, Node.Y, Node.X + Node.Width, Node.Y + Node.Height);
    if (X >= NodeRect.Left) and (X <= NodeRect.Right) and
       (Y >= NodeRect.Top) and (Y <= NodeRect.Bottom) then
    begin
      Result := Node;
      Break;
    end;
  end;
end;

procedure TERDrawGrid.GridDrawCell(Sender: TObject; aCol, aRow: Integer;
  aRect: TRect; aState: TGridDrawState);
var
  Canvas: TCanvas;
  i, j: Integer;
  Node: TERTableNode;
  NodeRect: TRect;
  TextRect: TRect;
  RowHeight: Integer;
  ColName, ColType: string;
  IsPK: Boolean;
  HeaderColor, BodyColor, TextColor, BorderColor: TColor;
begin
  Canvas := Self.Canvas;
  Canvas.Brush.Color := clBtnFace;
  Canvas.FillRect(aRect);

  if not Assigned(FManager) then Exit;
  if FManager.Nodes.Count = 0 then
  begin
    Canvas.Font.Color := clGray;
    Canvas.TextOut(aRect.Left + 10, aRect.Top + 10, '连接数据库后显示 ER 图...');
    Exit;
  end;

  for i := 0 to FManager.Nodes.Count - 1 do
  begin
    Node := TERTableNode(FManager.Nodes[i]);

    NodeRect.Left := Round(Node.X * FZoom + FOffsetX);
    NodeRect.Top := Round(Node.Y * FZoom + FOffsetY);
    NodeRect.Right := NodeRect.Left + Round(Node.Width * FZoom);
    NodeRect.Bottom := NodeRect.Top + Round(Node.Height * FZoom);

    if NodeRect.Right < aRect.Left then Continue;
    if NodeRect.Left > aRect.Right then Continue;
    if NodeRect.Bottom < aRect.Top then Continue;
    if NodeRect.Top > aRect.Bottom then Continue;

    if Node.Selected then
    begin
      HeaderColor := $00D4A06A;
      BodyColor := $00FFF4E8;
      BorderColor := $00B08040;
    end
    else
    begin
      HeaderColor := $00E8E8E8;
      BodyColor := clWindow;
      BorderColor := clGray;
    end;
    TextColor := clWindowText;

    RowHeight := Round(24 * FZoom);

    Canvas.Brush.Color := HeaderColor;
    Canvas.Pen.Color := BorderColor;
    Canvas.Pen.Width := 2;
    Canvas.Rectangle(NodeRect);
    Canvas.Pen.Width := 1;

    TextRect := Rect(NodeRect.Left + Round(8 * FZoom), NodeRect.Top + Round(2 * FZoom),
                     NodeRect.Right - Round(8 * FZoom), NodeRect.Top + RowHeight);
    Canvas.Brush.Color := HeaderColor;
    Canvas.Font.Color := TextColor;
    Canvas.Font.Style := [fsBold];
    Canvas.Font.Size := Round(10 * FZoom);
    Canvas.TextRect(TextRect, Node.TableName, [tfVerticalCenter, tfLeft]);

    Canvas.Pen.Color := BorderColor;
    Canvas.MoveTo(NodeRect.Left, NodeRect.Top + RowHeight);
    Canvas.LineTo(NodeRect.Right, NodeRect.Top + RowHeight);

    Canvas.Brush.Color := BodyColor;
    Canvas.FillRect(Rect(NodeRect.Left + 1, NodeRect.Top + RowHeight + 1,
                         NodeRect.Right - 1, NodeRect.Bottom - 1));

    Canvas.Font.Style := [];
    Canvas.Font.Size := Round(9 * FZoom);

    for j := 0 to Node.Columns.Count - 1 do
    begin
      if j >= 20 then Break;

      ColName := Node.Columns[j];
      ColType := '';
      if j < Node.ColumnTypes.Count then
        ColType := Node.ColumnTypes[j];
      IsPK := Node.IsPrimaryKey(ColName);

      TextRect := Rect(NodeRect.Left + Round(12 * FZoom),
                       NodeRect.Top + RowHeight + j * RowHeight + Round(2 * FZoom),
                       NodeRect.Right - Round(8 * FZoom),
                       NodeRect.Top + RowHeight + (j + 1) * RowHeight);

      if IsPK then
        Canvas.Font.Style := [fsBold]
      else
        Canvas.Font.Style := [];

      Canvas.Brush.Color := BodyColor;
      if IsPK then
        Canvas.Font.Color := $00804040
      else
        Canvas.Font.Color := TextColor;

      if IsPK then
        Canvas.TextOut(TextRect.Left, TextRect.Top + 2, '🔑 ')
      else
        Canvas.TextOut(TextRect.Left, TextRect.Top + 2, '   ');

      Canvas.TextOut(TextRect.Left + Round(20 * FZoom), TextRect.Top + 2, ColName);

      Canvas.Font.Color := clGray;
      Canvas.Font.Style := [];
      Canvas.TextOut(TextRect.Left + Round(120 * FZoom), TextRect.Top + 2, ColType);
    end;
  end;
end;

procedure TERDrawGrid.GridMouseDown(Sender: TObject; Button: TMouseButton;
  Shift: TShiftState; X, Y: Integer);
var
  Node: TERTableNode;
  i: Integer;
begin
  if Button = mbLeft then
  begin
    Node := GetNodeAt(X, Y);

    for i := 0 to FManager.Nodes.Count - 1 do
      TERTableNode(FManager.Nodes[i]).Selected := False;

    if Assigned(Node) then
    begin
      Node.Selected := True;
      FManager.SelectedNode := Node;
      FDragging := True;
      FDragNode := Node;
      FDragStartX := X;
      FDragStartY := Y;
      FLastMouseX := X;
      FLastMouseY := Y;
    end
    else
    begin
      FManager.SelectedNode := nil;
      FDragging := False;
      FDragNode := nil;
    end;

    Invalidate;
  end;
end;

procedure TERDrawGrid.GridMouseMove(Sender: TObject; Shift: TShiftState;
  X, Y: Integer);
var
  DeltaX, DeltaY: Integer;
begin
  if FDragging and Assigned(FDragNode) then
  begin
    DeltaX := Round((X - FLastMouseX) / FZoom);
    DeltaY := Round((Y - FLastMouseY) / FZoom);

    FDragNode.X := FDragNode.X + DeltaX;
    FDragNode.Y := FDragNode.Y + DeltaY;

    if FDragNode.X < 0 then FDragNode.X := 0;
    if FDragNode.Y < 0 then FDragNode.Y := 0;

    FLastMouseX := X;
    FLastMouseY := Y;
    Invalidate;
  end;
end;

procedure TERDrawGrid.GridMouseUp(Sender: TObject; Button: TMouseButton;
  Shift: TShiftState; X, Y: Integer);
begin
  FDragging := False;
  FDragNode := nil;
end;

procedure TERDrawGrid.GridDblClick(Sender: TObject);
var
  Node: TERTableNode;
begin
  Node := FManager.SelectedNode;
  if Assigned(Node) and Assigned(FManager.OnTableDblClick) then
    FManager.OnTableDblClick(Node);
end;

{ TERDiagramManager }

constructor TERDiagramManager.Create(AGrid: TCustomDrawGrid; AConnection: TDBConnection);
begin
  inherited Create;
  FConnection := AConnection;
  FNodes := TObjectList.Create(True);
  FSelectedNode := nil;
  FGrid := TERDrawGrid.Create(AGrid.Parent, Self);
  FGrid.Parent := AGrid.Parent;
  FGrid.Align := alClient;
  FGrid.BringToFront;
end;

destructor TERDiagramManager.Destroy;
begin
  FNodes.Free;
  inherited Destroy;
end;

procedure TERDiagramManager.Clear;
begin
  FNodes.Clear;
  FSelectedNode := nil;
  if Assigned(FGrid) then
    FGrid.Invalidate;
end;

procedure TERDiagramManager.Refresh;
begin
  if Assigned(FGrid) then
    FGrid.Invalidate;
end;

procedure TERDiagramManager.LoadTables;
var
  Tables: TStringList;
  i, j: Integer;
  TableName: string;
  Node: TERTableNode;
  Query: TSQLQuery;
  ColX, ColY: Integer;
  ColsPerRow: Integer;
begin
  Clear;
  if not Assigned(FConnection) or not FConnection.IsConnected then Exit;

  try
    Tables := FConnection.GetTables;
    try
      ColsPerRow := 3;
      for i := 0 to Tables.Count - 1 do
      begin
        TableName := Tables[i];
        Node := TERTableNode.Create;
        Node.TableName := TableName;

        try
          Query := FConnection.ExecuteQuery('PRAGMA table_info(' + TableName + ')');
          try
            while not Query.EOF do
            begin
              Node.Columns.Add(Query.FieldByName('name').AsString);
              Node.ColumnTypes.Add(Query.FieldByName('type').AsString);
              if Query.FieldByName('pk').AsInteger > 0 then
                Node.PrimaryKeys.Add(Query.FieldByName('name').AsString);
              Query.Next;
            end;
          finally
            Query.Free;
          end;
        except
        end;

        Node.Width := 220;
        Node.Height := 28 + (Node.Columns.Count + 1) * 24;
        if Node.Height > 500 then Node.Height := 500;

        ColX := i mod ColsPerRow;
        ColY := i div ColsPerRow;
        Node.X := 20 + ColX * 260;
        Node.Y := 20 + ColY * 280;

        FNodes.Add(Node);
      end;
    finally
      Tables.Free;
    end;

    Refresh;
  except
    on E: Exception do
      ShowMessage('加载 ER 图失败: ' + E.Message);
  end;
end;

function TERDiagramManager.GetNodeByName(const ATableName: string): TERTableNode;
var
  i: Integer;
begin
  Result := nil;
  for i := 0 to FNodes.Count - 1 do
  begin
    if SameText(TERTableNode(FNodes[i]).TableName, ATableName) then
    begin
      Result := TERTableNode(FNodes[i]);
      Break;
    end;
  end;
end;

end.
