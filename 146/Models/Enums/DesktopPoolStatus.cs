namespace CloudDesktop.Api.Models.Enums;

public enum DesktopPoolStatus
{
    Available,
    Busy,
    Maintenance,
    Offline
}

public enum DesktopStatus
{
    Available,
    InUse,
    Starting,
    Stopping,
    Maintenance,
    Error
}

public enum SessionStatus
{
    Active,
    Disconnected,
    LoggedOff,
    Connecting,
    Failed
}

public enum ConnectionProtocol
{
    RDP,
    VNC,
    SPICE
}
