unit connection;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, sqldb, sqlite3conn, LazUTF8;

type
  TDBConnection = class
  private
    FConnection: TSQLite3Connection;
    FTransaction: TSQLTransaction;
    FConnected: Boolean;
    FDatabasePath: string;
  public
    constructor Create;
    destructor Destroy; override;
    function Connect(const ADatabasePath: string): Boolean;
    procedure Disconnect;
    function ExecuteQuery(const ASQL: string): TSQLQuery;
    function ExecuteSQL(const ASQL: string): Integer;
    function IsConnected: Boolean;
    function GetTables: TStringList;
    property Connection: TSQLite3Connection read FConnection;
    property DatabasePath: string read FDatabasePath;
  end;

implementation

constructor TDBConnection.Create;
begin
  inherited Create;
  FConnected := False;
  FDatabasePath := '';
  FConnection := TSQLite3Connection.Create(nil);
  FTransaction := TSQLTransaction.Create(nil);
  FTransaction.DataBase := FConnection;
  FConnection.Transaction := FTransaction;
end;

destructor TDBConnection.Destroy;
begin
  Disconnect;
  FTransaction.Free;
  FConnection.Free;
  inherited Destroy;
end;

function TDBConnection.Connect(const ADatabasePath: string): Boolean;
begin
  Result := False;
  try
    Disconnect;
    FDatabasePath := ADatabasePath;
    {$IFDEF MSWINDOWS}
    FConnection.DatabaseName := UTF8ToSys(ADatabasePath);
    {$ELSE}
    FConnection.DatabaseName := ADatabasePath;
    {$ENDIF}
    FConnection.CharSet := 'UTF8';
    FConnection.Connected := True;
    FConnected := FConnection.Connected;
    Result := FConnected;
  except
    FConnected := False;
    raise;
  end;
end;

procedure TDBConnection.Disconnect;
begin
  try
    if Assigned(FTransaction) and FTransaction.Active then
      FTransaction.Commit;
  except
  end;
  try
    if Assigned(FConnection) then
      FConnection.Connected := False;
  finally
    FConnected := False;
  end;
end;

function TDBConnection.ExecuteQuery(const ASQL: string): TSQLQuery;
begin
  Result := nil;
  if not FConnected then
    raise Exception.Create('数据库未连接');

  Result := TSQLQuery.Create(nil);
  try
    Result.DataBase := FConnection;
    Result.Transaction := FTransaction;
    Result.SQL.Text := ASQL;
    Result.RequestLive := True;
    Result.UpdateMode := upWhereAll;
    Result.Open;
  except
    Result.Free;
    raise;
  end;
end;

function TDBConnection.ExecuteSQL(const ASQL: string): Integer;
begin
  Result := 0;
  if not FConnected then
    raise Exception.Create('数据库未连接');

  if not FTransaction.Active then
    FTransaction.StartTransaction;
  try
    FConnection.ExecuteDirect(ASQL);
    Result := FConnection.RowsAffected;
    if FTransaction.Active then
      FTransaction.Commit;
  except
    if FTransaction.Active then
      FTransaction.Rollback;
    raise;
  end;
end;

function TDBConnection.IsConnected: Boolean;
begin
  Result := FConnected and Assigned(FConnection) and FConnection.Connected;
end;

function TDBConnection.GetTables: TStringList;
var
  Query: TSQLQuery;
begin
  Result := TStringList.Create;
  try
    Query := ExecuteQuery(
      'SELECT name FROM sqlite_master WHERE type=''table'' AND name NOT LIKE ''sqlite_%'' ORDER BY name'
    );
    try
      while not Query.EOF do
      begin
        Result.Add(Query.Fields[0].AsString);
        Query.Next;
      end;
    finally
      Query.Free;
    end;
  except
    Result.Free;
    raise;
  end;
end;

end.
