using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Threading;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class LiveChecker : IDisposable
{
    private readonly HttpClient _httpClient;
    private readonly Config _config;
    private System.Threading.Timer? _timer;
    private bool _isRunning;
    private readonly Random _random = new();
    private int _consecutiveFailures;
    private readonly SemaphoreSlim _requestSemaphore = new(1, 1);

    public event EventHandler<LiveRoom>? RoomStatusChanged;
    public event EventHandler<LiveRoom>? RoomWentLive;
    public event EventHandler? CheckCompleted;

    public string? Cookie { get; set; }

    public LiveChecker(Config config)
    {
        _config = config;

        var socketsHandler = new SocketsHttpHandler
        {
            PooledConnectionLifetime = TimeSpan.FromMinutes(15),
            PooledConnectionIdleTimeout = TimeSpan.FromMinutes(5),
            MaxConnectionsPerServer = 10
        };

        _httpClient = new HttpClient(socketsHandler)
        {
            Timeout = TimeSpan.FromSeconds(30)
        };

        SetupHttpClientHeaders();
    }

    private void SetupHttpClientHeaders()
    {
        _httpClient.DefaultRequestHeaders.UserAgent.ParseAdd(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        );
        _httpClient.DefaultRequestHeaders.Accept.ParseAdd("application/json, text/plain, */*");
        _httpClient.DefaultRequestHeaders.AcceptLanguage.ParseAdd("zh-CN,zh;q=0.9,en;q=0.8");
        _httpClient.DefaultRequestHeaders.Referrer = new Uri("https://www.bilibili.com/");
        _httpClient.DefaultRequestHeaders.Add("Origin", "https://www.bilibili.com");
    }

    public void Start()
    {
        if (_isRunning) return;

        _isRunning = true;
        _consecutiveFailures = 0;
        _timer = new System.Threading.Timer(CheckAllRooms, null, 0, GetPollInterval());
    }

    public void Stop()
    {
        _isRunning = false;
        _timer?.Dispose();
        _timer = null;
    }

    public void Refresh()
    {
        if (_timer != null)
        {
            _timer.Change(0, GetPollInterval());
        }
    }

    private int GetPollInterval()
    {
        var baseInterval = _config.PollIntervalSeconds * 1000;
        var jitter = _random.Next(-5000, 5000);
        return Math.Max(30000, baseInterval + jitter);
    }

    private async void CheckAllRooms(object? state)
    {
        if (!_isRunning) return;

        try
        {
            var rooms = _config.FollowedRooms.ToList();
            if (rooms.Count == 0)
            {
                CheckCompleted?.Invoke(this, EventArgs.Empty);
                return;
            }

            var roomIds = rooms.Select(r => r.RoomId).ToList();
            var roomStatuses = await GetBatchRoomStatus(roomIds);

            if (roomStatuses != null)
            {
                foreach (var room in rooms)
                {
                    if (roomStatuses.TryGetValue(room.RoomId, out var info))
                    {
                        UpdateRoomFromBatchInfo(room, info);
                    }
                }
                _consecutiveFailures = 0;
            }
            else
            {
                _consecutiveFailures++;
                await CheckRoomsIndividually(rooms);
            }

            CheckCompleted?.Invoke(this, EventArgs.Empty);
        }
        catch (Exception ex)
        {
            _consecutiveFailures++;
        }
        finally
        {
            if (_isRunning && _timer != null)
            {
                var delay = CalculateBackoffDelay();
                _timer.Change(delay, GetPollInterval());
            }
        }
    }

    private int CalculateBackoffDelay()
    {
        if (_consecutiveFailures == 0)
            return GetPollInterval();

        var baseDelay = Math.Min(_consecutiveFailures * 30000, 300000);
        var jitter = _random.Next(0, 10000);
        return baseDelay + jitter;
    }

    private async Task<Dictionary<long, BatchRoomInfo>?> GetBatchRoomStatus(List<long> roomIds)
    {
        try
        {
            await _requestSemaphore.WaitAsync();

            await AddRandomDelay();

            var roomIdsParam = string.Join(",", roomIds);
            var url = $"https://api.live.bilibili.com/room/v1/Room/get_status_info_by_uids?uids={roomIdsParam}";

            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            AddRequestHeaders(request);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var jsonNode = JsonNode.Parse(json);

            if (jsonNode?["code"]?.GetValue<int>() != 0)
            {
                return null;
            }

            var data = jsonNode["data"];
            if (data == null) return null;

            var result = new Dictionary<long, BatchRoomInfo>();

            foreach (var item in data.AsObject())
            {
                if (long.TryParse(item.Key, out var uid) && item.Value != null)
                {
                    var info = ParseBatchRoomInfo(item.Value);
                    if (info != null)
                    {
                        result[info.RoomId] = info;
                    }
                }
            }

            return result;
        }
        catch
        {
            return null;
        }
        finally
        {
            _requestSemaphore.Release();
        }
    }

    private BatchRoomInfo? ParseBatchRoomInfo(JsonNode node)
    {
        try
        {
            return new BatchRoomInfo
            {
                RoomId = node["room_id"]?.GetValue<long>() ?? 0,
                Uid = node["uid"]?.GetValue<long>() ?? 0,
                UName = node["uname"]?.GetValue<string>() ?? string.Empty,
                Title = node["title"]?.GetValue<string>() ?? string.Empty,
                LiveStatus = node["live_status"]?.GetValue<int>() ?? 0,
                Cover = node["cover_from_user"]?.GetValue<string>() ?? string.Empty,
                AreaName = node["area_v2_name"]?.GetValue<string>() ?? string.Empty,
                ParentAreaName = node["area_v2_parent_name"]?.GetValue<string>() ?? string.Empty
            };
        }
        catch
        {
            return null;
        }
    }

    private void UpdateRoomFromBatchInfo(LiveRoom room, BatchRoomInfo info)
    {
        var oldStatus = room.LiveStatus;
        var newStatus = info.LiveStatus;

        room.Uid = info.Uid;
        if (!string.IsNullOrEmpty(info.UName))
        {
            room.UName = info.UName;
        }
        room.Title = info.Title;
        room.LiveStatus = newStatus;
        room.Cover = info.Cover;
        room.AreaName = !string.IsNullOrEmpty(info.ParentAreaName) && !string.IsNullOrEmpty(info.AreaName)
            ? $"{info.ParentAreaName}-{info.AreaName}"
            : info.AreaName;

        if (newStatus == 1)
        {
            if (oldStatus != 1 && !room.IsNotified)
            {
                room.IsNotified = true;
                room.LastLiveTime = DateTime.Now;
                RoomWentLive?.Invoke(this, room);
            }
        }
        else if (oldStatus == 1 && newStatus != 1)
        {
            room.IsNotified = false;
        }

        if (oldStatus != newStatus)
        {
            RoomStatusChanged?.Invoke(this, room);
        }

        _config.UpdateRoom(room);
    }

    private async Task CheckRoomsIndividually(List<LiveRoom> rooms)
    {
        foreach (var room in rooms)
        {
            await CheckRoomStatusSingle(room);
            await AddRandomDelay(1000, 2000);
        }
    }

    private async Task CheckRoomStatusSingle(LiveRoom room)
    {
        try
        {
            var newInfo = await GetRoomInfoSingle(room.RoomId);
            if (newInfo == null) return;

            var oldStatus = room.LiveStatus;
            var newStatus = newInfo.LiveStatus;

            if (string.IsNullOrEmpty(room.UName))
            {
                room.UName = newInfo.UName;
            }
            room.Title = newInfo.Title;
            room.LiveStatus = newStatus;
            room.Cover = newInfo.Cover;
            room.AreaName = newInfo.AreaName;

            if (newStatus == 1)
            {
                room.LastLiveTime = newInfo.LastLiveTime;

                if (oldStatus != 1 && !room.IsNotified)
                {
                    room.IsNotified = true;
                    RoomWentLive?.Invoke(this, room);
                }
            }
            else if (oldStatus == 1 && newStatus != 1)
            {
                room.IsNotified = false;
            }

            if (oldStatus != newStatus)
            {
                RoomStatusChanged?.Invoke(this, room);
            }

            _config.UpdateRoom(room);
        }
        catch
        {
        }
    }

    public async Task<LiveRoom?> GetRoomInfo(long roomId)
    {
        return await GetRoomInfoSingle(roomId);
    }

    private async Task<LiveRoom?> GetRoomInfoSingle(long roomId)
    {
        try
        {
            await _requestSemaphore.WaitAsync();
            await AddRandomDelay();

            var url = $"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={roomId}";

            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            AddRequestHeaders(request);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var jsonNode = JsonNode.Parse(json);

            if (jsonNode?["code"]?.GetValue<int>() != 0)
            {
                return null;
            }

            var data = jsonNode["data"];
            if (data == null) return null;

            var uid = data["uid"]?.GetValue<long>() ?? 0;
            var uname = data["uname"]?.GetValue<string>() ?? string.Empty;

            if (string.IsNullOrEmpty(uname) && uid > 0)
            {
                uname = await GetUserName(uid);
            }

            var liveStatus = data["live_status"]?.GetValue<int>() ?? 0;
            var liveTimeValue = data["live_time"]?.GetValue<long>() ?? 0;
            var liveTime = liveTimeValue > 0
                ? DateTimeOffset.FromUnixTimeSeconds(liveTimeValue).LocalDateTime
                : DateTime.MinValue;

            return new LiveRoom
            {
                RoomId = data["room_id"]?.GetValue<long>() ?? roomId,
                Title = data["title"]?.GetValue<string>() ?? string.Empty,
                Uid = uid,
                UName = uname,
                LiveStatus = liveStatus,
                Cover = data["user_cover"]?.GetValue<string>() ?? string.Empty,
                AreaName = $"{data["parent_area_name"]?.GetValue<string>()}-{data["area_name"]?.GetValue<string>()}",
                LastLiveTime = liveTime,
                IsNotified = false
            };
        }
        catch
        {
            return null;
        }
        finally
        {
            _requestSemaphore.Release();
        }
    }

    private async Task<string> GetUserName(long uid)
    {
        try
        {
            if (uid == 0) return string.Empty;

            await AddRandomDelay(500, 1000);

            var url = $"https://api.bilibili.com/x/space/wbi/acc/info?mid={uid}";

            using var request = new HttpRequestMessage(HttpMethod.Get, url);
            AddRequestHeaders(request);

            var response = await _httpClient.SendAsync(request);
            response.EnsureSuccessStatusCode();

            var json = await response.Content.ReadAsStringAsync();
            var jsonNode = JsonNode.Parse(json);

            if (jsonNode?["code"]?.GetValue<int>() != 0)
            {
                return string.Empty;
            }

            return jsonNode["data"]?["name"]?.GetValue<string>() ?? string.Empty;
        }
        catch
        {
            return string.Empty;
        }
    }

    private void AddRequestHeaders(HttpRequestMessage request)
    {
        if (!string.IsNullOrEmpty(Cookie))
        {
            request.Headers.Add("Cookie", Cookie);
        }
    }

    private async Task AddRandomDelay(int minMs = 300, int maxMs = 800)
    {
        var delay = _random.Next(minMs, maxMs);
        await Task.Delay(delay);
    }

    public void Dispose()
    {
        Stop();
        _httpClient.Dispose();
        _requestSemaphore.Dispose();
    }
}

public class BatchRoomInfo
{
    public long RoomId { get; set; }
    public long Uid { get; set; }
    public string UName { get; set; } = string.Empty;
    public string Title { get; set; } = string.Empty;
    public int LiveStatus { get; set; }
    public string Cover { get; set; } = string.Empty;
    public string AreaName { get; set; } = string.Empty;
    public string ParentAreaName { get; set; } = string.Empty;
}
