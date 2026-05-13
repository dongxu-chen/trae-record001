namespace BiliLiveMonitor.Models;

public class LiveRoom
{
    public long RoomId { get; set; }
    public string Title { get; set; } = string.Empty;
    public string UName { get; set; } = string.Empty;
    public long Uid { get; set; }
    public int LiveStatus { get; set; }
    public string Cover { get; set; } = string.Empty;
    public string AreaName { get; set; } = string.Empty;
    public DateTime LastLiveTime { get; set; }
    public bool IsNotified { get; set; }
}

public class BiliApiResponse<T>
{
    public int Code { get; set; }
    public string Message { get; set; } = string.Empty;
    public T? Data { get; set; }
}

public class RoomInfoData
{
    public long RoomId { get; set; }
    public long ShortId { get; set; }
    public long Uid { get; set; }
    public string Title { get; set; } = string.Empty;
    public string UName { get; set; } = string.Empty;
    public int LiveStatus { get; set; }
    public string Cover { get; set; } = string.Empty;
    public string AreaName { get; set; } = string.Empty;
    public string ParentAreaName { get; set; } = string.Empty;
    public DateTime LiveTime { get; set; }
}
