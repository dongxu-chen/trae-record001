using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models.Guacamole;

public class GuacamoleSession
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(GuacamoleConnection))]
    public Guid ConnectionId { get; set; }

    [Required]
    [ForeignKey(nameof(User))]
    public Guid UserId { get; set; }

    [MaxLength(100)]
    public string? ConnectionName { get; set; }

    public GuacamoleProtocol Protocol { get; set; }

    public GuacamoleConnectionState State { get; set; }

    [MaxLength(50)]
    public string? ClientIpAddress { get; set; }

    [MaxLength(100)]
    public string? ClientHostname { get; set; }

    [MaxLength(200)]
    public string? ClientUserAgent { get; set; }

    public int DisplayWidth { get; set; }

    public int DisplayHeight { get; set; }

    public int DisplayDpi { get; set; }

    public DateTime? ConnectedAt { get; set; }

    public DateTime? DisconnectedAt { get; set; }

    public TimeSpan? Duration { get; set; }

    public long BytesSent { get; set; }

    public long BytesReceived { get; set; }

    public long FrameCount { get; set; }

    public long KeyEventCount { get; set; }

    public long MouseEventCount { get; set; }

    [MaxLength(500)]
    public string? ErrorMessage { get; set; }

    [MaxLength(1000)]
    public string? DisconnectReason { get; set; }

    public bool HasRecording { get; set; }

    [MaxLength(500)]
    public string? RecordingPath { get; set; }

    public long RecordingSizeBytes { get; set; }

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public GuacamoleConnection Connection { get; set; } = null!;

    public User User { get; set; } = null!;

    public ICollection<SessionRecording> Recordings { get; set; } = new List<SessionRecording>();
}
