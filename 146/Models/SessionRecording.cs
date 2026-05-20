using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class SessionRecording
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Session))]
    public Guid SessionId { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    [Required]
    [ForeignKey(nameof(User))]
    public Guid UserId { get; set; }

    [Required]
    [MaxLength(500)]
    public string FilePath { get; set; } = string.Empty;

    [MaxLength(200)]
    public string? FileName { get; set; }

    public long FileSizeBytes { get; set; }

    public RecordingStatus Status { get; set; }

    public RecordingQuality Quality { get; set; }

    public int Fps { get; set; } = 30;

    public int Width { get; set; } = 1920;

    public int Height { get; set; } = 1080;

    public bool IncludeAudio { get; set; } = true;

    public bool IncludeCursor { get; set; } = true;

    public TimeSpan Duration { get; set; }

    public DateTime? StartedAt { get; set; }

    public DateTime? StoppedAt { get; set; }

    [MaxLength(500)]
    public string? ErrorMessage { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public Session Session { get; set; } = null!;

    public Desktop Desktop { get; set; } = null!;

    public User User { get; set; } = null!;
}

public class ClipboardConfiguration
{
    [Key]
    public Guid Id { get; set; }

    [ForeignKey(nameof(DesktopPool))]
    public Guid? DesktopPoolId { get; set; }

    [ForeignKey(nameof(Desktop))]
    public Guid? DesktopId { get; set; }

    [ForeignKey(nameof(User))]
    public Guid? UserId { get; set; }

    public bool ClipboardEnabled { get; set; } = true;

    public bool CopyFromClientEnabled { get; set; } = true;

    public bool CopyToClientEnabled { get; set; } = true;

    public bool FileTransferEnabled { get; set; } = false;

    public int MaxClipboardSizeKB { get; set; } = 10240;

    public bool RestrictFileTypes { get; set; } = false;

    [MaxLength(500)]
    public string? AllowedFileTypes { get; set; }

    [MaxLength(500)]
    public string? BlockedFileTypes { get; set; }

    public bool AuditClipboardActivity { get; set; } = false;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public DesktopPool? DesktopPool { get; set; }

    public Desktop? Desktop { get; set; }

    public User? User { get; set; }
}

public class ClipboardAuditLog
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Session))]
    public Guid SessionId { get; set; }

    [Required]
    [ForeignKey(nameof(User))]
    public Guid UserId { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    public bool IsCopyFromClient { get; set; }

    [MaxLength(500)]
    public string? ContentType { get; set; }

    public int ContentSizeKB { get; set; }

    [MaxLength(1000)]
    public string? FileName { get; set; }

    public bool WasBlocked { get; set; }

    [MaxLength(500)]
    public string? BlockReason { get; set; }

    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    public Session Session { get; set; } = null!;

    public User User { get; set; } = null!;

    public Desktop Desktop { get; set; } = null!;
}
