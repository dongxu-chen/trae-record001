using CloudDesktop.Api.Models.Enums;
using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace CloudDesktop.Api.Models;

public class DesktopHealthCheck
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    public HealthStatus OverallStatus { get; set; }

    public HealthStatus RdpStatus { get; set; }

    public HealthStatus CpuStatus { get; set; }

    public HealthStatus MemoryStatus { get; set; }

    public HealthStatus DiskStatus { get; set; }

    public HealthStatus NetworkStatus { get; set; }

    public HealthStatus GpuStatus { get; set; }

    public decimal CpuUsagePercent { get; set; }

    public decimal MemoryUsagePercent { get; set; }

    public decimal DiskUsagePercent { get; set; }

    public int NetworkLatencyMs { get; set; }

    public int UptimeSeconds { get; set; }

    public int ActiveSessions { get; set; }

    [MaxLength(1000)]
    public string? StatusMessage { get; set; }

    [MaxLength(2000)]
    public string? Details { get; set; }

    public DateTime CheckedAt { get; set; } = DateTime.UtcNow;

    public Desktop Desktop { get; set; } = null!;
}

public class DesktopHealthConfiguration
{
    [Key]
    public Guid Id { get; set; }

    [ForeignKey(nameof(DesktopPool))]
    public Guid? DesktopPoolId { get; set; }

    [ForeignKey(nameof(Desktop))]
    public Guid? DesktopId { get; set; }

    public bool HealthCheckEnabled { get; set; } = true;

    public int CheckIntervalSeconds { get; set; } = 60;

    public int HeartbeatTimeoutSeconds { get; set; } = 120;

    public bool AutoRecoveryEnabled { get; set; } = true;

    public int MaxRecoveryAttempts { get; set; } = 3;

    public int RecoveryCooldownMinutes { get; set; } = 30;

    public bool RestartOnRdpFailure { get; set; } = true;

    public bool RestartOnHighCpuUsage { get; set; } = false;

    public decimal CpuUsageThresholdPercent { get; set; } = 95;

    public int CpuUsageThresholdDurationSeconds { get; set; } = 300;

    public bool RestartOnHighMemoryUsage { get; set; } = false;

    public decimal MemoryUsageThresholdPercent { get; set; } = 95;

    public int MemoryUsageThresholdDurationSeconds { get; set; } = 300;

    public bool RestartOnHighDiskUsage { get; set; } = false;

    public decimal DiskUsageThresholdPercent { get; set; } = 95;

    public int ConsecutiveFailuresForRecovery { get; set; } = 3;

    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;

    public DateTime? UpdatedAt { get; set; }

    public DesktopPool? DesktopPool { get; set; }

    public Desktop? Desktop { get; set; }
}

public class RecoveryHistory
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    [Required]
    [MaxLength(100)]
    public string RecoveryType { get; set; } = string.Empty;

    [MaxLength(1000)]
    public string? Reason { get; set; }

    public HealthStatus StatusBeforeRecovery { get; set; }

    public bool RecoverySuccessful { get; set; }

    public int RecoveryAttempt { get; set; }

    public int RecoveryDurationSeconds { get; set; }

    [MaxLength(2000)]
    public string? RecoveryDetails { get; set; }

    [MaxLength(1000)]
    public string? ErrorMessage { get; set; }

    public DateTime StartedAt { get; set; } = DateTime.UtcNow;

    public DateTime? CompletedAt { get; set; }

    public Desktop Desktop { get; set; } = null!;
}

public class DesktopMetrics
{
    [Key]
    public Guid Id { get; set; }

    [Required]
    [ForeignKey(nameof(Desktop))]
    public Guid DesktopId { get; set; }

    public decimal CpuUsagePercent { get; set; }

    public decimal MemoryUsagePercent { get; set; }

    public decimal DiskUsagePercent { get; set; }

    public long NetworkInBytes { get; set; }

    public long NetworkOutBytes { get; set; }

    public int NetworkLatencyMs { get; set; }

    public decimal GpuUsagePercent { get; set; }

    public decimal GpuMemoryUsagePercent { get; set; }

    public decimal GpuTemperature { get; set; }

    public int ActiveSessionCount { get; set; }

    public int UptimeSeconds { get; set; }

    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    public Desktop Desktop { get; set; } = null!;
}
