using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class Desktop
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(DesktopPool))]
    public Guid DesktopPoolId { get; set; }

    [Required]
    [MaxLength(100)]
    public string Name { get; set; } = string.Empty;

    [MaxLength(50)]
    public string? ComputerName { get; set; }

    [MaxLength(50)]
    public string? IpAddress { get; set; }

    public int Port { get; set; } = 3389;

    [Required]
    public DesktopStatus Status { get; set; }

    [MaxLength(500)]
    public string? StatusMessage { get; set; }

    public ConnectionProtocol Protocol { get; set; }

    public int CpuCores { get; set; }

    public int MemoryGB { get; set; }

    public int StorageGB { get; set; }

    public DateTime? LastHeartbeat { get; set; }

    public bool GpuPassthroughEnabled { get; set; } = false;

    public bool SessionRecordingEnabled { get; set; } = false;

    public HealthStatus HealthStatus { get; set; } = HealthStatus.Unknown;

    public int ConsecutiveHealthFailures { get; set; } = 0;

    public DateTime? LastRecoveryAt { get; set; }

    public int RecoveryAttempts { get; set; } = 0;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public DesktopPool DesktopPool { get; set; } = null!;

    public ICollection<Session> Sessions { get; set; } = new List<Session>();

    public ICollection<GpuAssignment> GpuAssignments { get; set; } = new List<GpuAssignment>();

    public ICollection<SessionRecording> SessionRecordings { get; set; } = new List<SessionRecording>();

    public ICollection<DesktopHealthCheck> HealthChecks { get; set; } = new List<DesktopHealthCheck>();

    public ICollection<RecoveryHistory> RecoveryHistories { get; set; } = new List<RecoveryHistory>();

    public ICollection<DesktopMetrics> Metrics { get; set; } = new List<DesktopMetrics>();
}
