using System.Collections.Concurrent;
using System.IO;
using System.Text;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class DanmakuRecorder : IDisposable
{
    private readonly long _roomId;
    private readonly Database _db;
    private readonly DanmakuClient _client;
    private readonly HttpClient _httpClient;
    private long? _sessionId;
    private bool _isRecording;

    private readonly ConcurrentQueue<DanmakuMessage> _danmakuQueue = new();
    private readonly ConcurrentQueue<GiftMessage> _giftQueue = new();
    private readonly ConcurrentQueue<SuperChatMessage> _superChatQueue = new();
    private System.Threading.Timer? _flushTimer;
    private readonly object _queueLock = new();
    private bool _disposed;

    private readonly string _recordDir;
    private StreamWriter? _danmakuFileWriter;
    private StreamWriter? _giftFileWriter;

    public event EventHandler<DanmakuMessage>? DanmakuReceived;
    public event EventHandler<GiftMessage>? GiftReceived;
    public event EventHandler<SuperChatMessage>? SuperChatReceived;
    public event EventHandler? RecordingStarted;
    public event EventHandler? RecordingStopped;

    public bool IsRecording => _isRecording;
    public long RoomId => _roomId;
    public long? SessionId => _sessionId;

    public DanmakuRecorder(long roomId, Database db, HttpClient httpClient)
    {
        _roomId = roomId;
        _db = db;
        _httpClient = httpClient;
        _client = new DanmakuClient(roomId, httpClient);

        _recordDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyVideos),
            "BiliLiveMonitor",
            roomId.ToString()
        );

        SetupEvents();
    }

    private void SetupEvents()
    {
        _client.DanmakuReceived += (s, e) =>
        {
            _danmakuQueue.Enqueue(e);
            DanmakuReceived?.Invoke(this, e);
        };

        _client.GiftReceived += (s, e) =>
        {
            _giftQueue.Enqueue(e);
            GiftReceived?.Invoke(this, e);
        };

        _client.SuperChatReceived += (s, e) =>
        {
            _superChatQueue.Enqueue(e);
            SuperChatReceived?.Invoke(this, e);
        };

        _client.Disconnected += (s, e) =>
        {
            if (_isRecording)
            {
                _ = TryReconnectAsync();
            }
        };
    }

    public async Task<bool> StartRecordingAsync(LiveRoom roomInfo)
    {
        if (_isRecording) return true;

        try
        {
            _sessionId = _db.StartLiveSession(_roomId, roomInfo.Uid, roomInfo.UName, roomInfo.Title);

            if (!Directory.Exists(_recordDir))
            {
                Directory.CreateDirectory(_recordDir);
            }

            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var danmakuFilePath = Path.Combine(_recordDir, $"danmaku_{timestamp}.xml");
            var giftFilePath = Path.Combine(_recordDir, $"gifts_{timestamp}.txt");

            _danmakuFileWriter = new StreamWriter(danmakuFilePath, false, Encoding.UTF8)
            {
                AutoFlush = true
            };
            await WriteDanmakuXmlHeaderAsync(_danmakuFileWriter, roomInfo);

            _giftFileWriter = new StreamWriter(giftFilePath, false, Encoding.UTF8)
            {
                AutoFlush = true
            };

            var connected = await _client.ConnectAsync();
            if (!connected)
            {
                throw new InvalidOperationException("无法连接弹幕服务器");
            }

            _flushTimer = new System.Threading.Timer(FlushQueues, null, 1000, 1000);

            _isRecording = true;
            RecordingStarted?.Invoke(this, EventArgs.Empty);
            return true;
        }
        catch
        {
            Cleanup();
            return false;
        }
    }

    private async Task WriteDanmakuXmlHeaderAsync(StreamWriter writer, LiveRoom roomInfo)
    {
        var header = $@"<?xml version=""1.0"" encoding=""UTF-8""?>
<i>
    <chatserver>chat.bilibili.com</chatserver>
    <chatid>{roomInfo.RoomId}</chatid>
    <mission>0</mission>
    <maxlimit>10000</maxlimit>
    <state>0</state>
    <real_name>0</real_name>
    <source>e-r</source>
";
        await writer.WriteAsync(header);
    }

    private async Task WriteDanmakuXmlFooterAsync(StreamWriter writer)
    {
        await writer.WriteAsync("</i>");
    }

    public void StopRecording()
    {
        if (!_isRecording) return;

        _isRecording = false;

        try
        {
            _client.Disconnect();

            _flushTimer?.Dispose();
            _flushTimer = null;

            FlushQueues(null);

            if (_sessionId.HasValue)
            {
                _db.EndLiveSession(_sessionId.Value);
            }

            if (_danmakuFileWriter != null)
            {
                WriteDanmakuXmlFooterAsync(_danmakuFileWriter).Wait();
                _danmakuFileWriter.Dispose();
                _danmakuFileWriter = null;
            }

            _giftFileWriter?.Dispose();
            _giftFileWriter = null;
        }
        catch
        {
        }
        finally
        {
            _sessionId = null;
            RecordingStopped?.Invoke(this, EventArgs.Empty);
        }
    }

    private async Task TryReconnectAsync()
    {
        for (int i = 0; i < 5 && _isRecording; i++)
        {
            await Task.Delay(5000 * (i + 1));
            try
            {
                if (await _client.ConnectAsync())
                {
                    return;
                }
            }
            catch
            {
            }
        }
    }

    private void FlushQueues(object? state)
    {
        lock (_queueLock)
        {
            if (!_sessionId.HasValue) return;

            while (_danmakuQueue.TryDequeue(out var danmaku))
            {
                try
                {
                    _db.InsertDanmaku(_sessionId.Value, _roomId, danmaku);
                    WriteDanmakuToFile(danmaku);
                }
                catch
                {
                }
            }

            while (_giftQueue.TryDequeue(out var gift))
            {
                try
                {
                    _db.InsertGift(_sessionId.Value, _roomId, gift);
                    WriteGiftToFile(gift);
                }
                catch
                {
                }
            }

            while (_superChatQueue.TryDequeue(out var sc))
            {
                try
                {
                    _db.InsertSuperChat(_sessionId.Value, _roomId, sc);
                    WriteSuperChatToFile(sc);
                }
                catch
                {
                }
            }
        }
    }

    private void WriteDanmakuToFile(DanmakuMessage msg)
    {
        if (_danmakuFileWriter == null) return;

        try
        {
            var xmlLine = $"<d p=\"0,1,25,16777215,{DateTimeOffset.Now.ToUnixTimeSeconds()},0,{msg.Uid},0\">{EscapeXml(msg.Content)}</d>{Environment.NewLine}";
            _danmakuFileWriter.Write(xmlLine);
        }
        catch
        {
        }
    }

    private void WriteGiftToFile(GiftMessage msg)
    {
        if (_giftFileWriter == null) return;

        try
        {
            var line = $"[{DateTime.Now:HH:mm:ss}] {msg.Uname} 赠送 {msg.GiftName} x{msg.Count} (价值 {msg.TotalCoin} 金瓜子){Environment.NewLine}";
            _giftFileWriter.Write(line);
        }
        catch
        {
        }
    }

    private void WriteSuperChatToFile(SuperChatMessage msg)
    {
        if (_giftFileWriter == null) return;

        try
        {
            var line = $"[{DateTime.Now:HH:mm:ss}] 【SC ¥{msg.Price}】{msg.Uname}: {msg.Message}{Environment.NewLine}";
            _giftFileWriter.Write(line);
        }
        catch
        {
        }
    }

    private string EscapeXml(string value)
    {
        return value
            .Replace("&", "&amp;")
            .Replace("<", "&lt;")
            .Replace(">", "&gt;")
            .Replace("\"", "&quot;")
            .Replace("'", "&apos;");
    }

    private void Cleanup()
    {
        _flushTimer?.Dispose();
        _danmakuFileWriter?.Dispose();
        _giftFileWriter?.Dispose();
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;

        StopRecording();
        _client.Dispose();
    }
}
