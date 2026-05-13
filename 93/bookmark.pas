unit bookmark;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, Contnrs, INIFiles, Forms;

type
  TBookmarkItem = class
  private
    FName: string;
    FSQL: string;
    FDescription: string;
    FModified: TDateTime;
  public
    property Name: string read FName write FName;
    property SQL: string read FSQL write FSQL;
    property Description: string read FDescription write FDescription;
    property Modified: TDateTime read FModified write FModified;
  end;

  TBookmarkManager = class
  private
    FItems: TObjectList;
    FFileName: string;
    function GetCount: Integer;
    function GetItem(Index: Integer): TBookmarkItem;
  public
    constructor Create;
    destructor Destroy; override;
    function Add(const AName, ASQL, ADescription: string): TBookmarkItem;
    procedure Delete(Index: Integer);
    procedure Update(Index: Integer; const AName, ASQL, ADescription: string);
    function FindByName(const AName: string): TBookmarkItem;
    function IndexOf(Item: TBookmarkItem): Integer;
    procedure Load;
    procedure Save;
    procedure Clear;
    function GetUniqueName(const ABaseName: string): string;
    property Count: Integer read GetCount;
    property Items[Index: Integer]: TBookmarkItem read GetItem; default;
    property FileName: string read FFileName write FFileName;
  end;

implementation

constructor TBookmarkManager.Create;
begin
  inherited Create;
  FItems := TObjectList.Create(True);
  FFileName := ExtractFilePath(Application.ExeName) + 'bookmarks.ini';
end;

destructor TBookmarkManager.Destroy;
begin
  FItems.Free;
  inherited Destroy;
end;

function TBookmarkManager.GetCount: Integer;
begin
  Result := FItems.Count;
end;

function TBookmarkManager.GetItem(Index: Integer): TBookmarkItem;
begin
  if (Index >= 0) and (Index < FItems.Count) then
    Result := TBookmarkItem(FItems[Index])
  else
    Result := nil;
end;

function TBookmarkManager.Add(const AName, ASQL, ADescription: string): TBookmarkItem;
begin
  Result := TBookmarkItem.Create;
  Result.Name := AName;
  Result.SQL := ASQL;
  Result.Description := ADescription;
  Result.Modified := Now;
  FItems.Add(Result);
end;

procedure TBookmarkManager.Delete(Index: Integer);
begin
  if (Index >= 0) and (Index < FItems.Count) then
    FItems.Delete(Index);
end;

procedure TBookmarkManager.Update(Index: Integer; const AName, ASQL, ADescription: string);
var
  Item: TBookmarkItem;
begin
  Item := GetItem(Index);
  if Assigned(Item) then
  begin
    Item.Name := AName;
    Item.SQL := ASQL;
    Item.Description := ADescription;
    Item.Modified := Now;
  end;
end;

function TBookmarkManager.FindByName(const AName: string): TBookmarkItem;
var
  i: Integer;
begin
  Result := nil;
  for i := 0 to FItems.Count - 1 do
  begin
    if SameText(TBookmarkItem(FItems[i]).Name, AName) then
    begin
      Result := TBookmarkItem(FItems[i]);
      Break;
    end;
  end;
end;

function TBookmarkManager.IndexOf(Item: TBookmarkItem): Integer;
begin
  Result := FItems.IndexOf(Item);
end;

function TBookmarkManager.GetUniqueName(const ABaseName: string): string;
var
  i: Integer;
  Candidate: string;
begin
  Result := ABaseName;
  i := 1;
  while Assigned(FindByName(Result)) do
  begin
    Inc(i);
    Candidate := ABaseName + ' (' + IntToStr(i) + ')';
    Result := Candidate;
  end;
end;

procedure TBookmarkManager.Clear;
begin
  FItems.Clear;
end;

procedure TBookmarkManager.Load;
var
  Ini: TINIFile;
  i, Count: Integer;
  Section: string;
  Name, SQL, Desc: string;
  Modified: TDateTime;
begin
  Clear;
  if not FileExists(FFileName) then Exit;

  Ini := TINIFile.Create(FFileName);
  try
    Count := Ini.ReadInteger('General', 'Count', 0);
    for i := 0 to Count - 1 do
    begin
      Section := 'Bookmark_' + IntToStr(i);
      if Ini.SectionExists(Section) then
      begin
        Name := Ini.ReadString(Section, 'Name', '');
        SQL := Ini.ReadString(Section, 'SQL', '');
        Desc := Ini.ReadString(Section, 'Description', '');
        Modified := Ini.ReadDateTime(Section, 'Modified', Now);
        if Name <> '' then
        begin
          Add(Name, SQL, Desc).Modified := Modified;
        end;
      end;
    end;
  finally
    Ini.Free;
  end;
end;

procedure TBookmarkManager.Save;
var
  Ini: TINIFile;
  i: Integer;
  Section: string;
  Item: TBookmarkItem;
begin
  Ini := TINIFile.Create(FFileName);
  try
    Ini.EraseSection('General');
    Ini.WriteInteger('General', 'Count', FItems.Count);

    for i := 0 to FItems.Count - 1 do
    begin
      Section := 'Bookmark_' + IntToStr(i);
      Item := TBookmarkItem(FItems[i]);
      Ini.EraseSection(Section);
      Ini.WriteString(Section, 'Name', Item.Name);
      Ini.WriteString(Section, 'SQL', Item.SQL);
      Ini.WriteString(Section, 'Description', Item.Description);
      Ini.WriteDateTime(Section, 'Modified', Item.Modified);
    end;

    Ini.UpdateFile;
  finally
    Ini.Free;
  end;
end;

end.
