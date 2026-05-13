using System.Data;
using Microsoft.Data.Sqlite;
using BiliLiveMonitor.Models;

namespace BiliLiveMonitor;

public class Database : IDisposable
{
    private readonly SqliteConnection _connection;
    private readonly object _lock = new();
    private bool _disposed;

    private static readonly string DbPath = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "BiliLiveMonitor",
        "data.db"
    );

    public Database()
    {
        var dir = Path.GetDirectoryName(DbPath);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
        {
            Directory.CreateDirectory(dir);
        }

        _connection = new SqliteConnection($"Data Source={DbPath}");
        _connection.Open();
        InitializeTables();
    }

    private void InitializeTables()
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
CREATE TABLE IF NOT EXISTS live_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id INTEGER NOT NULL,
    uid INTEGER,
    uname TEXT,
    title TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_live_sessions_room ON live_sessions(room_id);
CREATE INDEX IF NOT EXISTS idx_live_sessions_status ON live_sessions(status);

CREATE TABLE IF NOT EXISTS danmakus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    uid INTEGER,
    uname TEXT,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    msg_type INTEGER DEFAULT 1,
    price INTEGER DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES live_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_danmakus_session ON danmakus(session_id);
CREATE INDEX IF NOT EXISTS idx_danmakus_room ON danmakus(room_id);
CREATE INDEX IF NOT EXISTS idx_danmakus_time ON danmakus(timestamp);

CREATE TABLE IF NOT EXISTS gifts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    uid INTEGER,
    uname TEXT,
    gift_name TEXT NOT NULL,
    gift_id INTEGER,
    count INTEGER NOT NULL,
    price INTEGER NOT NULL,
    total_coin INTEGER NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES live_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_gifts_session ON gifts(session_id);
CREATE INDEX IF NOT EXISTS idx_gifts_room ON gifts(room_id);
CREATE INDEX IF NOT EXISTS idx_gifts_time ON gifts(timestamp);

CREATE TABLE IF NOT EXISTS super_chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    uid INTEGER,
    uname TEXT,
    content TEXT,
    price INTEGER NOT NULL,
    message TEXT,
    timestamp TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES live_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_super_chats_session ON super_chats(session_id);
CREATE INDEX IF NOT EXISTS idx_super_chats_room ON super_chats(room_id);

CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    room_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status INTEGER DEFAULT 0,
    FOREIGN KEY(session_id) REFERENCES live_sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_records_session ON records(session_id);
CREATE INDEX IF NOT EXISTS idx_records_room ON records(room_id);
";
            cmd.ExecuteNonQuery();
        }
    }

    public long StartLiveSession(long roomId, long uid, string uname, string title)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
INSERT INTO live_sessions (room_id, uid, uname, title, start_time, status)
VALUES ($roomId, $uid, $uname, $title, $startTime, 1);
SELECT last_insert_rowid();
";
            cmd.Parameters.AddWithValue("$roomId", roomId);
            cmd.Parameters.AddWithValue("$uid", uid);
            cmd.Parameters.AddWithValue("$uname", uname ?? string.Empty);
            cmd.Parameters.AddWithValue("$title", title ?? string.Empty);
            cmd.Parameters.AddWithValue("$startTime", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));

            var result = cmd.ExecuteScalar();
            return Convert.ToInt64(result);
        }
    }

    public void EndLiveSession(long sessionId)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
UPDATE live_sessions 
SET end_time = $endTime, status = 0 
WHERE id = $sessionId AND status = 1
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$endTime", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            cmd.ExecuteNonQuery();
        }
    }

    public long? GetActiveSessionId(long roomId)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
SELECT id FROM live_sessions 
WHERE room_id = $roomId AND status = 1 
ORDER BY id DESC LIMIT 1
";
            cmd.Parameters.AddWithValue("$roomId", roomId);

            using var reader = cmd.ExecuteReader();
            if (reader.Read())
            {
                return reader.GetInt64(0);
            }
            return null;
        }
    }

    public void InsertDanmaku(long sessionId, long roomId, DanmakuMessage msg)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
INSERT INTO danmakus (session_id, room_id, uid, uname, content, timestamp, msg_type, price)
VALUES ($sessionId, $roomId, $uid, $uname, $content, $timestamp, $msgType, $price)
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$roomId", roomId);
            cmd.Parameters.AddWithValue("$uid", msg.Uid);
            cmd.Parameters.AddWithValue("$uname", msg.Uname ?? string.Empty);
            cmd.Parameters.AddWithValue("$content", msg.Content ?? string.Empty);
            cmd.Parameters.AddWithValue("$timestamp", msg.Timestamp.ToString("yyyy-MM-dd HH:mm:ss"));
            cmd.Parameters.AddWithValue("$msgType", msg.MsgType);
            cmd.Parameters.AddWithValue("$price", msg.Price);
            cmd.ExecuteNonQuery();
        }
    }

    public void InsertGift(long sessionId, long roomId, GiftMessage msg)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
INSERT INTO gifts (session_id, room_id, uid, uname, gift_name, gift_id, count, price, total_coin, timestamp)
VALUES ($sessionId, $roomId, $uid, $uname, $giftName, $giftId, $count, $price, $totalCoin, $timestamp)
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$roomId", roomId);
            cmd.Parameters.AddWithValue("$uid", msg.Uid);
            cmd.Parameters.AddWithValue("$uname", msg.Uname ?? string.Empty);
            cmd.Parameters.AddWithValue("$giftName", msg.GiftName ?? string.Empty);
            cmd.Parameters.AddWithValue("$giftId", msg.GiftId);
            cmd.Parameters.AddWithValue("$count", msg.Count);
            cmd.Parameters.AddWithValue("$price", msg.Price);
            cmd.Parameters.AddWithValue("$totalCoin", msg.TotalCoin);
            cmd.Parameters.AddWithValue("$timestamp", msg.Timestamp.ToString("yyyy-MM-dd HH:mm:ss"));
            cmd.ExecuteNonQuery();
        }
    }

    public void InsertSuperChat(long sessionId, long roomId, SuperChatMessage msg)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
INSERT INTO super_chats (session_id, room_id, uid, uname, content, price, message, timestamp)
VALUES ($sessionId, $roomId, $uid, $uname, $content, $price, $message, $timestamp)
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$roomId", roomId);
            cmd.Parameters.AddWithValue("$uid", msg.Uid);
            cmd.Parameters.AddWithValue("$uname", msg.Uname ?? string.Empty);
            cmd.Parameters.AddWithValue("$content", msg.Content ?? string.Empty);
            cmd.Parameters.AddWithValue("$price", msg.Price);
            cmd.Parameters.AddWithValue("$message", msg.Message ?? string.Empty);
            cmd.Parameters.AddWithValue("$timestamp", msg.Timestamp.ToString("yyyy-MM-dd HH:mm:ss"));
            cmd.ExecuteNonQuery();
        }
    }

    public long AddRecord(long sessionId, long roomId, string filePath)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
INSERT INTO records (session_id, room_id, file_path, start_time, status)
VALUES ($sessionId, $roomId, $filePath, $startTime, 1);
SELECT last_insert_rowid();
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$roomId", roomId);
            cmd.Parameters.AddWithValue("$filePath", filePath);
            cmd.Parameters.AddWithValue("$startTime", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));

            var result = cmd.ExecuteScalar();
            return Convert.ToInt64(result);
        }
    }

    public void UpdateRecordEnd(long recordId, long fileSize = 0)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
UPDATE records 
SET end_time = $endTime, file_size = $fileSize, status = 2 
WHERE id = $recordId
";
            cmd.Parameters.AddWithValue("$recordId", recordId);
            cmd.Parameters.AddWithValue("$endTime", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"));
            cmd.Parameters.AddWithValue("$fileSize", fileSize);
            cmd.ExecuteNonQuery();
        }
    }

    public List<GiftStatsResult> GetGiftStatsBySession(long sessionId)
    {
        var results = new List<GiftStatsResult>();
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
SELECT gift_name, SUM(count) as total_count, SUM(total_coin) as total_coin, COUNT(*) as send_count
FROM gifts 
WHERE session_id = $sessionId
GROUP BY gift_name
ORDER BY total_coin DESC
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                results.Add(new GiftStatsResult
                {
                    GiftName = reader.GetString(0),
                    TotalCount = reader.GetInt32(1),
                    TotalCoin = reader.GetInt32(2),
                    SendCount = reader.GetInt32(3)
                });
            }
        }
        return results;
    }

    public List<GiftStatsByUser> GetGiftStatsByUser(long sessionId, int topN = 10)
    {
        var results = new List<GiftStatsByUser>();
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
SELECT uname, SUM(total_coin) as total_coin, COUNT(*) as gift_count
FROM gifts 
WHERE session_id = $sessionId
GROUP BY uid, uname
ORDER BY total_coin DESC
LIMIT $topN
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            cmd.Parameters.AddWithValue("$topN", topN);

            using var reader = cmd.ExecuteReader();
            while (reader.Read())
            {
                results.Add(new GiftStatsByUser
                {
                    Uname = reader.GetString(0),
                    TotalCoin = reader.GetInt32(1),
                    GiftCount = reader.GetInt32(2)
                });
            }
        }
        return results;
    }

    public int GetDanmakuCount(long sessionId)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"SELECT COUNT(*) FROM danmakus WHERE session_id = $sessionId";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            return Convert.ToInt32(cmd.ExecuteScalar());
        }
    }

    public long GetTotalIncome(long sessionId)
    {
        lock (_lock)
        {
            using var cmd = _connection.CreateCommand();
            cmd.CommandText = @"
SELECT COALESCE(SUM(total_coin), 0) + COALESCE((SELECT SUM(price) FROM super_chats WHERE session_id = $sessionId), 0)
FROM gifts WHERE session_id = $sessionId
";
            cmd.Parameters.AddWithValue("$sessionId", sessionId);
            return Convert.ToInt64(cmd.ExecuteScalar());
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        _disposed = true;
        _connection?.Close();
        _connection?.Dispose();
    }
}

public class DanmakuMessage
{
    public long Uid { get; set; }
    public string Uname { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public DateTime Timestamp { get; set; } = DateTime.Now;
    public int MsgType { get; set; } = 1;
    public int Price { get; set; }
}

public class GiftMessage
{
    public long Uid { get; set; }
    public string Uname { get; set; } = string.Empty;
    public string GiftName { get; set; } = string.Empty;
    public long GiftId { get; set; }
    public int Count { get; set; }
    public int Price { get; set; }
    public int TotalCoin { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.Now;
}

public class SuperChatMessage
{
    public long Uid { get; set; }
    public string Uname { get; set; } = string.Empty;
    public string Content { get; set; } = string.Empty;
    public string Message { get; set; } = string.Empty;
    public int Price { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.Now;
}

public class GiftStatsResult
{
    public string GiftName { get; set; } = string.Empty;
    public int TotalCount { get; set; }
    public int TotalCoin { get; set; }
    public int SendCount { get; set; }
}

public class GiftStatsByUser
{
    public string Uname { get; set; } = string.Empty;
    public int TotalCoin { get; set; }
    public int GiftCount { get; set; }
}
