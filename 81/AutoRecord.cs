using System.Diagnostics;
using System.IO;
using System.Text;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class AutoRecorder : IDisposable
{
    private readonly Database _db;
    private readonly Dictionary<long, RecordingSession> _sessions = new();
    private readonly object _lock = new();
    private bool _disposed;

    public string RecordOutputDir { get; set; }
    public string? CustomCommand { get; set; }
    public string RecordTool { get; set; } = "ffmpeg";
    public bool Enabled { get; set; } = false;
    public string Quality { get; set; } = "10000";

    public event EventHandler<RecordingEventArgs>? RecordingStarted;
    public event EventHandler<RecordingEventArgs>? RecordingStopped;
    public event EventHandler<RecordingErrorEventArgs>? RecordingError;

    public AutoRecorder(Database db)
    {
        _db = db;
        RecordOutputDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyVideos),
            "BiliLiveMonitor",
            "Records"
        );
    }

    public bool StartRecording(LiveRoom room)
    {
        if (!Enabled) return false;
        if (string.IsNullOrEmpty(RecordTool)) return false;

        lock (_lock)
        {
            if (_sessions.ContainsKey(room.RoomId))
            {
                return false;
            }

            var session = new RecordingSession
            {
                RoomId = room.RoomId,
                RoomInfo = room,
                StartTime = DateTime.Now
            };

            try
            {
                var roomDir = Path.Combine(RecordOutputDir, $"{room.RoomId}_{room.UName}");
                if (!Directory.Exists(roomDir))
                {
                    Directory.CreateDirectory(roomDir);
                }

                var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
                var safeTitle = MakeSafeFileName(room.Title);
                var fileName = $"{timestamp}_{safeTitle}.mp4";
                session.OutputPath = Path.Combine(roomDir, fileName);

                var activeSessionId = _db.GetActiveSessionId(room.RoomId);
                if (activeSessionId.HasValue)
                {
                    session.DbRecordId = _db.AddRecord(activeSessionId.Value, room.RoomId, session.OutputPath);
                }

                Process process;
                if (!string.IsNullOrEmpty(CustomCommand))
                {
                    process = StartCustomProcess(room, session.OutputPath);
                }
                else
                {
                    process = RecordTool.ToLower() switch
                    {
                        "streamlink" => StartStreamlink(room, session.OutputPath),
                        "ffmpeg" => StartFfmpeg(room, session.OutputPath),
                        _ => throw new NotSupportedException($"不支持的录屏工具: {RecordTool}")
                    };
                }

                if (process == null)
                {
                    throw new InvalidOperationException("无法启动录屏进程");
                }

                session.Process = process;
                process.EnableRaisingEvents = true;
                process.Exited += (s, e) => OnProcessExited(room.RoomId);

                _sessions[room.RoomId] = session;
                RecordingStarted?.Invoke(this, new RecordingEventArgs { RoomId = room.RoomId, OutputPath = session.OutputPath });
                return true;
            }
            catch (Exception ex)
            {
                RecordingError?.Invoke(this, new RecordingErrorEventArgs { RoomId = room.RoomId, Error = ex.Message });
                return false;
            }
        }
    }

    public void StopRecording(long roomId)
    {
        lock (_lock)
        {
            if (!_sessions.TryGetValue(roomId, out var session))
            {
                return;
            }

            try
            {
                if (session.Process != null && !session.Process.HasExited)
                {
                    try
                    {
                        session.Process.StandardInput.WriteLine("q");
                    }
                    catch
                    {
                    }

                    if (!session.Process.WaitForExit(5000))
                    {
                        try
                        {
                            session.Process.Kill();
                        }
                        catch
                        {
                        }
                    }
                }

                if (session.DbRecordId.HasValue && File.Exists(session.OutputPath))
                {
                    var fileInfo = new FileInfo(session.OutputPath);
                    _db.UpdateRecordEnd(session.DbRecordId.Value, (long)fileInfo.Length);
                }
            }
            catch (Exception ex)
            {
                RecordingError?.Invoke(this, new RecordingErrorEventArgs { RoomId = roomId, Error = ex.Message });
            }
            finally
            {
                _sessions.Remove(roomId);
                RecordingStopped?.Invoke(this, new RecordingEventArgs { RoomId = roomId, OutputPath = session.OutputPath });
            }
        }
    }

    public bool IsRecording(long roomId)
    {
        lock (_lock)
        {
            return _sessions.ContainsKey(roomId);
        }
    }

    public RecordingSession? GetSession(long roomId)
    {
        lock (_lock)
        {
            return _sessions.TryGetValue(roomId, out var session) ? session : null;
        }
    }

    public List<RecordingSession> GetActiveSessions()
    {
        lock (_lock)
        {
            return _sessions.Values.ToList();
        }
    }

    public void StopAll()
    {
        lock (_lock)
        {
            var roomIds = _sessions.Keys.ToList();
            foreach (var roomId in roomIds)
            {
                StopRecording(roomId);
            }
        }
    }

    private void OnProcessExited(long roomId)
    {
        RecordingStopped?.Invoke(this, new RecordingEventArgs { RoomId = roomId });
    }

    private Process? StartStreamlink(LiveRoom room, string outputPath)
    {
        var arguments = $"\"https://live.bilibili.com/{room.RoomId}\" best -o \"{outputPath}\"";

        return StartProcess("streamlink", arguments);
    }

    private Process? StartFfmpeg(LiveRoom room, string outputPath)
    {
        var streamUrl = GetStreamUrl(room.RoomId).Result;
        if (string.IsNullOrEmpty(streamUrl))
        {
            return null;
        }

        var arguments = $"-i \"{streamUrl}\" -c copy -bsf:a aac_adtstoasc -y \"{outputPath}\"";

        return StartProcess("ffmpeg", arguments);
    }

    private Process? StartCustomProcess(LiveRoom room, string outputPath)
    {
        if (string.IsNullOrEmpty(CustomCommand)) return null;

        var cmd = CustomCommand
            .Replace("{roomId}", room.RoomId.ToString())
            .Replace("{roomName}", room.UName)
            .Replace("{title}", room.Title)
            .Replace("{output}", outputPath)
            .Replace("{quality}", Quality);

        var firstSpace = cmd.IndexOf(' ');
        if (firstSpace <= 0) return null;

        var exe = cmd.Substring(0, firstSpace);
        var args = cmd.Substring(firstSpace + 1);

        return StartProcess(exe, args);
    }

    private Process? StartProcess(string fileName, string arguments)
    {
        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            return Process.Start(startInfo);
        }
        catch
        {
            return null;
        }
    }

    private async Task<string?> GetStreamUrl(long roomId)
    {
        try
        {
            using var httpClient = new HttpClient();
            httpClient.DefaultRequestHeaders.UserAgent.ParseAdd(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            );

            var url = $"https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={roomId}&protocol=0,1&format=0,1,2&codec=0,1&qn={Quality}&platform=web&ptype=8";
            var response = await httpClient.GetAsync(url);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            using var doc = System.Text.Json.JsonDocument.Parse(json);

            if (doc.RootElement.GetProperty("code").GetInt32() != 0)
            {
                return null;
            }

            var data = doc.RootElement.GetProperty("data");
            var playUrlInfo = data.GetProperty("playurl_info");
            var playUrl = playUrlInfo.GetProperty("playurl");
            var stream = playUrl.GetProperty("stream")[0];
            var format = stream.GetProperty("format")[0];
            var codec = format.GetProperty("codec")[0];
            var baseUrl = codec.GetProperty("base_url").GetString();
            var urlInfo = codec.GetProperty("url_info")[0];
            var host = urlInfo.GetProperty("host").GetString();
            var extra = urlInfo.GetProperty("extra").GetString();

            return $"{host}{baseUrl}{extra}";
        }
        catch
        {
            return null;
        }
    }

    private string MakeSafeFileName(string name)
    {
        var invalidChars = Path.GetInvalidFileNameChars();
        var sb = new StringBuilder(name);
        foreach (var c in invalidChars)
        {
            sb.Replace(c, '_');
        }
        return sb.ToString().Trim();
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        StopAll();
    }
}

public class RecordingSession
{
    public long RoomId { get; set; }
    public LiveRoom RoomInfo { get; set; } = null!;
    public string OutputPath { get; set; } = string.Empty;
    public DateTime StartTime { get; set; }
    public Process? Process { get; set; }
    public long? DbRecordId { get; set; }
}

public class RecordingEventArgs : EventArgs
{
    public long RoomId { get; set; }
    public string? OutputPath { get; set; }
}

public class RecordingErrorEventArgs : EventArgs
{
    public long RoomId { get; set; }
    public string Error { get; set; } = string.Empty;
}
