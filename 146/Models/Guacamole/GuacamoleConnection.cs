using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models.Guacamole;

public class GuacamoleConnection
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(500)]
    public string? Description { get; set; }

    [Required]
    public GuacamoleProtocol Protocol { get; set; }

    [Required]
    [MaxLength(255)]
    public string Hostname { get; set; } = string.Empty;

    public int Port { get; set; }

    [MaxLength(100)]
    public string? Username { get; set; }

    [MaxLength(255)]
    public string? Password { get; set; }

    [MaxLength(100)]
    public string? Domain { get; set; }

    #region RDP Specific
    public int ColorDepth { get; set; } = 24;

    public int Width { get; set; } = 1920;

    public int Height { get; set; } = 1080;

    public int Dpi { get; set; } = 96;

    public bool EnableAudio { get; set; } = true;

    public bool EnableAudioInput { get; set; } = false;

    public bool EnablePrinting { get; set; } = false;

    public bool EnableDrive { get; set; } = false;

    [MaxLength(500)]
    public string? DrivePath { get; set; }

    public bool EnableClipboard { get; set; } = true;

    public ClipboardDirection ClipboardDirection { get; set; } = ClipboardDirection.Bidirectional;

    public bool EnableWallpaper { get; set; } = false;

    public bool EnableTheming { get; set; } = false;

    public bool EnableFontSmoothing { get; set; } = true;

    public bool EnableFullWindowDrag { get; set; } = false;

    public bool EnableDesktopComposition { get; set; } = false;

    public bool EnableMenuAnimations { get; set; } = false;

    public bool DisableGlyphWrapping { get; set; } = false;

    public bool EnableRemoteApp { get; set; } = false;

    [MaxLength(255)]
    public string? RemoteAppProgram { get; set; }

    [MaxLength(500)]
    public string? RemoteAppArgs { get; set; }

    [MaxLength(500)]
    public string? RemoteAppDir { get; set; }
    #endregion

    #region VNC Specific
    public bool EnableVncCursor { get; set; } = true;

    public bool EnableVncCompression { get; set; } = true;

    public int VncCompressionLevel { get; set; } = 6;

    public bool EnableVncJpeg { get; set; } = true;

    public int VncJpegQuality { get; set; } = 8;

    public bool EnableVncSwapRedBlue { get; set; } = false;

    public bool EnableVncReadOnly { get; set; } = false;
    #endregion

    #region SSH Specific
    [MaxLength(500)]
    public string? SshPrivateKey { get; set; }

    [MaxLength(100)]
    public string? SshPassphrase { get; set; }

    [MaxLength(100)]
    public string? SshHostKey { get; set; }

    public int SshFontSize { get; set; } = 12;

    [MaxLength(100)]
    public string? SshFontName { get; set; } = "Consolas";

    public bool SshEnableSftp { get; set; } = true;
    #endregion

    #region General Settings
    public bool EnableRecording { get; set; } = false;

    [MaxLength(500)]
    public string? RecordingPath { get; set; }

    public bool RecordingIncludeKeyEvents { get; set; } = true;

    public bool RecordingIncludeMouseEvents { get; set; } = true;

    public bool RecordingIncludeTextEvents { get; set; } = true;

    public AudioQuality AudioQuality { get; set; } = AudioQuality.Medium;

    public bool EnableWebSocketCompression { get; set; } = true;

    public int ReadTimeout { get; set; } = 15000;

    public int WriteTimeout { get; set; } = 15000;

    public bool IgnoreCert { get; set; } = true;
    #endregion

    [ForeignKey(nameof(DesktopPool))]
    public Guid? DesktopPoolId { get; set; }

    public Guid? CreatedByUserId { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public bool IsActive { get; set; } = true;

    public DesktopPool? DesktopPool { get; set; }

    public ICollection<GuacamoleSession> Sessions { get; set; } = new List<GuacamoleSession>();
}
