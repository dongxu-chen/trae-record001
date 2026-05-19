namespace CloudDesktop.Api.Models.Guacamole;

public enum GuacamoleProtocol
{
    RDP,
    VNC,
    SSH,
    Telnet
}

public enum GuacamoleConnectionState
{
    Idle,
    Connecting,
    Connected,
    Disconnecting,
    Disconnected,
    Error
}

public enum ClipboardDirection
{
    Disabled,
    ServerToClient,
    ClientToServer,
    Bidirectional
}

public enum AudioQuality
{
    Low,
    Medium,
    High
}

public enum RecordingFormat
{
    Raw,
    JSON,
    Binary
}
