namespace CloudDesktop.Api.Models.Enums;

public enum GpuStatus
{
    Available,
    Allocated,
    Maintenance,
    Offline,
    Error
}

public enum GpuType
{
    NVIDIA,
    AMD,
    Intel,
    Other
}

public enum RecordingStatus
{
    Idle,
    Recording,
    Paused,
    Stopped,
    Failed,
    Processing
}

public enum RecordingQuality
{
    Low,
    Medium,
    High,
    Ultra
}

public enum HealthStatus
{
    Healthy,
    Warning,
    Critical,
    Offline,
    Unknown
}

public enum HealthCheckType
{
    Heartbeat,
    RdpConnection,
    CpuUsage,
    MemoryUsage,
    DiskUsage,
    NetworkLatency
}
