unit export;

{$mode objfpc}{$H+}

interface

uses
  Classes, SysUtils, DB, sqldb, Dialogs;

type
  TCSVExporter = class
  private
    FDelimiter: Char;
    FQuoteChar: Char;
    FIncludeHeader: Boolean;
    FUseQuoteAlways: Boolean;
    function EscapeField(const AValue: string): string;
  public
    constructor Create;
    function ExportToCSV(AQuery: TSQLQuery; const AFileName: string): Integer; overload;
    function ExportToCSV(ADataSet: TDataSet; const AFileName: string): Integer; overload;
    property Delimiter: Char read FDelimiter write FDelimiter;
    property QuoteChar: Char read FQuoteChar write FQuoteChar;
    property IncludeHeader: Boolean read FIncludeHeader write FIncludeHeader;
    property UseQuoteAlways: Boolean read FUseQuoteAlways write FUseQuoteAlways;
  end;

implementation

constructor TCSVExporter.Create;
begin
  inherited Create;
  FDelimiter := ',';
  FQuoteChar := '"';
  FIncludeHeader := True;
  FUseQuoteAlways := False;
end;

function TCSVExporter.EscapeField(const AValue: string): string;
var
  NeedQuote: Boolean;
  i: Integer;
begin
  NeedQuote := FUseQuoteAlways;
  Result := AValue;

  if not NeedQuote then
  begin
    for i := 1 to Length(AValue) do
    begin
      case AValue[i] of
        FDelimiter, FQuoteChar, #13, #10:
          begin
            NeedQuote := True;
            Break;
          end;
      end;
    end;
  end;

  if Pos(FQuoteChar, Result) > 0 then
    Result := StringReplace(Result, FQuoteChar, FQuoteChar + FQuoteChar, [rfReplaceAll]);

  if NeedQuote then
    Result := FQuoteChar + Result + FQuoteChar;
end;

function TCSVExporter.ExportToCSV(AQuery: TSQLQuery; const AFileName: string): Integer;
begin
  Result := ExportToCSV(TDataSet(AQuery), AFileName);
end;

function TCSVExporter.ExportToCSV(ADataSet: TDataSet; const AFileName: string): Integer;
var
  Stream: TFileStream;
  Writer: TStreamWriter;
  i: Integer;
  Line: string;
  FieldValue: string;
  BOM: TBytes;
begin
  Result := 0;
  if not Assigned(ADataSet) or not ADataSet.Active then
    raise Exception.Create('数据集无效或未打开');

  BOM := TEncoding.UTF8.GetPreamble;
  Stream := TFileStream.Create(AFileName, fmCreate or fmShareDenyWrite);
  try
    if Length(BOM) > 0 then
      Stream.WriteBuffer(BOM[0], Length(BOM));

    Writer := TStreamWriter.Create(Stream, TEncoding.UTF8);
    try
      Writer.AutoFlush := False;

      if FIncludeHeader then
      begin
        Line := '';
        for i := 0 to ADataSet.Fields.Count - 1 do
        begin
          if i > 0 then
            Line := Line + FDelimiter;
          Line := Line + EscapeField(ADataSet.Fields[i].DisplayLabel);
        end;
        Writer.WriteLine(Line);
      end;

      ADataSet.First;
      while not ADataSet.EOF do
      begin
        Line := '';
        for i := 0 to ADataSet.Fields.Count - 1 do
        begin
          if i > 0 then
            Line := Line + FDelimiter;

          if ADataSet.Fields[i].IsNull then
            FieldValue := ''
          else
            FieldValue := ADataSet.Fields[i].AsString;

          Line := Line + EscapeField(FieldValue);
        end;
        Writer.WriteLine(Line);
        Inc(Result);
        ADataSet.Next;
      end;

      Writer.Flush;
    finally
      Writer.Free;
    end;
  finally
    Stream.Free;
  end;
end;

end.
