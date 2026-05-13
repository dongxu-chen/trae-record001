unit dbgrid;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, DB, DBCtrls, Grids, DBGrids, sqldb, SQLDB;

type
  TDBGridManager = class
  private
    FGrid: TDBGrid;
    FDataSource: TDataSource;
    FQuery: TSQLQuery;
    procedure DataSourceDataChange(Sender: TObject; Field: TField);
  public
    constructor Create(AGrid: TDBGrid);
    destructor Destroy; override;
    procedure BindQuery(AQuery: TSQLQuery);
    procedure Clear;
    procedure Refresh;
    procedure PostChanges;
    function GetCurrentQuery: TSQLQuery;
    function GetRecordCount: Integer;
    procedure AutoSizeColumns;
    property Grid: TDBGrid read FGrid;
    property DataSource: TDataSource read FDataSource;
  end;

implementation

constructor TDBGridManager.Create(AGrid: TDBGrid);
begin
  inherited Create;
  FGrid := AGrid;
  FDataSource := TDataSource.Create(nil);
  FDataSource.OnDataChange := @DataSourceDataChange;
  FQuery := nil;
  FGrid.DataSource := FDataSource;
  FGrid.Options := FGrid.Options + [dgEditing, dgAddNew, dgDelete, dgColumnResize, dgColLines, dgRowLines, dgTabs, dgConfirmDelete, dgCancelOnExit, dgTitleClick, dgTitleHotTrack];
  FGrid.Options := FGrid.Options - [dgReadOnly];
end;

destructor TDBGridManager.Destroy;
begin
  Clear;
  FDataSource.Free;
  inherited Destroy;
end;

procedure TDBGridManager.DataSourceDataChange(Sender: TObject; Field: TField);
begin
  if Assigned(FQuery) and Assigned(FQuery.DataBase) and Assigned(FQuery.Transaction) then
  begin
    if FQuery.State in [dsEdit, dsInsert] then
    begin
      if not FQuery.Transaction.Active then
        FQuery.Transaction.StartTransaction;
    end;
  end;
end;

procedure TDBGridManager.PostChanges;
begin
  if not Assigned(FQuery) then Exit;

  if FQuery.State in [dsEdit, dsInsert] then
  begin
    FQuery.Post;
  end;

  if FQuery.Active and Assigned(FQuery.Transaction) and FQuery.Transaction.Active then
  begin
    FQuery.ApplyUpdates;
    FQuery.Transaction.Commit;
    FQuery.Refresh;
  end;
end;

procedure TDBGridManager.BindQuery(AQuery: TSQLQuery);
begin
  Clear;
  FQuery := AQuery;
  if Assigned(FQuery) then
  begin
    FDataSource.DataSet := FQuery;
    FGrid.Enabled := True;
    AutoSizeColumns;
  end
  else
  begin
    FGrid.Enabled := False;
  end;
end;

procedure TDBGridManager.Clear;
begin
  if FDataSource.DataSet <> nil then
  begin
    FDataSource.DataSet := nil;
  end;
  FQuery := nil;
end;

procedure TDBGridManager.Refresh;
begin
  if Assigned(FQuery) and FQuery.Active then
  begin
    FQuery.Refresh;
    AutoSizeColumns;
  end;
end;

function TDBGridManager.GetCurrentQuery: TSQLQuery;
begin
  Result := FQuery;
end;

function TDBGridManager.GetRecordCount: Integer;
begin
  Result := 0;
  if Assigned(FQuery) and FQuery.Active then
    Result := FQuery.RecordCount;
end;

procedure TDBGridManager.AutoSizeColumns;
var
  i: Integer;
begin
  if not Assigned(FGrid) then Exit;
  for i := 0 to FGrid.Columns.Count - 1 do
  begin
    FGrid.Columns[i].Width := FGrid.Columns[i].Width + 10;
  end;
end;

end.
