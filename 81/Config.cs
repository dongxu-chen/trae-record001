using System.IO;
using System.Text.Json;
using System.Threading;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class Config
{
    private static readonly string ConfigPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "BiliLiveMonitor",
        "config.json"
    );

    private static readonly SemaphoreSlim _fileLock = new(1, 1);
    private readonly object _listLock = new();

    private List<LiveRoom> _followedRooms = new();

    public List<LiveRoom> FollowedRooms
    {
        get
        {
            lock (_listLock)
            {
                return _followedRooms.ToList();
            }
        }
    }

    public int PollIntervalSeconds { get; set; } = 60;
    public bool EnableNotification { get; set; } = true;

    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true
    };

    public static Config Load()
    {
        try
        {
            _fileLock.Wait();
            try
            {
                if (File.Exists(ConfigPath))
                {
                    var json = File.ReadAllText(ConfigPath);
                    var config = JsonSerializer.Deserialize<Config>(json);
                    if (config != null)
                    {
                        return config;
                    }
                }
            }
            finally
            {
                _fileLock.Release();
            }
        }
        catch
        {
        }

        return new Config();
    }

    public void Save()
    {
        try
        {
            _fileLock.Wait();
            try
            {
                var dir = Path.GetDirectoryName(ConfigPath);
                if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
                {
                    Directory.CreateDirectory(dir);
                }

                var tempPath = ConfigPath + ".tmp";
                var backupPath = ConfigPath + ".bak";

                var snapshot = new ConfigSnapshot
                {
                    FollowedRooms = GetRoomsSnapshot(),
                    PollIntervalSeconds = this.PollIntervalSeconds,
                    EnableNotification = this.EnableNotification
                };

                var json = JsonSerializer.Serialize(snapshot, JsonOptions);
                File.WriteAllText(tempPath, json);

                if (File.Exists(ConfigPath))
                {
                    if (File.Exists(backupPath))
                    {
                        File.Delete(backupPath);
                    }
                    File.Move(ConfigPath, backupPath);
                }

                File.Move(tempPath, ConfigPath);

                if (File.Exists(backupPath))
                {
                    try
                    {
                        File.Delete(backupPath);
                    }
                    catch
                    {
                    }
                }
            }
            finally
            {
                _fileLock.Release();
            }
        }
        catch
        {
        }
    }

    private List<LiveRoom> GetRoomsSnapshot()
    {
        lock (_listLock)
        {
            return _followedRooms.Select(r => new LiveRoom
            {
                RoomId = r.RoomId,
                Title = r.Title,
                UName = r.UName,
                Uid = r.Uid,
                LiveStatus = r.LiveStatus,
                Cover = r.Cover,
                AreaName = r.AreaName,
                LastLiveTime = r.LastLiveTime,
                IsNotified = r.IsNotified
            }).ToList();
        }
    }

    public bool AddRoom(LiveRoom room)
    {
        lock (_listLock)
        {
            if (_followedRooms.Any(r => r.RoomId == room.RoomId))
                return false;

            _followedRooms.Add(room);
        }

        Save();
        return true;
    }

    public bool RemoveRoom(long roomId)
    {
        bool removed;
        lock (_listLock)
        {
            var room = _followedRooms.FirstOrDefault(r => r.RoomId == roomId);
            if (room == null)
                return false;

            removed = _followedRooms.Remove(room);
        }

        if (removed)
        {
            Save();
        }

        return removed;
    }

    public void UpdateRoom(LiveRoom room)
    {
        bool needsSave = false;

        lock (_listLock)
        {
            var existing = _followedRooms.FirstOrDefault(r => r.RoomId == room.RoomId);
            if (existing != null)
            {
                existing.Title = room.Title;
                existing.UName = room.UName;
                existing.LiveStatus = room.LiveStatus;
                existing.Cover = room.Cover;
                existing.AreaName = room.AreaName;
                existing.LastLiveTime = room.LastLiveTime;
                existing.IsNotified = room.IsNotified;
                needsSave = true;
            }
        }

        if (needsSave)
        {
            Save();
        }
    }

    public LiveRoom? GetRoom(long roomId)
    {
        lock (_listLock)
        {
            var existing = _followedRooms.FirstOrDefault(r => r.RoomId == roomId);
            if (existing == null) return null;

            return new LiveRoom
            {
                RoomId = existing.RoomId,
                Title = existing.Title,
                UName = existing.UName,
                Uid = existing.Uid,
                LiveStatus = existing.LiveStatus,
                Cover = existing.Cover,
                AreaName = existing.AreaName,
                LastLiveTime = existing.LastLiveTime,
                IsNotified = existing.IsNotified
            };
        }
    }

    public int GetRoomCount()
    {
        lock (_listLock)
        {
            return _followedRooms.Count;
        }
    }

    private class ConfigSnapshot
    {
        public List<LiveRoom> FollowedRooms { get; set; } = new();
        public int PollIntervalSeconds { get; set; }
        public bool EnableNotification { get; set; }
    }
}
